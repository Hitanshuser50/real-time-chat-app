FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

<<<<<<< HEAD
# Copy requirements first for better caching
COPY requirements.txt .
=======
# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy requirements first for better caching
COPY ../requirements.txt .
>>>>>>> origin/master

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

<<<<<<< HEAD
=======
# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

>>>>>>> origin/master
# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "app:app"]