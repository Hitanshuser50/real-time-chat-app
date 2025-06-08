from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import requests
import time
import os
import logging
from datetime import datetime
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

# Initialize SocketIO with CORS enabled
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Configuration
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
MODEL_NAME = 'llama3.2:1b'  # Using smaller model for better performance

# In-memory storage (use Redis for production)
active_users = {}
chat_history = []
MAX_HISTORY = 100

def check_ollama_health():
    """Check if Ollama service is available"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        return False

def pull_model_if_needed():
    """Pull the model if it's not available"""
    try:
        # Check if model exists
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_exists = any(MODEL_NAME in model.get('name', '') for model in models)
            
            if not model_exists:
                logger.info(f"Pulling model {MODEL_NAME}...")
                pull_response = requests.post(
                    f"{OLLAMA_URL}/api/pull",
                    json={"name": MODEL_NAME},
                    timeout=300  # 5 minutes timeout for model pull
                )
                if pull_response.status_code == 200:
                    logger.info(f"Successfully pulled model {MODEL_NAME}")
                else:
                    logger.error(f"Failed to pull model: {pull_response.text}")
            else:
                logger.info(f"Model {MODEL_NAME} already available")
                
    except Exception as e:
        logger.error(f"Error checking/pulling model: {e}")

def get_ai_response(message, context=""):
    """Get response from Ollama AI"""
    try:
        if not check_ollama_health():
            return "❌ AI service is currently unavailable. Please try again later."
        
        # Prepare the prompt
        prompt = f"Context: {context}\nUser: {message}\nAssistant:"
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 150
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', 'No response generated')
        else:
            logger.error(f"Ollama API error: {response.status_code} - {response.text}")
            return "❌ Sorry, I couldn't process your request right now."
            
    except requests.exceptions.Timeout:
        return "⏱️ Request timed out. The AI is thinking too hard!"
    except Exception as e:
        logger.error(f"AI response error: {e}")
        return "❌ Something went wrong while getting AI response."

@app.route('/health')
def health_check():
    """Health check endpoint"""
    ollama_status = check_ollama_health()
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'ollama_available': ollama_status,
        'active_users': len(active_users),
        'chat_history_size': len(chat_history)
    }, 200

@app.route('/')
def index():
    """Basic index endpoint"""
    return {
        'message': 'Chat Backend API',
        'endpoints': ['/health'],
        'socketio': 'enabled'
    }

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connect_response', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")
    
    # Remove user from active users
    username = active_users.pop(request.sid, None)
    if username:
        # Notify other users
        socketio.emit('active_users', list(set(active_users.values())))
        
        # Add system message
        system_message = {
            'username': 'System',
            'message': f'{username} left the chat',
            'timestamp': time.time(),
            'type': 'system'
        }
        chat_history.append(system_message)
        
        # Keep history manageable
        if len(chat_history) > MAX_HISTORY:
            chat_history.pop(0)
        
        socketio.emit('new_message', system_message)

@socketio.on('join_chat')
def handle_join_chat(data):
    """Handle user joining chat"""
    username = data.get('username', '').strip()
    
    if not username:
        emit('error', {'message': 'Username is required'})
        return
    
    # Check if username is already taken
    if username in active_users.values():
        emit('error', {'message': 'Username already taken'})
        return
    
    # Add user to active users
    active_users[request.sid] = username
    
    logger.info(f"User {username} joined chat")
    
    # Send chat history to new user
    emit('chat_history', chat_history)
    
    # Send updated active users list to all clients
    socketio.emit('active_users', list(set(active_users.values())))
    
    # Add system message
    system_message = {
        'username': 'System',
        'message': f'{username} joined the chat',
        'timestamp': time.time(),
        'type': 'system'
    }
    chat_history.append(system_message)
    
    # Keep history manageable
    if len(chat_history) > MAX_HISTORY:
        chat_history.pop(0)
    
    # Broadcast system message to all clients
    socketio.emit('new_message', system_message)

@socketio.on('send_message')
def handle_send_message(data):
    """Handle message sending"""
    username = active_users.get(request.sid)
    if not username:
        emit('error', {'message': 'Not logged in'})
        return
    
    message = data.get('message', '').strip()
    if not message:
        return
    
    # Create message object
    user_message = {
        'username': username,
        'message': message,
        'timestamp': time.time(),
        'type': 'user'
    }
    
    # Add to history
    chat_history.append(user_message)
    
    # Broadcast message to all clients
    socketio.emit('new_message', user_message)
    
    # Check if it's an AI request
    if message.lower().startswith(('@ai', '@bot')) or 'ai' in message.lower():
        # Process AI request in background thread
        def process_ai_request():
            try:
                # Get recent context (last 5 messages)
                context_messages = chat_history[-5:-1] if len(chat_history) > 1 else []
                context = "\n".join([f"{msg['username']}: {msg['message']}" 
                                   for msg in context_messages if msg['type'] != 'system'])
                
                # Get AI response
                ai_response = get_ai_response(message, context)
                
                # Create AI message
                ai_message = {
                    'username': 'AI Assistant',
                    'message': ai_response,
                    'timestamp': time.time(),
                    'type': 'ai'
                }
                
                # Add to history
                chat_history.append(ai_message)
                
                # Keep history manageable
                if len(chat_history) > MAX_HISTORY:
                    chat_history.pop(0)
                
                # Broadcast AI response
                socketio.emit('new_message', ai_message)
                
            except Exception as e:
                logger.error(f"AI processing error: {e}")
                error_message = {
                    'username': 'System',
                    'message': 'Sorry, the AI assistant encountered an error.',
                    'timestamp': time.time(),
                    'type': 'error'
                }
                socketio.emit('new_message', error_message)
        
        # Start AI processing in background
        threading.Thread(target=process_ai_request, daemon=True).start()
    
    # Keep history manageable
    if len(chat_history) > MAX_HISTORY:
        chat_history.pop(0)

@socketio.on('get_active_users')
def handle_get_active_users():
    """Handle request for active users"""
    emit('active_users', list(set(active_users.values())))

if __name__ == '__main__':
    logger.info("Starting Chat Backend...")
    logger.info(f"Ollama URL: {OLLAMA_URL}")
    logger.info(f"Model: {MODEL_NAME}")
    
    # Check Ollama and pull model in background
    threading.Thread(target=pull_model_if_needed, daemon=True).start()
    
    # Run the application
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)