import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# 允许所有来源跨域（手机端访问需要）
CORS(app, origins=['*'], supports_credentials=True)

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = 'https://api.deepseek.com/chat/completions'

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/chat', methods=['POST'])
def chat():
    # 不再验证登录，直接处理请求
    data = request.get_json()
    if not data or 'messages' not in data:
        return jsonify({'error': 'Missing messages'}), 400

    messages = data['messages']
    # 限制历史长度，避免过长
    if len(messages) > 30:
        messages = messages[-30:]

    if not DEEPSEEK_API_KEY:
        print("错误: DEEPSEEK_API_KEY 环境变量未设置")
        return jsonify({'error': 'Server configuration error'}), 500

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}'
    }

    payload = {
        'model': 'deepseek-chat',
        'messages': messages,
        'temperature': 0.7,
        'max_tokens': 500
    }

    try:
        resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        reply = result['choices'][0]['message']['content']
        return jsonify({'reply': reply})
    except requests.exceptions.RequestException as e:
        print(f"DeepSeek API 请求失败: {e}")
        return jsonify({'error': 'AI service unavailable'}), 500
    except Exception as e:
        print(f"未知错误: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))