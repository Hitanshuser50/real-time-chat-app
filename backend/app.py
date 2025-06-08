import os
import time
import requests
import threading
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app, resources={r"/*": {"origins": "*"}})

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Configuration
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
MODEL_NAME = 'llama3.2:1b'  # Using smaller model for better performance

# Store active users and chat history
active_users = {}
chat_history = []

class OllamaClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.model_loaded = False
        
    def wait_for_ollama(self, max_retries=30):
        """Wait for Ollama service to be ready"""
        for i in range(max_retries):
            try:
                response = requests.get(f"{self.base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    print("Ollama service is ready!")
                    return True
            except requests.exceptions.RequestException:
                print(f"Waiting for Ollama service... ({i+1}/{max_retries})")
                time.sleep(2)
        return False
    
    def ensure_model_loaded(self):
        """Pull the model if not already available"""
        if self.model_loaded:
            return True
            
        try:
            # Check if model exists
            response = requests.get(f"{self.base_url}/api/tags")
            models = response.json()
            
            model_exists = any(MODEL_NAME in model['name'] for model in models.get('models', []))
            
            if not model_exists:
                print(f"Pulling model {MODEL_NAME}...")
                pull_response = requests.post(
                    f"{self.base_url}/api/pull",
                    json={"name": MODEL_NAME},
                    stream=True,
                    timeout=300
                )
                
                for line in pull_response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if data.get('status') == 'success':
                                print(f"Model {MODEL_NAME} pulled successfully!")
                                break
                        except json.JSONDecodeError:
                            continue
            
            self.model_loaded = True
            return True
            
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def generate_response(self, prompt, context=""):
        """Generate response from Ollama"""
        try:
            full_prompt = f"{context}\nUser: {prompt}\nAssistant:"
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": MODEL_NAME,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 512
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', 'Sorry, I could not generate a response.')
            else:
                return f"Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error generating response: {str(e)}"

# Initialize Ollama client
ollama_client = OllamaClient(OLLAMA_URL)

def initialize_ollama():
    """Initialize Ollama in a separate thread"""
    print("Initializing Ollama...")
    if ollama_client.wait_for_ollama():
        if ollama_client.ensure_model_loaded():
            print("Ollama initialization complete!")
        else:
            print("Failed to load model!")
    else:
        print("Failed to connect to Ollama service!")

# Start Ollama initialization in background
threading.Thread(target=initialize_ollama, daemon=True).start()

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    # Send chat history to new user
    emit('chat_history', chat_history)

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')
    # Remove user from active users
    if request.sid in active_users:
        username = active_users[request.sid]['username']
        del active_users[request.sid]
        emit('user_left', {'username': username}, broadcast=True)
        emit('active_users', list(set(user['username'] for user in active_users.values())), broadcast=True)

@socketio.on('join_chat')
def handle_join_chat(data):
    username = data['username']
    active_users[request.sid] = {
        'username': username,
        'joined_at': time.time()
    }
    
    join_message = {
        'username': 'System',
        'message': f'{username} joined the chat',
        'timestamp': time.time(),
        'type': 'system'
    }
    
    chat_history.append(join_message)
    emit('new_message', join_message, broadcast=True)
    emit('active_users', list(set(user['username'] for user in active_users.values())), broadcast=True)

@socketio.on('send_message')
def handle_message(data):
    if request.sid not in active_users:
        return
    
    username = active_users[request.sid]['username']
    message = data['message']
    
    # Store user message
    user_message = {
        'username': username,
        'message': message,
        'timestamp': time.time(),
        'type': 'user'
    }
    
    chat_history.append(user_message)
    emit('new_message', user_message, broadcast=True)
    
    # Check if message is directed to AI (starts with @ai or @bot)
    if message.lower().startswith('@ai ') or message.lower().startswith('@bot '):
        # Extract the actual question
        ai_prompt = message[4:].strip()  # Remove @ai or @bot prefix
        
        # Generate context from recent chat history
        context = "\n".join([
            f"{msg['username']}: {msg['message']}" 
            for msg in chat_history[-10:] 
            if msg['type'] == 'user'
        ])
        
        # Generate AI response in a separate thread to avoid blocking
        def generate_ai_response():
            try:
                ai_response = ollama_client.generate_response(ai_prompt, context)
                
                ai_message = {
                    'username': 'AI Assistant',
                    'message': ai_response,
                    'timestamp': time.time(),
                    'type': 'ai'
                }
                
                chat_history.append(ai_message)
                socketio.emit('new_message', ai_message)
                
            except Exception as e:
                error_message = {
                    'username': 'System',
                    'message': f'AI Error: {str(e)}',
                    'timestamp': time.time(),
                    'type': 'error'
                }
                socketio.emit('new_message', error_message)
        
        threading.Thread(target=generate_ai_response, daemon=True).start()

@socketio.on('get_active_users')
def handle_get_active_users():
    emit('active_users', list(set(user['username'] for user in active_users.values())))

@app.route('/health')
def health_check():
    return {'status': 'healthy', 'ollama_url': OLLAMA_URL}

if __name__ == '__main__':
    print(f"Starting chat server on port 5000...")
    print(f"Ollama URL: {OLLAMA_URL}")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)