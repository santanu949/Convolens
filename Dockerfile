FROM python:3.11-slim

WORKDIR /app

# Install Node.js for frontend build
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Build frontend
COPY frontend/ ./frontend/
RUN cd frontend && npm install && npm run build

# Copy backend
COPY backend/ ./backend/

# Create data directory
RUN mkdir -p /app/data/uploads

# Set environment
ENV FLASK_ENV=production
ENV DATA_DIR=/app/data
ENV DB_PATH=/app/data/convolens.db
ENV UPLOAD_DIR=/app/data/uploads
ENV PORT=5000
ENV PYTHONPATH=/app/backend

EXPOSE 5000

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "600", "backend.app:create_app()"]
