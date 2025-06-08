# Real-time Chat Application with AI Assistant

A real-time chat application powered by local LLM using Ollama, with Socket.IO for real-time communication and Streamlit for the frontend interface.

## Features

- **Real-time messaging** with Socket.IO
- **AI Assistant** integration using Ollama (LLaMA 3.2)
- **Multi-user support** with user presence tracking
- **Streamlit frontend** with modern UI
- **Fully containerized** with Docker Compose
- **Asynchronous message processing**

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Streamlit      │    │  Flask+SocketIO │    │  Ollama         │
│  Frontend       │◄──►│  Backend        │◄──►│  LLM Service    │
│  (Port 8501)    │    │  (Port 5000)    │    │  (Port 11434)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Prerequisites

- Docker and Docker Compose
- At least 4GB RAM (8GB+ recommended for better LLM performance)
- Internet connection for initial model download

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone <your-repository-url>
   cd real-time-chat-app
   ```

2. **Start the services:**
   ```bash
   docker-compose up -d
   ```

3. **Wait for initialization:**
   - The Ollama service will pull the LLaMA 3.2 model on first run
   - This may take 5-10 minutes depending on your internet connection
   - Monitor progress: `docker-compose logs -f ollama`

4. **Access the application:**
   - Open your browser and go to `http://localhost:8501`
   - Enter a username and join the chat

## Usage

### Basic Chat
- Enter your username to join the chat
- Type messages in the input field
- Messages are shared with all connected users in real-time

### AI Assistant
- Use `@ai` or `@bot` prefix to ask the AI assistant
- Example: `@ai What is the weather like?`
- The AI will respond based on the conversation context

### Multi-User Features
- See active users in the sidebar
- Real-time user join/leave notifications
- Chat history is preserved for new users

## Project Structure

```
real-time-chat-app/
├── docker-compose.yml          # Docker Compose configuration
├── backend/
│   ├── Dockerfile             # Backend container
│   ├── requirements.txt       # Python dependencies
│   └── app.py                 # Flask+SocketIO server
├── frontend/
│   ├── Dockerfile             # Frontend container
│   ├── requirements.txt       # Streamlit dependencies
│   └── app.py                 # Streamlit application
└── README.md                  # This file
```

## Configuration

### Environment Variables

**Backend (`chat-backend`):**
- `OLLAMA_URL`: URL of Ollama service (default: `http://ollama:11434`)
- `FLASK_ENV`: Flask environment (default: `production`)

**Frontend (`streamlit-frontend`):**
- `BACKEND_URL`: URL of backend service (default: `http://chat-backend:5000`)

### Model Configuration

The application uses `llama3.2:1b` by default for better performance. To use a different model:

1. Edit `backend/app.py` and change the `MODEL_NAME` variable
2. Rebuild the backend: `docker-compose build chat-backend`
3. Restart services: `docker-compose restart`

Available models:
- `llama3.2:1b` (1GB) - Fast, good for demos
- `llama3.2:3b` (2GB) - Better quality
- `mistral:7b` (4GB) - High quality
- `codellama:7b` (4GB) - Code-focused

## Monitoring and Logs

**View all logs:**
```bash
docker-compose logs -f
```

**View specific service logs:**
```bash
docker-compose logs -f ollama
docker-compose logs -f chat-backend
docker-compose logs -f streamlit-frontend
```

**Check service status:**
```bash
docker-compose ps
```

## Troubleshooting

### Common Issues

1. **Ollama model not loading:**
   - Check if you have enough RAM
   - Monitor: `docker-compose logs -f ollama`
   - Restart: `docker-compose restart ollama`

2. **Frontend can't connect to backend:**
   - Verify all services are running: `docker-compose ps`
   - Check backend logs: `docker-compose logs chat-backend`

3. **Slow AI responses:**
   - Switch to a smaller model (e.g., `llama3.2:1b`)
   - Increase Docker memory allocation
   - Check system resources: `docker stats`

### Performance Optimization

1. **Reduce model size:**
   - Use `llama3.2:1b` instead of larger models
   - Edit `MODEL_NAME` in `backend/app.py`

2. **Increase Docker resources:**
   - Allocate more RAM to Docker Desktop
   - Set CPU limits in `docker-compose.yml`

3. **Enable GPU acceleration (if available):**
   - Add GPU support to Ollama service in `docker-compose.yml`

## Development

### Local Development

1. **Backend development:**
   ```bash
   cd backend
   pip install -r requirements.txt
   python app.py
   ```

2. **Frontend development:**
   ```bash
   cd frontend
   pip install -r requirements.txt
   streamlit run app.py
   ```

### Adding Features

1. **New message types:**
   - Add handlers in `backend/app.py`
   - Update frontend in `frontend/app.py`

2. **Authentication:**
   - Implement user authentication in backend
   - Add login form in Streamlit frontend

3. **Persistent storage:**
   - Add database integration (PostgreSQL, MongoDB)
   - Store chat history and user data

## Deployment

### Production Deployment

1. **Security considerations:**
   - Change default secret keys
   - Add authentication
   - Use HTTPS/WSS
   - Implement rate limiting

2. **Scaling:**
   - Use Redis for session storage
   - Load balance multiple backend instances
   - Separate Ollama service

3. **Monitoring:**
   - Add health checks
   - Implement logging
   - Set up alerts

## API Reference

### Socket.IO Events

**Client to Server:**
- `join_chat`: Join chat with username
- `send_message`: Send message to chat
- `get_active_users`: Request active users list

**Server to Client:**
- `new_message`: New message received
- `chat_history`: Chat history on connect
- `active_users`: Updated active users list
- `user_left`: User left notification

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Docker and service logs
3. Open an issue on GitHub

---

**Note:** This application is designed for educational and demonstration purposes. For production use, implement proper security measures, authentication, and monitoring.