#!/bin/bash
# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
# Startup script for PCB Design Agent - Single Container Mode

set -e

echo "🚀 Starting PCB Design Agent (Single Container Mode)..."

# Set environment variables
export PYTHONPATH=/app
export NODE_ENV=production

# Create output directories
mkdir -p /app/outputs /app/projects /app/datasheet_cache

# Check if we're in compose mode (nginx handles routing) or standalone mode
if [ "${COMPOSE_MODE:-false}" = "true" ]; then
    echo "📡 Starting in Docker Compose mode - Backend only"
    exec python -m uvicorn api_server:app --host 0.0.0.0 --port 8000
else
    echo "📡 Starting in standalone mode - Backend + Frontend"
    
    # Install Node.js if not present (for standalone mode)
    if ! command -v node &> /dev/null; then
        echo "📦 Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt-get install -y nodejs
    fi
    
    # Check if web directory exists
    if [ ! -d "/app/web" ]; then
        echo "❌ Web directory not found. This image is configured for compose mode only."
        echo "Please use docker-compose.yml or build with web assets included."
        exit 1
    fi
    
    # Start FastAPI backend in background
    echo "📡 Starting FastAPI backend on port 8000..."
    python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    
    # Wait for backend to start
    echo "⏳ Waiting for backend to start..."
    for i in {1..30}; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ Backend is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ Backend failed to start within 30 seconds"
            exit 1
        fi
        sleep 1
    done
    
    # Start Next.js web application
    echo "🌐 Starting web interface on port 8080..."
    cd /app/web
    npm start -- --port 8080 --hostname 0.0.0.0 &
    WEB_PID=$!
    
    # Function to handle shutdown
    shutdown() {
        echo "🛑 Shutting down services..."
        kill $BACKEND_PID $WEB_PID 2>/dev/null || true
        wait $BACKEND_PID $WEB_PID 2>/dev/null || true
        echo "✅ Shutdown complete"
        exit 0
    }
    
    # Set up signal handlers
    trap shutdown SIGTERM SIGINT
    
    # Wait for either process to exit
    wait -n $BACKEND_PID $WEB_PID
    
    # If we get here, one process has exited
    echo "❌ One of the services has exited unexpectedly"
    shutdown
fi