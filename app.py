import os
import hashlib
import requests
from flask import Flask, request, jsonify, session
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a-default-secret-key-change-in-production')
CORS(app, origins=['*'], supports_credentials=True)  # 允许携带 cookie

# ---------- 预设用户（白名单）----------
# 格式：用户名: 密码的 sha256 哈希（或明文，建议哈希）
# 方式1：从环境变量读取 JSON 字符串
# 例如在 Railway Variables 中添加 ALLOWED_USERS = '{"alice":"5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8","bob":"..."}'
# 方式2：直接硬编码（不推荐，但简单）
ALLOWED_USERS_RAW = os.environ.get('ALLOWED_USERS', '{}')
import json
try:
    ALLOWED_USERS = json.loads(ALLOWED_USERS_RAW)
except:
    ALLOWED_USERS = {}

# 如果没有设置环境变量，默认只允许一个测试账号（请务必在生产环境修改）
if not ALLOWED_USERS:
    # 默认账号: username = "admin", password = "admin123" 的 sha256
    # 实际使用请通过 Railway Variables 覆盖
    ALLOWED_USERS = {
        "admin": hashlib.sha256("admin123".encode()).hexdigest()
    }

def verify_password(username, password):
    if username not in ALLOWED_USERS:
        return False
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return hashed == ALLOWED_USERS[username]

# ---------- 路由 ----------
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if verify_password(username, password):
        session['user'] = username
        session.permanent = True  # 保持会话
        return jsonify({'success': True, 'username': username})
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'success': True})

@app.route('/check_auth', methods=['GET'])
def check_auth():
    if 'user' in session:
        return jsonify({'authenticated': True, 'username': session['user']})
    return jsonify({'authenticated': False}), 401

@app.route('/chat', methods=['POST'])
def chat():
    # 未登录拒绝访问
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # 以下为原有聊天逻辑
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
    if not DEEPSEEK_API_KEY:
        return jsonify({'error': 'DEEPSEEK_API_KEY not set'}), 500

    data = request.get_json()
    if not data or 'messages' not in data:
        return jsonify({'error': 'Missing messages'}), 400

    messages = data['messages'][-30:]

    try:
        resp = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {DEEPSEEK_API_KEY}'
            },
            json={
                'model': 'deepseek-chat',
                'messages': messages,
                'temperature': 0.7,
                'max_tokens': 500
            },
            timeout=30
        )
        resp.raise_for_status()
        result = resp.json()
        reply = result['choices'][0]['message']['content']
        return jsonify({'reply': reply})
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
