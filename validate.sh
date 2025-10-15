#!/bin/bash
# Copyright © 2025 Adventures of the Persistently Impaired (and Other Tales) Limited. All Rights Reserved.
# Validation script for PCB Design Agent Docker deployment

echo "🔍 PCB Design Agent - Deployment Validation"
echo "=========================================="

# Function to check files
check_file() {
    if [ -f "$1" ]; then
        echo "✅ $1 exists"
    else
        echo "❌ $1 missing"
        return 1
    fi
}

# Function to check directories
check_dir() {
    if [ -d "$1" ]; then
        echo "✅ $1/ directory exists"
    else
        echo "❌ $1/ directory missing"
        return 1
    fi
}

echo ""
echo "Checking project structure..."

# Critical files
check_file "Dockerfile"
check_file "docker-compose.yml"
check_file "requirements.txt"
check_file "api_server.py"
check_file "start.sh"

# Project structure
check_dir "src"
check_dir "web"
check_dir "tests"

# Web app files
check_file "web/package.json"
check_file "web/next.config.ts"
check_dir "web/src"

echo ""
echo "Checking Docker..."
if command -v docker >/dev/null 2>&1; then
    echo "✅ Docker is available"
    docker --version
else
    echo "❌ Docker not found"
fi

echo ""
echo "Checking ports..."
if command -v lsof >/dev/null 2>&1; then
    if lsof -i:8080 >/dev/null 2>&1; then
        echo "⚠️  Port 8080 is in use"
    else
        echo "✅ Port 8080 is available"
    fi
    
    if lsof -i:8000 >/dev/null 2>&1; then
        echo "⚠️  Port 8000 is in use"
    else
        echo "✅ Port 8000 is available"
    fi
else
    echo "ℹ️  Cannot check port availability (lsof not available)"
fi

echo ""
echo "Validation complete!"
echo ""
echo "To deploy the system:"
echo "  docker build -t pcb-design-agent ."
echo "  docker run -p 8080:8080 pcb-design-agent"
echo ""
echo "Access the web interface at: http://localhost:8080"