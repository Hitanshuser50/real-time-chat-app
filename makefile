# Makefile for Real-time Chat Application

.PHONY: help build start stop restart logs clean test dev status health codespace-setup codespace-start codespace-stop

# Default target
help:
	@echo "Real-time Chat Application with AI Assistant"
	@echo "============================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make start     - Start all services"
	@echo "  make stop      - Stop all services"
	@echo "  make restart   - Restart all services"
	@echo "  make build     - Build all Docker images"
	@echo "  make logs      - Show logs from all services"
	@echo "  make clean     - Clean up containers and volumes"
	@echo "  make test      - Run integration tests"
	@echo "  make dev       - Start in development mode"
	@echo "  make status    - Show status of all services"
	@echo "  make health    - Check health of all services"
	@echo ""
	@echo "GitHub Codespaces commands:"
	@echo "  make codespace-setup  - Setup environment for Codespaces"
	@echo "  make codespace-start  - Start services in Codespaces"
	@echo "  make codespace-stop   - Stop services in Codespaces"
	@echo ""
	@echo "Service-specific commands:"
	@echo "  make logs-ollama    - Show Ollama logs"
	@echo "  make logs-backend   - Show backend logs"
	@echo "  make logs-frontend  - Show frontend logs"

# Start all services
start:
	@echo "🚀 Starting Real-time Chat Application..."
	@docker-compose up -d
	@echo "✅ Services started! Access the app at http://localhost:8501"

# Stop all services
stop:
	@echo "🛑 Stopping all services..."
	@docker-compose down
	@echo "✅ All services stopped"

# Restart all services
restart: stop start

# Build all Docker images
build:
	@echo "🔨 Building Docker images..."
	@docker-compose build --no-cache
	@echo "✅ All images built successfully"

# Show logs from all services
logs:
	@docker-compose logs -f

# Show logs from specific services
logs-ollama:
	@docker-compose logs -f ollama

logs-backend:
	@docker-compose logs -f chat-backend

logs-frontend:
	@docker-compose logs -f streamlit-frontend

# Clean up containers, images, and volumes
clean:
	@echo "🧹 Cleaning up Docker resources..."
	@docker-compose down -v --remove-orphans
	@docker system prune -f
	@echo "✅ Cleanup completed"

# Run integration tests
test:
	@echo "🧪 Running integration tests..."
	@python test_integration.py

# Start in development mode
dev:
	@echo "🔧 Starting in development mode..."
	@docker-compose -f docker-compose.dev.yml up --build -d
	@echo "✅ Development environment started!"

# Show status of all services
status:
	@echo "📊 Service Status:"
	@docker-compose ps

# Check health of all services
health:
	@echo "🏥 Health Check:"
	@echo "Checking Ollama..."
	@curl -f http://localhost:11434/api/tags > /dev/null 2>&1 && echo "✅ Ollama: Healthy" || echo "❌ Ollama: Unhealthy"
	@echo "Checking Backend..."
	@curl -f http://localhost:5000/health > /dev/null 2>&1 && echo "✅ Backend: Healthy" || echo "❌ Backend: Unhealthy"
	@echo "Checking Frontend..."
	@curl -f http://localhost:8501 > /dev/null 2>&1 && echo "✅ Frontend: Healthy" || echo "❌ Frontend: Unhealthy"

# GitHub Codespaces specific commands
codespace-setup:
	@echo "🔧 Setting up GitHub Codespaces environment..."
	@chmod +x start.sh
	@pip install -r backend/requirements.txt
	@pip install -r frontend/requirements.txt
	@echo "✅ Codespaces setup completed"

codespace-start:
	@echo "🚀 Starting services in GitHub Codespaces..."
	@docker-compose -f docker-compose.dev.yml up --build -d
	@echo "✅ Services started in Codespaces!"
	@echo "Frontend: http://localhost:8501"
	@echo "Backend: http://localhost:5000"
	@echo "Ollama: http://localhost:11434"

codespace-stop:
	@echo "🛑 Stopping services in GitHub Codespaces..."
	@docker-compose -f docker-compose.dev.yml down
	@echo "✅ Services stopped in Codespaces"

# Setup development environment
setup-dev:
	@echo "🔧 Setting up development environment..."
	@chmod +x start.sh
	@pip install -r backend/requirements.txt
	@pip install -r frontend/requirements.txt
	@echo "✅ Development setup completed"

# Quick start with automatic model download
quick-start:
	@echo "⚡ Quick Start - This will download AI models (may take 5-10 minutes)..."
	@chmod +x start.sh
	@./start.sh

# Monitor resource usage
monitor:
	@echo "📈 Resource Usage:"
	@docker stats --no-stream

# Backup Ollama models
backup-models:
	@echo "💾 Backing up Ollama models..."
	@docker run --rm -v real-time-chat-app_ollama_data:/data -v $(PWD):/backup alpine tar czf /backup/ollama_backup.tar.gz -C /data .
	@echo "✅ Models backed up to ollama_backup.tar.gz"

# Restore Ollama models
restore-models:
	@echo "📥 Restoring Ollama models..."
	@docker run --rm -v real-time-chat-app_ollama_data:/data -v $(PWD):/backup alpine tar xzf /backup/ollama_backup.tar.gz -C /data
	@echo "✅ Models restored from ollama_backup.tar.gz"

# Update application
update:
	@echo "🔄 Updating application..."
	@git pull
	@docker-compose build --no-cache
	@docker-compose up -d
	@echo "✅ Application updated successfully"