from flask import Flask, request
from flask_socketio import SocketIO, emit
import requests
import time
import os
import logging
from datetime import datetime
import threading
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# Initialize SocketIO with CORS enabled and better error handling
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=True, engineio_logger=True)

# Configuration
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
MODEL_NAME = os.getenv('MODEL_NAME', 'llama2')  # Changed to a more common model name
MAX_RECONNECT_ATTEMPTS = 5
HEARTBEAT_INTERVAL = 30

# In-memory storage with better cleanup
active_users = {}
chat_history = []
MAX_HISTORY = 100
last_cleanup = time.time()
CLEANUP_INTERVAL = 300  # 5 minutes

def check_ollama_health():
    """Check if Ollama service is available"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            logger.info("Ollama service is healthy")
            return True
        else:
            logger.warning(f"Ollama health check failed with status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama service - connection refused")
        return False
    except requests.exceptions.Timeout:
        logger.error("Ollama health check timed out")
        return False
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        return False

def pull_model_if_needed():
    """Pull the model if it's not available"""
    try:
        logger.info("Checking if model needs to be pulled...")
        
        # Check if model exists
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_exists = any(MODEL_NAME in model.get('name', '') for model in models)
            
            if not model_exists:
                logger.info(f"Model {MODEL_NAME} not found. Pulling...")
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
                logger.info(f"Model {MODEL_NAME} is already available")
        else:
            logger.error(f"Failed to check available models: {response.status_code}")
                
    except Exception as e:
        logger.error(f"Error checking/pulling model: {e}")

def get_ai_response(message, context=""):
    """Enhanced AI response function with better error handling"""
    try:
        if not check_ollama_health():
            return "❌ AI service is currently unavailable. Please try again later."
        
        # Prepare a more structured prompt
        system_prompt = "You are a helpful AI assistant in a group chat. Keep responses concise, friendly, and under 200 words."
        
        if context:
            prompt = f"{system_prompt}\n\nRecent conversation:\n{context}\n\nUser question: {message}\n\nAssistant:"
        else:
            prompt = f"{system_prompt}\n\nUser: {message}\nAssistant:"
        
        logger.info(f"Sending prompt to Ollama (first 100 chars): {prompt[:100]}...")
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 200,
                    "stop": ["User:", "Assistant:", "\n\nUser:", "\n\nAssistant:"]
                }
            },
            timeout=45  # Increased timeout
        )
        
        logger.info(f"Ollama response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            ai_text = result.get('response', 'No response generated').strip()
            
            if not ai_text:
                return "🤔 I'm having trouble thinking of a response right now."
            
            # Clean up the response - remove excessive newlines and artifacts
            ai_text = ai_text.replace('\n\n', '\n').strip()
            
            # Remove any leftover prompt artifacts
            for stop_word in ["User:", "Assistant:", "Context:"]:
                if stop_word in ai_text:
                    ai_text = ai_text.split(stop_word)[0].strip()
            
            logger.info(f"AI response (first 100 chars): {ai_text[:100]}...")
            return ai_text
        else:
            logger.error(f"Ollama API error: {response.status_code} - {response.text}")
            return f"❌ Sorry, I couldn't process your request (Error: {response.status_code})"
            
    except requests.exceptions.Timeout:
        logger.error("AI request timed out")
        return "⏱️ Sorry, that request took too long. Please try again!"
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama service")
        return "❌ AI service is currently unavailable. Please check if Ollama is running."
    except Exception as e:
        logger.error(f"AI response error: {e}")
        return f"❌ Something went wrong: {str(e)}"

@app.route('/health')
def health_check():
    """Health check endpoint"""
    ollama_status = check_ollama_health()
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'ollama_available': ollama_status,
        'active_users': len(active_users),
        'chat_history_size': len(chat_history),
        'model': MODEL_NAME,
        'ollama_url': OLLAMA_URL
    }, 200

@app.route('/')
def index():
    """Basic index endpoint"""
    return {
        'message': 'Enhanced Chat Backend API with AI Integration',
        'version': '2.0',
        'endpoints': ['/health'],
        'socketio': 'enabled',
        'ai_integration': 'ollama',
        'model': MODEL_NAME
    }

@socketio.on('connect')
def handle_connect():
    """Enhanced connection handling"""
    try:
        logger.info(f"Client connected: {request.sid}")
        # Initialize user data
        active_users[request.sid] = {
            'username': None,
            'last_activity': time.time()
        }
        
        # Send connection response with more details
        emit('connect_response', {
            'status': 'connected',
            'sid': request.sid,
            'ai_available': check_ollama_health(),
            'server_time': time.time(),
            'active_users_count': len(active_users)
        })
        
        # Start periodic cleanup
        cleanup_inactive_users()
        
    except Exception as e:
        logger.error(f"Error in handle_connect: {e}")
        emit('error', {'message': 'Connection error occurred'})

@socketio.on('disconnect')
def handle_disconnect():
    """Enhanced disconnection handling"""
    try:
        logger.info(f"Client disconnected: {request.sid}")
        
        # Get username before removing
        user_data = active_users.get(request.sid, {})
        username = user_data.get('username')
        
        # Remove user from active users
        if request.sid in active_users:
            del active_users[request.sid]
        
        if username:
            logger.info(f"User {username} left the chat")
            
            # Notify other users about updated user list
            socketio.emit('active_users', list(set(u.get('username') for u in active_users.values() if u.get('username'))))
            
            # Add system message
            system_message = {
                'username': 'System',
                'message': f'👋 {username} left the chat',
                'timestamp': time.time(),
                'type': 'system'
            }
            chat_history.append(system_message)
            
            # Keep history manageable
            if len(chat_history) > MAX_HISTORY:
                chat_history.pop(0)
            
            socketio.emit('new_message', system_message)
            
    except Exception as e:
        logger.error(f"Error in handle_disconnect: {e}")

@socketio.on('join_chat')
def handle_join_chat(data):
    """Enhanced join chat handling with better validation"""
    try:
        username = data.get('username', '').strip()
        
        if not username:
            emit('error', {'message': 'Username is required'})
            return
        
        if len(username) > 50:
            emit('error', {'message': 'Username too long (max 50 characters)'})
            return
        
        # Check if username is already taken
        if any(u.get('username') == username for u in active_users.values()):
            emit('error', {'message': 'Username already taken'})
            return
        
        # Update user data
        active_users[request.sid] = {
            'username': username,
            'last_activity': time.time()
        }
        
        logger.info(f"User {username} joined chat (SID: {request.sid})")
        
        # Send chat history to new user
        emit('chat_history', chat_history)
        
        # Send updated active users list to all clients
        socketio.emit('active_users', list(set(u.get('username') for u in active_users.values() if u.get('username'))))
        
        # Add system message
        system_message = {
            'username': 'System',
            'message': f'🎉 {username} joined the chat',
            'timestamp': time.time(),
            'type': 'system'
        }
        chat_history.append(system_message)
        
        # Keep history manageable
        if len(chat_history) > MAX_HISTORY:
            chat_history.pop(0)
        
        # Broadcast system message to all clients
        socketio.emit('new_message', system_message)
        
        # Send success confirmation to the joining user
        emit('join_success', {'username': username})
        
    except Exception as e:
        logger.error(f"Error in handle_join_chat: {e}")
        emit('error', {'message': 'An error occurred while joining the chat'})

@socketio.on('send_message')
def handle_send_message(data):
    """Handle message sending with improved AI detection"""
    username = active_users.get(request.sid)
    if not username:
        emit('error', {'message': 'Not logged in'})
        return
    
    message = data.get('message', '').strip()
    if not message:
        return
    
    # Message length validation
    if len(message) > 1000:
        emit('error', {'message': 'Message too long (max 1000 characters)'})
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
    
    # Improved AI detection - more flexible triggers
    message_lower = message.lower()
    ai_triggers = ['@ai', '@bot', 'ai:', 'bot:', 'hey ai', 'ask ai', 'ai please', 'ai help']
    is_ai_request = any(trigger in message_lower for trigger in ai_triggers)
    
    # Also trigger AI if message is a question and mentions AI-related terms
    question_indicators = ['?', 'how', 'what', 'why', 'when', 'where', 'can you']
    ai_mentions = ['artificial intelligence', 'machine learning', 'algorithm']
    is_ai_question = any(q in message_lower for q in question_indicators) and any(ai in message_lower for ai in ai_mentions)
    
    if is_ai_request or is_ai_question:
        logger.info(f"AI request detected from {username}: {message[:100]}...")
        
        # Send immediate acknowledgment
        ack_message = {
            'username': 'System',
            'message': '🤖 AI is thinking...',
            'timestamp': time.time(),
            'type': 'system'
        }
        socketio.emit('new_message', ack_message)
        
        # Process AI request in background thread
        def process_ai_request():
            try:
                # Get recent context (last 5 messages excluding system messages)
                context_messages = [msg for msg in chat_history[-6:-1] if msg['type'] not in ['system', 'error']][-5:]
                context = "\n".join([f"{msg['username']}: {msg['message']}" 
                                   for msg in context_messages])
                
                # Clean the message for AI (remove trigger words)
                clean_message = message
                for trigger in ai_triggers:
                    clean_message = clean_message.replace(trigger, '').strip()
                
                # Remove common prefixes
                clean_message = clean_message.lstrip(',').strip()
                
                if not clean_message:
                    clean_message = "Hello! How can I help you?"
                
                logger.info(f"Sending to AI: {clean_message[:100]}...")
                
                # Get AI response
                ai_response = get_ai_response(clean_message, context)
                
                logger.info(f"AI responded (first 100 chars): {ai_response[:100]}...")
                
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
                logger.info("AI response broadcasted successfully")
                
            except Exception as e:
                logger.error(f"AI processing error: {e}")
                error_message = {
                    'username': 'System',
                    'message': f'❌ Sorry, the AI assistant encountered an error: {str(e)[:100]}',
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

@socketio.on('get_chat_history')
def handle_get_chat_history():
    """Handle request for chat history"""
    emit('chat_history', chat_history)

@socketio.on('ping')
def handle_ping():
    """Handle ping requests for connection testing"""
    emit('pong', {'timestamp': time.time()})

@app.route('/favicon.ico')
def favicon():
    return '', 204


@app.route('/debug-ai')
def debug_ai_endpoint():
    """Simple endpoint to test AI without SocketIO"""
    message = request.args.get('message', 'Hello')
    try:
        ai_response = get_ai_response(message)
        return {
            'success': True,
            'input': message,
            'output': ai_response,
            'timestamp': time.time()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'input': message
        }

# Error handlers
@socketio.on_error_default
def default_error_handler(e):
    """Default error handler for SocketIO events"""
    logger.error(f"SocketIO error: {e}")
    emit('error', {'message': 'An unexpected error occurred'})

@app.errorhandler(404)
def not_found(error):
    return {'error': 'Endpoint not found'}, 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return {'error': 'Internal server error'}, 500

def cleanup_inactive_users():
    """Clean up inactive users and old messages"""
    global last_cleanup
    current_time = time.time()
    
    if current_time - last_cleanup > CLEANUP_INTERVAL:
        # Remove inactive users
        inactive_sids = []
        for sid, user_data in active_users.items():
            if current_time - user_data.get('last_activity', 0) > 300:  # 5 minutes
                inactive_sids.append(sid)
        
        for sid in inactive_sids:
            username = active_users[sid].get('username')
            if username:
                logger.info(f"Cleaning up inactive user: {username}")
                del active_users[sid]
        
        # Trim chat history if too long
        while len(chat_history) > MAX_HISTORY:
            chat_history.pop(0)
        
        last_cleanup = current_time

if __name__ == '__main__':
    logger.info("🚀 Starting Enhanced Chat Backend...")
    logger.info(f"📡 Ollama URL: {OLLAMA_URL}")
    logger.info(f"🤖 AI Model: {MODEL_NAME}")
    logger.info(f"🔧 Environment: {'Production' if not app.debug else 'Development'}")
    
    # Check Ollama health on startup
    if check_ollama_health():
        logger.info("✅ Ollama service is available")
        # Check and pull model in background
        threading.Thread(target=pull_model_if_needed, daemon=True).start()
    else:
        logger.warning("⚠️  Ollama service not available - AI features will be disabled")
    
    # Run the application
    try:
        socketio.run(
            app, 
            host='0.0.0.0', 
            port=int(os.getenv('PORT', 5000)), 
            debug=os.getenv('DEBUG', 'False').lower() == 'true',
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        logger.info("👋 Shutting down chat backend...")
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        raise