#!/bin/bash

# Start CityScrape Development Environment

echo "🚀 Starting CityScrape Development Environment..."

# Check if .env files exist
if [ ! -f "web/.env.local" ]; then
    echo "⚠️  Creating web/.env.local file..."
    cat > web/.env.local << EOF
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
API_URL=http://localhost:8000

# NextAuth Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key-change-this-in-production

# Auth0 Configuration
AUTH0_CLIENT_ID=N9WyueGE0jV0qwqPdC5BsKO2zIHq7a20
AUTH0_CLIENT_SECRET=fE3btXp2KgR3Xsbg7GkBR5j7QkjG2f12fVlCaYt9wJ0VNa92Snvr2_n_f5oM4R-3
AUTH0_DOMAIN=dev-aefjtih56irvjqjx.us.auth0.com
AUTH0_ISSUER=https://dev-aefjtih56irvjqjx.us.auth0.com
EOF
fi

# Start FastAPI backend
echo "🔧 Starting FastAPI backend on http://localhost:8000..."
cd api
python -m uvicorn main:app --reload --port 8000 &
API_PID=$!

# Wait for API to start
sleep 3

# Start Next.js frontend
echo "🎨 Starting Next.js frontend on http://localhost:3000..."
cd ../web
npm run dev &
WEB_PID=$!

echo "✅ Development environment started!"
echo "   - API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for Ctrl+C
trap "kill $API_PID $WEB_PID; exit" INT
wait