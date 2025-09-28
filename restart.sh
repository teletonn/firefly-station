#!/bin/bash

# Clean Restart Procedure for Светлячок LLM Radio System
# This script stops running processes, clears caches, rebuilds the frontend, and restarts the application

set -e  # Exit on any error

echo "🛑 Stopping running processes..."

# Kill any running Python processes related to the application
pkill -f "python main.py" || echo "No main.py processes found"
pkill -f "uvicorn" || echo "No uvicorn processes found"
pkill -f "launch.py" || echo "No launch.py processes found"

# Kill any Node.js development servers if running
pkill -f "react-scripts start" || echo "No React dev server found"

# Wait a moment for processes to terminate
sleep 2

echo "🧹 Clearing caches..."

# Clear Python cache files
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || echo "No Python cache found"
find . -name "*.pyc" -delete 2>/dev/null || echo "No .pyc files found"

# Clear frontend build directory
if [ -d "frontend/build" ]; then
    rm -rf frontend/build
    echo "✅ Cleared frontend build cache"
else
    echo "No frontend build directory found"
fi

# Clear npm cache
cd frontend
npm cache clean --force || echo "Failed to clear npm cache"
cd ..

echo "🔨 Rebuilding frontend..."

# Install frontend dependencies and build
cd frontend
npm install
npm run build
cd ..

echo "✅ Frontend rebuilt successfully"

echo "🚀 Starting the application..."

# Start the application using main.py directly (bypassing launch.py checks since we just did them)
python3 main.py

echo "🎉 Application restarted successfully!"
echo ""
echo "🌐 Web Interface: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo ""
echo "📋 Browser Cache Clearing Instructions:"
echo "To ensure a completely fresh start, clear your browser cache:"
echo "- Chrome: Ctrl+Shift+R (or Cmd+Shift+R on Mac) for hard refresh"
echo "- Firefox: Ctrl+F5 (or Cmd+Shift+R on Mac)"
echo "- Or manually: Browser settings > Clear browsing data > Cached images and files"
echo ""
echo "Press Ctrl+C to stop the application"