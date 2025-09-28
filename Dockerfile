# Multi-stage Docker build for Firefly Station
FROM python:3.9-slim as backend-builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend build stage
FROM node:18-alpine as frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY frontend/ ./

# Build frontend
RUN npm run build

# Final production image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production
ENV PYTHONPATH=/app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash firefly

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=backend-builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=firefly:firefly . .

# Copy built frontend from builder
COPY --from=frontend-builder --chown=firefly:firefly /app/frontend/build ./frontend/build

# Create necessary directories
RUN mkdir -p logs backups && \
    chown -R firefly:firefly /app

# Switch to non-root user
USER firefly

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "from backend import database; database.init_db(); print('OK')" || exit 1

# Start command
CMD ["python3", "main.py"]