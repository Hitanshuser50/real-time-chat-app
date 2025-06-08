import streamlit as st
import socketio
import time
import threading
import queue
import os
from datetime import datetime
import extra_streamlit_components as stx

# Page configuration
st.set_page_config(
    page_title="Real-time Chat with AI",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'active_users' not in st.session_state:
    st.session_state.active_users = []
if 'message_queue' not in st.session_state:
    st.session_state.message_queue = queue.Queue()
if 'sio' not in st.session_state:
    st.session_state.sio = None

class ChatClient:
    def __init__(self):
        self.sio = socketio.Client()
        self.setup_events()
    
    def setup_events(self):
        @self.sio.event
        def connect():
            st.session_state.connected = True
            st.session_state.message_queue.put(('status', 'Connected to chat server'))
        
        @self.sio.event
        def disconnect():
            st.session_state.connected = False
            st.session_state.message_queue.put(('status', 'Disconnected from chat server'))
        
        @self.sio.event
        def new_message(data):
            st.session_state.message_queue.put(('message', data))
        
        @self.sio.event
        def chat_history(data):
            st.session_state.message_queue.put(('history', data))
        
        @self.sio.event
        def active_users(data):
            st.session_state.message_queue.put(('users', data))
    
    def connect(self):
        try:
            self.sio.connect(BACKEND_URL)
            return True
        except Exception as e:
            st.error(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        if self.sio.connected:
            self.sio.disconnect()
    
    def join_chat(self, username):
        self.sio.emit('join_chat', {'username': username})
    
    def send_message(self, message):
        self.sio.emit('send_message', {'message': message})
    
    def get_active_users(self):
        self.sio.emit('get_active_users')

def process_message_queue():
    """Process messages from the queue and update session state"""
    while not st.session_state.message_queue.empty():
        try:
            msg_type, data = st.session_state.message_queue.get_nowait()
            
            if msg_type == 'message':
                st.session_state.messages.append(data)
            elif msg_type == 'history':
                st.session_state.messages = data
            elif msg_type == 'users':
                st.session_state.active_users = data
            elif msg_type == 'status':
                st.info(data)
                
        except queue.Empty:
            break

def format_timestamp(timestamp):
    """Format timestamp for display"""
    return datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")

def get_message_style(msg_type):
    """Get CSS style for different message types"""
    styles = {
        'user': 'background-color: #e1f5fe; border-left: 4px solid #2196f3;',
        'ai': 'background-color: #f3e5f5; border-left: 4px solid #9c27b0;',
        'system': 'background-color: #fff3e0; border-left: 4px solid #ff9800;',
        'error': 'background-color: #ffebee; border-left: 4px solid #f44336;'
    }
    return styles.get(msg_type, '')

# Main UI
st.title("💬 Real-time Chat with AI")
st.markdown("---")

# Sidebar for user management
with st.sidebar:
    st.header("Chat Controls")
    
    # Username input
    if not st.session_state.connected:
        username_input = st.text_input("Enter your username:", key="username_input")
        
        if st.button("Join Chat", type="primary"):
            if username_input.strip():
                st.session_state.username = username_input.strip()
                
                # Initialize chat client
                if st.session_state.sio is None:
                    st.session_state.sio = ChatClient()
                
                if st.session_state.sio.connect():
                    st.session_state.sio.join_chat(st.session_state.username)
                    st.rerun()
                else:
                    st.error("Failed to connect to chat server")
            else:
                st.warning("Please enter a username")
    
    else:
        st.success(f"Connected as: **{st.session_state.username}**")
        
        if st.button("Leave Chat", type="secondary"):
            if st.session_state.sio:
                st.session_state.sio.disconnect()
            st.session_state.connected = False
            st.session_state.username = ""
            st.session_state.messages = []
            st.session_state.active_users = []
            st.session_state.sio = None
            st.rerun()
    
    st.markdown("---")
    
    # Active users
    st.subheader("Active Users")
    if st.session_state.active_users:
        for user in st.session_state.active_users:
            st.write(f"👤 {user}")
    else:
        st.write("No active users")
    
    st.markdown("---")
    
    # Instructions
    st.subheader("How to use:")
    st.markdown("""
    - Type your message in the chat input
    - Use `@ai` or `@bot` to ask the AI assistant
    - Messages are shared with all users in real-time
    """)

# Main chat area
if st.session_state.connected:
    # Process any pending messages
    process_message_queue()
    
    # Chat history container
    chat_container = st.container()
    
    with chat_container:
        st.subheader("Chat Messages")
        
        # Display messages
        for msg in st.session_state.messages:
            msg_time = format_timestamp(msg['timestamp'])
            msg_type = msg.get('type', 'user')
            
            with st.container():
                style = get_message_style(msg_type)
                
                if msg_type == 'system':
                    st.markdown(f"""
                    <div style="padding: 10px; margin: 5px 0; border-radius: 5px; {style}">
                        <small><strong>{msg_time}</strong></small><br>
                        <em>{msg['message']}</em>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    icon = "🤖" if msg_type == 'ai' else "👤"
                    st.markdown(f"""
                    <div style="padding: 10px; margin: 5px 0; border-radius: 5px; {style}">
                        <small><strong>{icon} {msg['username']} - {msg_time}</strong></small><br>
                        {msg['message']}
                    </div>
                    """, unsafe_allow_html=True)
    
    # Message input
    st.markdown("---")
    
    # Use columns for better layout
    col1, col2 = st.columns([4, 1])
    
    with col1:
        message_input = st.text_input(
            "Type your message:", 
            key="message_input",
            placeholder="Enter your message here... (use @ai to ask the AI assistant)"
        )
    
    with col2:
        send_button = st.button("Send", type="primary")
    
    # Send message
    if send_button or (message_input and st.session_state.get('enter_pressed', False)):
        if message_input.strip():
            st.session_state.sio.send_message(message_input.strip())
            st.session_state['message_input'] = ""  # Clear input
            st.rerun()
    
    # Auto-refresh to get new messages
    time.sleep(0.5)
    st.rerun()

else:
    st.info("👈 Please enter a username and join the chat to start messaging!")
    
    # Show connection status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Connection Status", "Disconnected", delta="Offline")
    
    with col2:
        st.metric("Active Users", len(st.session_state.active_users))
    
    with col3:
        st.metric("Messages", len(st.session_state.messages))

# Auto-refresh for real-time updates
if st.session_state.connected:
    time.sleep(1)
    st.rerun()