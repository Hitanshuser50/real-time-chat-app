#!/usr/bin/env python3
"""
Integration test script for the real-time chat application.
Tests the core functionality including Socket.IO connections and AI responses.
"""

import requests
import socketio
import time
import threading
import sys
from datetime import datetime

class ChatTester:
    def __init__(self, backend_url="http://localhost:5000"):
        self.backend_url = backend_url
        self.sio = socketio.Client()
        self.messages_received = []
        self.connected = False
        self.setup_events()
    
    def setup_events(self):
        @self.sio.event
        def connect():
            self.connected = True
            print("✅ Connected to chat server")
        
        @self.sio.event
        def disconnect():
            self.connected = False
            print("❌ Disconnected from chat server")
        
        @self.sio.event
        def new_message(data):
            self.messages_received.append(data)
            timestamp = datetime.fromtimestamp(data['timestamp']).strftime("%H:%M:%S")
            print(f"📨 [{timestamp}] {data['username']}: {data['message']}")
        
        @self.sio.event
        def chat_history(data):
            print(f"📚 Received chat history: {len(data)} messages")
        
        @self.sio.event
        def active_users(data):
            print(f"👥 Active users: {data}")
    
    def test_backend_health(self):
        """Test if backend is running and healthy"""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Backend health check passed")
                return True
            else:
                print(f"❌ Backend health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Backend health check failed: {e}")
            return False
    
    def test_connection(self):
        """Test Socket.IO connection"""
        try:
            self.sio.connect(self.backend_url)
            time.sleep(1)
            if self.connected:
                print("✅ Socket.IO connection test passed")
                return True
            else:
                print("❌ Socket.IO connection test failed")
                return False
        except Exception as e:
            print(f"❌ Socket.IO connection test failed: {e}")
            return False
    
    def test_join_chat(self, username="TestUser"):
        """Test joining the chat"""
        try:
            self.sio.emit('join_chat', {'username': username})
            time.sleep(1)
            print(f"✅ Joined chat as {username}")
            return True
        except Exception as e:
            print(f"❌ Join chat test failed: {e}")
            return False
    
    def test_send_message(self, message="Hello, this is a test message!"):
        """Test sending a regular message"""
        try:
            initial_count = len(self.messages_received)
            self.sio.emit('send_message', {'message': message})
            
            # Wait for message to be received
            timeout = 5
            while len(self.messages_received) <= initial_count and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
            
            if len(self.messages_received) > initial_count:
                print("✅ Send message test passed")
                return True
            else:
                print("❌ Send message test failed - no message received")
                return False
        except Exception as e:
            print(f"❌ Send message test failed: {e}")
            return False
    
    def test_ai_response(self, ai_message="@ai What is 2+2?"):
        """Test AI assistant response"""
        try:
            initial_count = len(self.messages_received)
            self.sio.emit('send_message', {'message': ai_message})
            
            # Wait for both user message and AI response
            timeout = 30  # AI responses can take longer
            ai_response_received = False
            
            while timeout > 0:
                # Check if we received an AI response
                for msg in self.messages_received[initial_count:]:
                    if msg.get('type') == 'ai' or msg.get('username') == 'AI Assistant':
                        ai_response_received = True
                        break
                
                if ai_response_received:
                    break
                
                time.sleep(0.5)
                timeout -= 0.5
            
            if ai_response_received:
                print("✅ AI response test passed")
                return True
            else:
                print("❌ AI response test failed - no AI response received")
                return False
        except Exception as e:
            print(f"❌ AI response test failed: {e}")
            return False
    
    def test_ollama_service(self):
        """Test Ollama service directly"""
        try:
            # Test Ollama API
            ollama_url = "http://localhost:11434"
            response = requests.get(f"{ollama_url}/api/tags", timeout=10)
            
            if response.status_code == 200:
                models = response.json()
                print(f"✅ Ollama service is running with {len(models.get('models', []))} models")
                return True
            else:
                print(f"❌ Ollama service test failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ollama service test failed: {e}")
            return False
    
    def disconnect_client(self):
        """Disconnect the test client"""
        if self.sio.connected:
            self.sio.disconnect()
            print("🔌 Disconnected from chat server")

def run_tests():
    """Run all integration tests"""
    print("🧪 Starting Real-time Chat Application Integration Tests")
    print("=" * 60)
    
    tester = ChatTester()
    tests_passed = 0
    total_tests = 6
    
    try:
        # Test 1: Backend Health
        print("\n1️⃣ Testing Backend Health...")
        if tester.test_backend_health():
            tests_passed += 1
        
        # Test 2: Ollama Service
        print("\n2️⃣ Testing Ollama Service...")
        if tester.test_ollama_service():
            tests_passed += 1
        
        # Test 3: Socket.IO Connection
        print("\n3️⃣ Testing Socket.IO Connection...")
        if tester.test_connection():
            tests_passed += 1
        
        # Test 4: Join Chat
        print("\n4️⃣ Testing Join Chat...")
        if tester.test_join_chat():
            tests_passed += 1
        
        # Test 5: Send Message
        print("\n5️⃣ Testing Send Message...")
        if tester.test_send_message():
            tests_passed += 1
        
        # Test 6: AI Response
        print("\n6️⃣ Testing AI Assistant Response...")
        if tester.test_ai_response():
            tests_passed += 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
    finally:
        tester.disconnect_client()
    
    # Results
    print("\n" + "=" * 60)
    print(f"🏁 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! The application is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the logs above for details.")
        return 1

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)