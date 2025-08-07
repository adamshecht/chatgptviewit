#!/bin/bash

# Start CityScrape Services

echo "🚀 Starting CityScrape services..."

# Kill any existing processes
echo "Cleaning up old processes..."
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true

# Start API backend
echo "Starting API backend on http://localhost:8001..."
cd /Users/adams/Desktop/BrightStone_Script/api
DEV_MODE=true uvicorn main:app --host 127.0.0.1 --port 8001 --log-level info &
API_PID=$!

# Wait for API to start
sleep 5

# Start frontend
echo "Starting frontend on http://localhost:3000..."
cd /Users/adams/Desktop/BrightStone_Script/web
npm run dev &
FRONTEND_PID=$!

# Wait a bit for frontend to start
sleep 5

echo "✅ Services started!"
echo "   API: http://localhost:8001"
echo "   Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for Ctrl+C
trap "echo 'Stopping services...'; kill $API_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait