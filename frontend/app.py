import streamlit as st
import socketio
import time
import threading
import queue
import os
from datetime import datetime
import requests

# Page configuration
st.set_page_config(
    page_title="Real-time Chat with AI",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')
<<<<<<< HEAD
RECONNECT_ATTEMPTS = 3
MESSAGE_REFRESH_INTERVAL = 5
=======
RECONNECT_ATTEMPTS = 5
MESSAGE_REFRESH_INTERVAL = 2
>>>>>>> origin/master

# Global queue to handle cross-thread communication
if 'global_message_queue' not in st.session_state:
    st.session_state.global_message_queue = queue.Queue()

# Initialize session state with better defaults
def init_session_state():
    defaults = {
        'messages': [],
        'username': "",
        'connected': False,
        'active_users': [],
        'sio': None,
        'connection_status': "disconnected",
        'last_message_id': 0,
        'connection_error': None,
        'auto_reconnect': True,
<<<<<<< HEAD
        'message_sending': False
=======
        'message_sending': False,
        'reconnect_attempts': 0,
        'last_reconnect': 0
>>>>>>> origin/master
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

class EnhancedChatClient:
    def __init__(self, message_queue):
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=RECONNECT_ATTEMPTS,
<<<<<<< HEAD
            reconnection_delay=2,
            reconnection_delay_max=10
        )
        self.message_queue = message_queue  # Pass queue as parameter
=======
            reconnection_delay=1,
            reconnection_delay_max=5,
            logger=True,
            engineio_logger=True
        )
        self.message_queue = message_queue
>>>>>>> origin/master
        self.setup_events()
        self.last_heartbeat = time.time()
    
    def setup_events(self):
        @self.sio.event
        def connect():
            self.last_heartbeat = time.time()
            self.message_queue.put(('connection_status', {
                'connected': True,
                'status': 'connected',
                'error': None,
                'message': '✅ Connected to chat server'
            }))
<<<<<<< HEAD
=======
            # Reset reconnect attempts on successful connection
            st.session_state.reconnect_attempts = 0
>>>>>>> origin/master
        
        @self.sio.event
        def disconnect():
            self.message_queue.put(('connection_status', {
                'connected': False,
                'status': 'disconnected',
                'error': None,
                'message': '❌ Disconnected from chat server'
            }))
<<<<<<< HEAD
        
        @self.sio.event
        def connect_error(data):
            self.message_queue.put(('connection_status', {
                'connected': False,
                'status': 'error',
                'error': str(data),
                'message': f'❌ Connection error: {data}'
            }))
=======
            # Attempt to reconnect if auto_reconnect is enabled
            if st.session_state.auto_reconnect:
                current_time = time.time()
                if current_time - st.session_state.last_reconnect > 5:  # Prevent rapid reconnection attempts
                    st.session_state.last_reconnect = current_time
                    st.session_state.reconnect_attempts += 1
                    if st.session_state.reconnect_attempts <= RECONNECT_ATTEMPTS:
                        self.connect()
        
        @self.sio.event
        def connect_error(data):
            error_msg = str(data)
            self.message_queue.put(('connection_status', {
                'connected': False,
                'status': 'error',
                'error': error_msg,
                'message': f'❌ Connection error: {error_msg}'
            }))
            # Log the error for debugging
            print(f"Connection error: {error_msg}")
>>>>>>> origin/master
        
        @self.sio.event
        def reconnect():
            self.message_queue.put(('status', '🔄 Reconnected to chat server'))
            # Re-join chat after reconnection would need to be handled in main thread
        
        @self.sio.event
        def new_message(data):
            # Add message ID to prevent duplicates
            if 'id' not in data:
                data['id'] = f"{data.get('timestamp', time.time())}_{data.get('username', 'unknown')}"
            self.message_queue.put(('message', data))
        
        @self.sio.event
        def chat_history(data):
            self.message_queue.put(('history', data))
        
        @self.sio.event
        def active_users(data):
            self.message_queue.put(('users', data))
        
        @self.sio.event
        def error(data):
            self.message_queue.put(('error', data.get('message', 'Unknown error')))
        
        @self.sio.event
        def message_sent():
            self.message_queue.put(('message_sent', True))
    
    def connect(self):
        try:
            if self.sio.connected:
                return True
            
            self.message_queue.put(('connection_status', {
                'connected': False,
                'status': 'connecting',
                'error': None,
                'message': 'Connecting...'
            }))
            
            # Test backend health first
            try:
                response = requests.get(f"{BACKEND_URL}/health", timeout=5)
                if response.status_code != 200:
                    raise Exception(f"Backend unhealthy: {response.status_code}")
            except Exception as e:
                self.message_queue.put(('connection_status', {
                    'connected': False,
                    'status': 'error',
                    'error': f"Backend not available: {e}",
                    'message': f"Backend not available: {e}"
                }))
                return False
            
            self.sio.connect(BACKEND_URL)
            return True
            
        except Exception as e:
            self.message_queue.put(('connection_status', {
                'connected': False,
                'status': 'error',
                'error': str(e),
                'message': f"Connection failed: {e}"
            }))
            return False
    
    def disconnect(self):
        try:
            if self.sio.connected:
                self.sio.disconnect()
        except Exception as e:
            print(f"Disconnect error: {e}")
    
    def join_chat(self, username):
        if self.sio.connected and username:
            self.sio.emit('join_chat', {'username': username})
            return True
        return False
    
    def send_message(self, message):
        if self.sio.connected and message.strip():
            self.sio.emit('send_message', {'message': message.strip()})
            return True
        return False
    
    def is_healthy(self):
        """Check connection health"""
        if not self.sio.connected:
            return False
        
        # Check if we haven't received any events recently
        if time.time() - self.last_heartbeat > 30:
            return False
        
        return True
    


def process_message_queue():
    """Enhanced message queue processing with deduplication"""
    processed = 0
    seen_message_ids = set()
    
    while not st.session_state.global_message_queue.empty() and processed < 20:
        try:
            msg_type, data = st.session_state.global_message_queue.get_nowait()
            
            if msg_type == 'connection_status':
                # Update connection state
                st.session_state.connected = data['connected']
                st.session_state.connection_status = data['status']
                st.session_state.connection_error = data['error']
                st.session_state.last_status = data['message']
                
            elif msg_type == 'message':
                # Prevent duplicate messages
                msg_id = data.get('id', f"{data.get('timestamp', time.time())}")
                if msg_id not in seen_message_ids:
                    seen_message_ids.add(msg_id)
                    st.session_state.messages.append(data)
                    
            elif msg_type == 'history':
                st.session_state.messages = data
                
            elif msg_type == 'users':
                st.session_state.active_users = data
                
            elif msg_type == 'status':
                # Show status in a temporary notification
                st.session_state.last_status = data
                
            elif msg_type == 'error':
                st.session_state.last_error = data
                
            elif msg_type == 'message_sent':
                st.session_state.message_sending = False
                st.session_state.last_status = '✅ Message sent'
            
            processed += 1
                
        except queue.Empty:
            break

def format_timestamp(timestamp):
    """Format timestamp for display"""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%H:%M:%S")
    except:
        return datetime.now().strftime("%H:%M:%S")

def validate_message(message):
    """Validate message before sending"""
    if not message or not message.strip():
        return False, "Message cannot be empty"
    
    if len(message) > 500:
        return False, "Message too long (max 500 characters)"
    
    # Basic spam detection
    if message.count('!') > 10 or message.count('?') > 10:
        return False, "Message appears to be spam"
    
    return True, ""

def get_connection_status_color():
    """Get color for connection status"""
    status = st.session_state.connection_status
    colors = {
        'connected': '🟢',
        'connecting': '🟡', 
        'disconnected': '⚪',
        'error': '🔴'
    }
    return colors.get(status, '⚪')

# Custom CSS for better UI
st.markdown("""
<style>
.message-container {
    padding: 10px;
    margin: 5px 0;
    border-radius: 10px;
    border-left: 4px solid;
}
.user-message {
    background-color: #e3f2fd;
    border-left-color: #2196f3;
}
.ai-message {
    background-color: #f3e5f5;
    border-left-color: #9c27b0;
}
.system-message {
    background-color: #fff3e0;
    border-left-color: #ff9800;
    font-style: italic;
}
.error-message {
    background-color: #ffebee;
    border-left-color: #f44336;
}
.status-indicator {
    position: fixed;
    top: 10px;
    right: 10px;
    z-index: 1000;
    padding: 5px 10px;
    border-radius: 5px;
    background: white;
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}
</style>
""", unsafe_allow_html=True)

# Process messages from background threads
process_message_queue()

# Main UI
st.title("💬 Real-time Chat with AI Assistant")

# Status indicator
status_color = get_connection_status_color()
st.markdown(f"""
<div class="status-indicator">
{status_color} {st.session_state.connection_status.title()}
</div>
""", unsafe_allow_html=True)

# Show last status message if available
if hasattr(st.session_state, 'last_status'):
    st.info(st.session_state.last_status)
    # Clear after showing
    delattr(st.session_state, 'last_status')

# Show last error if available
if hasattr(st.session_state, 'last_error'):
    st.error(f"❌ {st.session_state.last_error}")
    # Clear after showing
    delattr(st.session_state, 'last_error')

st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("🎮 Chat Controls")
    
    # Connection Management
    st.subheader("Connection")
    
    if not st.session_state.connected:
        # Username input with validation
        username_input = st.text_input(
            "Username (3-20 characters):", 
            value=st.session_state.username,
            max_chars=20,
            key="username_input"
        )
        
        # Validate username
        username_valid = len(username_input.strip()) >= 3 if username_input else False
        
        if st.button("🚀 Join Chat", type="primary", disabled=not username_valid):
            st.session_state.username = username_input.strip()
            
            # Clean up existing connection
            if st.session_state.sio:
                try:
                    st.session_state.sio.disconnect()
                except:
                    pass
            
            # Create new client with the global queue
            st.session_state.sio = EnhancedChatClient(st.session_state.global_message_queue)
            
            with st.spinner("Connecting to chat..."):
                if st.session_state.sio.connect():
                    # Wait a moment for connection to establish
                    time.sleep(1)
                    if st.session_state.connected:  # Check if connection was successful
                        if st.session_state.sio.join_chat(st.session_state.username):
                            st.success("✅ Connected successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Failed to join chat")
                else:
                    st.error(f"❌ Connection failed")
        
        if not username_valid and username_input:
            st.warning("Username must be 3-20 characters long")
            
        # Show connection error if any
        if st.session_state.connection_error:
            st.error(f"Connection Error: {st.session_state.connection_error}")
    
    else:
        st.success(f"✅ Connected as: **{st.session_state.username}**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚪 Leave", type="secondary"):
                if st.session_state.sio:
                    st.session_state.sio.disconnect()
                
                # Reset state
                for key in ['connected', 'username', 'messages', 'active_users']:
                    if key in st.session_state:
                        if key == 'messages':
                            st.session_state[key] = []
                        elif key == 'active_users':
                            st.session_state[key] = []
                        else:
                            st.session_state[key] = "" if key == 'username' else False
                
                st.session_state.connection_status = "disconnected"
                st.session_state.sio = None
                st.rerun()
        
        with col2:
            if st.button("🔄 Reconnect"):
                if st.session_state.sio:
                    st.session_state.sio.connect()
    
    st.markdown("---")
    
    # Active Users
    st.subheader("👥 Active Users")
    if st.session_state.active_users:
        for i, user in enumerate(st.session_state.active_users):
            icon = "👑" if user == st.session_state.username else "👤"
            st.write(f"{icon} {user}")
    else:
        st.write("No users online")
    
    st.markdown("---")
    
    # Statistics
    st.subheader("📊 Stats")
    st.metric("Messages", len(st.session_state.messages))
    st.metric("Online Users", len(st.session_state.active_users))
    
    st.markdown("---")
    
    # Instructions
    st.subheader("💡 How to Use")
    st.markdown("""
    • Type messages normally for group chat
    • Use `@ai` or `@bot` to talk to AI
    • Press Enter or click Send
    • AI responses may take a few seconds
    """)

# Main Chat Area
if st.session_state.connected:
    # Chat Messages
    st.subheader("💬 Messages")
    
    # Message container with scrolling
    messages_container = st.container()
    
    with messages_container:
        if st.session_state.messages:
            # Show recent messages (last 50)
            recent_messages = st.session_state.messages[-50:]
            
            for msg in recent_messages:
                timestamp = format_timestamp(msg.get('timestamp', time.time()))
                msg_type = msg.get('type', 'user')
                username = msg.get('username', 'Unknown')
                message = msg.get('message', '')
                
                # Message styling based on type
                if msg_type == 'system':
                    st.markdown(f"""
                    <div class="message-container system-message">
                        <small><strong>{timestamp}</strong></small><br>
                        <em>{message}</em>
                    </div>
                    """, unsafe_allow_html=True)
                
                elif msg_type == 'ai':
                    st.markdown(f"""
                    <div class="message-container ai-message">
                        <small><strong>🤖 {username} • {timestamp}</strong></small><br>
                        {message}
                    </div>
                    """, unsafe_allow_html=True)
                
                elif msg_type == 'error':
                    st.markdown(f"""
                    <div class="message-container error-message">
                        <small><strong>❌ Error • {timestamp}</strong></small><br>
                        {message}
                    </div>
                    """, unsafe_allow_html=True)
                
                else:  # user message
                    icon = "👑" if username == st.session_state.username else "👤"
                    st.markdown(f"""
                    <div class="message-container user-message">
                        <small><strong>{icon} {username} • {timestamp}</strong></small><br>
                        {message}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("💬 No messages yet. Start the conversation!")
    
    st.markdown("---")
    
    # Message Input - Enhanced
    st.subheader("✍️ Send Message")
    
    # Message input form
    with st.form("message_form", clear_on_submit=True):
        message_input = st.text_area(
            "Your message:",
            placeholder="Type your message here... Use @ai to ask the AI assistant",
            max_chars=500,
            height=100,
            key="message_text"
        )
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            send_clicked = st.form_submit_button("📤 Send Message", type="primary")
        
        with col2:
            chars_left = 500 - len(message_input) if message_input else 500
            st.caption(f"Characters left: {chars_left}")
        
        with col3:
            if st.session_state.message_sending:
                st.caption("Sending...")
        
        # Handle message sending
        if send_clicked and message_input:
            is_valid, error_msg = validate_message(message_input)
            
            if is_valid:
                if st.session_state.sio and st.session_state.sio.send_message(message_input):
                    st.session_state.message_sending = True
                    st.success("✅ Message sent!")
                else:
                    st.error("❌ Failed to send message")
            else:
                st.error(f"❌ {error_msg}")
    
    # Auto-refresh with reduced frequency
    time.sleep(MESSAGE_REFRESH_INTERVAL)
    st.rerun()

else:
    # Not connected state
    st.info("👈 Please join the chat to start messaging!")
    
    # Connection diagnostics
    st.subheader("🔧 Connection Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Status", st.session_state.connection_status.title())
        st.metric("Backend URL", BACKEND_URL)
    
    with col2:
        # Test backend connectivity
        if st.button("🩺 Test Backend"):
            try:
                with st.spinner("Testing connection..."):
                    response = requests.get(f"{BACKEND_URL}/health", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        st.success("✅ Backend is healthy!")
                        st.json(data)
                    else:
                        st.error(f"❌ Backend returned {response.status_code}")
            except Exception as e:
                st.error(f"❌ Cannot reach backend: {e}")
    
    # Show error details if available
    if st.session_state.connection_error:
        st.error(f"Last Error: {st.session_state.connection_error}")
    
    # Slower refresh when disconnected
    time.sleep(10)
    st.rerun()