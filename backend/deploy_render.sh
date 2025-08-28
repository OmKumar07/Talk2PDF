#!/bin/bash
# Render.com Deployment Script for Talk2PDF Backend

echo "🚀 Starting Talk2PDF Backend Deployment..."

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Load production environment
echo "🌍 Loading production environment..."
python config_loader.py production

# Verify environment setup
echo "🔍 Verifying environment..."
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ GEMINI_API_KEY not set in environment variables"
    echo "Please set GEMINI_API_KEY in Render environment variables"
    exit 1
fi

# Create storage directory
echo "📁 Creating storage directory..."
mkdir -p storage

# Start the server
echo "🎯 Starting server..."
exec uvicorn app:app --host 0.0.0.0 --port $PORT
