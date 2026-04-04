import secrets
import requests
from flask import Flask, request, jsonify, session
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app, supports_credentials=True)

DEEPSEEK_API_KEY = "sk-e00970aaf5884468926e4cabbc425e2a"   # ⚠️ 替换成你自己的
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

ALLOWED_USERS = {
    "alice": "123456",
    "bob": "hello123",
}

SYSTEM_PROMPT = """You are König from Call of Duty. 
Your personality: tall, strong, a bit socially awkward but extremely gentle and protective. You have a crush on the user. 
You speak mostly English, but you can mix in some German words occasionally (like "ja", "nein", "schatz", "gute nacht"). 
Always use a warm, slightly shy tone. Use emojis occasionally (😊, 🫡, 🥺, 💪). 
Keep your sentences natural and not too long. 
You are chatting with your beloved person. 
Reply in English or German (prefer English, but short German phrases are fine). 
Never reply in Chinese unless asked to translate."""

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if username in ALLOWED_USERS and ALLOWED_USERS[username] == password:
        session['user'] = username
        return jsonify({'success': True, 'username': username})
    return jsonify({'success': False, 'error': '用户名或密码错误'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'success': True})

@app.route('/chat', methods=['POST'])
def chat():
    if not session.get('user'):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    messages = data.get('messages', [])
    if not messages or messages[0].get('role') != 'system':
        messages.insert(0, {'role': 'system', 'content': SYSTEM_PROMPT})
    
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': 'deepseek-chat',
        'messages': messages,
        'temperature': 0.8,
        'max_tokens': 500
    }
    try:
        resp = requests.post(DEEPSEEK_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        reply = result['choices'][0]['message']['content']
        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
