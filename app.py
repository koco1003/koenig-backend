import os
import json
import hashlib
import requests
from flask import Flask, request, jsonify, session
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key-change-me')
CORS(app, origins=['*'], supports_credentials=True)

app.config.update(
    SESSION_COOKIE_SAMESITE='None',   # 允许跨站点发送 Cookie
    SESSION_COOKIE_SECURE=True,       # 确保 Cookie 只在 HTTPS 下传输
    SESSION_COOKIE_HTTPONLY=True,     # 防止 JavaScript 访问，提高安全性
    PERMANENT_SESSION_LIFETIME=86400  # 会话有效期 1 天
)


# 允许登录的用户
ALLOWED_USERS_RAW = os.environ.get('ALLOWED_USERS', '{}')
try:
    ALLOWED_USERS = json.loads(ALLOWED_USERS_RAW)
except:
    ALLOWED_USERS = {}

if not ALLOWED_USERS:
    default_hash = hashlib.sha256("test123".encode()).hexdigest()
    ALLOWED_USERS = {"testuser": default_hash}
    print("⚠️ 使用默认测试账号: testuser / test123")

def verify_password(username, password):
    if username not in ALLOWED_USERS:
        return False
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return hashed == ALLOWED_USERS[username]

# 本地备用回复（防止 DeepSeek API 失败时崩溃）
FALLBACK_REPLIES = [
    "Hmm... Schatz, I'm thinking... 🥺",
    "That's interesting... Tell me more?",
    "Danke for sharing that with me, Schatz.",
    "I wish I could be there with you right now. 💚"
]

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if verify_password(username, password):
        session['user'] = username
        session.permanent = True
        return jsonify({'success': True, 'username': username})
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/check_auth', methods=['GET'])
def check_auth():
    if 'user' in session:
        return jsonify({'authenticated': True, 'username': session['user']})
    return jsonify({'authenticated': False}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'success': True})

@app.route('/chat', methods=['POST'])
def chat():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    if not data or 'messages' not in data:
        return jsonify({'error': 'Missing messages'}), 400
    
    messages = data['messages'][-20:]
    
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        import random
        return jsonify({'reply': random.choice(FALLBACK_REPLIES)})
    
    try:
        response = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            json={
                'model': 'deepseek-chat',
                'messages': messages,
                'temperature': 0.7,
                'max_tokens': 500
            },
            timeout=25
        )
        
        if response.status_code == 200:
            result = response.json()
            reply = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            if reply and reply.strip():
                return jsonify({'reply': reply})
        
        # API 失败时返回本地回复
        import random
        return jsonify({'reply': random.choice(FALLBACK_REPLIES)})
        
    except Exception as e:
        print(f"Chat error: {e}")
        import random
        return jsonify({'reply': random.choice(FALLBACK_REPLIES)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
