from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import datetime
import os
import redis
from dotenv import load_dotenv
import telegram

app = Flask(__name__)
CORS(app, origins=[os.getenv('FRONTEND_URL')])
load_dotenv()

# Get the absolute path to user_data.json from Telegram bot
USER_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user_data.json')

def load_user_data():
    try:
        if not os.path.exists(USER_DATA_FILE):
            return {}
        with open(USER_DATA_FILE, 'r') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"Error loading user data: {e}")
        return {}

load_dotenv()

# Replace hardcoded values with environment variables
redis_url = os.getenv('REDIS_URL')
redis_client = redis.from_url(redis_url, decode_responses=True)

# Remove hardcoded bot token
BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = telegram.Bot(token=BOT_TOKEN)

@app.route('/validate-key', methods=['POST'])
def validate_key():
    try:
        data = request.json
        key = data.get('key')
        if not key:
            return jsonify({
                'valid': False,
                'message': 'No key provided'
            }), 400

        print(f"Validating key: {key}")
        user_data = load_user_data()

        # Check if key exists in any user's data
        for user_info in user_data.values():
            if user_info.get('key') == key:
                try:
                    expiry_time = datetime.datetime.strptime(
                        user_info['expiry_time'], 
                        "%Y-%m-%d %H:%M:%S"
                    )
                    
                    if datetime.datetime.now() < expiry_time:
                        return jsonify({
                            'valid': True,
                            'message': 'Key validated successfully',
                            'expiryTime': user_info['expiry_time']
                        })
                except Exception as e:
                    print(f"Error processing key validation: {e}")

        return jsonify({
            'valid': False,
            'message': 'Invalid or expired key'
        })

    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({
            'valid': False,
            'message': f'Server error occurred: {str(e)}'
        }), 500

@app.route('/api/redis/recent-messages', methods=['GET', 'POST'])
def handle_recent_messages():
    if request.method == 'POST':
        data = request.json
        chat_id = data['chatId']
        message = data['message']
        key = f'recent_messages:{chat_id}'
        redis_client.lpush(key, json.dumps(message))
        redis_client.ltrim(key, 0, 9)  # Keep only last 10 messages
        return jsonify({'status': 'success'})
    else:
        chat_id = request.args.get('chatId')
        key = f'recent_messages:{chat_id}'
        messages = redis_client.lrange(key, 0, -1)
        return jsonify([json.loads(m) for m in messages])

@app.route('/api/chat', methods=['POST'])
def chat():
    api_key = os.getenv('GOOGLE_API_KEY')
    data = request.json
    
    # Handle the chat logic here with the API key
    settings = {
        'maxTokens': data.get('maxTokens'),
        'temperature': data.get('temperature'),
        'safetySettings': data.get('safetySettings'),
        'model': data.get('model')
    }
    
    # Your chat implementation here
    return jsonify({'response': 'chat response'})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'alive'})

@app.route('/webhook', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(), bot)
    # Your bot logic here
    return 'OK'

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
