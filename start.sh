#!/bin/bash

# Real-time Chat Application Startup Script

echo "🚀 Starting Real-time Chat Application with AI Assistant"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed."
    exit 1
fi

echo "✅ Docker is running"

# Create necessary directories if they don't exist
mkdir -p backend frontend

# Stop any existing services
echo "🔄 Stopping existing services..."
docker-compose down

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."

# Function to check if a service is healthy
check_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo "Checking $service service..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:$port/health > /dev/null 2>&1 || \
           curl -f http://localhost:$port > /dev/null 2>&1; then
            echo "✅ $service is ready!"
            return 0
        fi
        
        echo "⏳ Attempt $attempt/$max_attempts: Waiting for $service..."
        sleep 2
        ((attempt++))
    done
    
    echo "❌ $service failed to start after $max_attempts attempts"
    return 1
}

# Check Ollama service
echo "Checking Ollama service..."
attempt=1
max_attempts=60  # Ollama takes longer due to model download
while [ $attempt -le $max_attempts ]; do
    if curl -f http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama is ready!"
        break
    fi
    
    if [ $attempt -eq 1 ]; then
        echo "📥 First run detected. Downloading AI model (this may take 5-10 minutes)..."
    fi
    
    echo "⏳ Attempt $attempt/$max_attempts: Waiting for Ollama..."
    sleep 5
    ((attempt++))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ Ollama failed to start. Check logs: docker-compose logs ollama"
    exit 1
fi

# Check backend service
check_service "Backend" 5000

# Check frontend service
check_service "Frontend" 8501

echo ""
echo "🎉 All services are running successfully!"
echo "=================================================="
echo "📱 Access the chat application at: http://localhost:8501"
echo "🔧 Backend API available at: http://localhost:5000"
echo "🤖 Ollama API available at: http://localhost:11434"
echo ""
echo "💡 Useful commands:"
echo "   View all logs:     docker-compose logs -f"
echo "   View service logs: docker-compose logs -f [service-name]"
echo "   Stop services:     docker-compose down"
echo "   Restart services:  docker-compose restart"
echo ""
echo "🎯 Ready to chat! Open your browser and go to http://localhost:8501"