# Quick diagnostic script to test AI integration
import requests
import json

def test_ollama_connection():
    """Test Ollama connection and model availability"""
    OLLAMA_URL = 'http://localhost:11434'
    MODEL_NAME = 'llama3.2:1b'
    
    print("🔍 Testing Ollama Connection...")
    
    # Test 1: Health check
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama is responding")
            models = response.json().get('models', [])
            print(f"📋 Available models: {len(models)}")
            
            # Check if our model exists
            model_found = False
            for model in models:
                if MODEL_NAME in model.get('name', ''):
                    model_found = True
                    print(f"✅ Model {MODEL_NAME} found")
                    break
            
            if not model_found:
                print(f"❌ Model {MODEL_NAME} not found")
                return False
                
        else:
            print(f"❌ Ollama health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        return False
    
    # Test 2: Generate response
    try:
        print("\n🤖 Testing AI response generation...")
        test_prompt = "Hello, can you respond with just 'AI is working!'?"
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL_NAME,
                "prompt": test_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 50
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get('response', 'No response')
            print(f"✅ AI Response: {ai_response}")
            return True
        else:
            print(f"❌ AI generation failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ AI generation error: {e}")
        return False

def test_backend_health():
    """Test backend health"""
    BACKEND_URL = 'http://localhost:5000'
    
    print("\n🔍 Testing Backend Connection...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Backend is healthy")
            print(f"📊 Stats: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 AI Integration Diagnostic\n")
    
    ollama_ok = test_ollama_connection()
    backend_ok = test_backend_health()
    
    print(f"\n📋 Summary:")
    print(f"Ollama: {'✅ OK' if ollama_ok else '❌ FAILED'}")
    print(f"Backend: {'✅ OK' if backend_ok else '❌ FAILED'}")
    
    if ollama_ok and backend_ok:
        print("\n🎉 Everything looks good! Try sending '@ai hello' in your chat.")
    else:
        print("\n🔧 Issues found. Check the errors above.")
        
        if not ollama_ok:
            print("\nOllama fixes:")
            print("- Make sure Docker container is running: docker ps")
            print("- Check model: docker exec ollama ollama list")
            print("- Pull model: docker exec ollama ollama pull llama3.2:1b")
            
        if not backend_ok:
            print("\nBackend fixes:")
            print("- Make sure backend is running: python app.py")
            print("- Check port 5000 is not blocked")
            print("- Check backend logs for errors")