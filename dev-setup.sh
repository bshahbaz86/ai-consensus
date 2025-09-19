#!/bin/bash

# Development setup script for AI Consensus

echo "🚀 Setting up AI Consensus development environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from example..."
    cp .env.example .env
fi

# Start Redis for development (standalone)
echo "🔄 Starting Redis..."
redis-server --daemonize yes --port 6379

# Install Python dependencies locally for development
echo "📦 Installing Python dependencies..."
python3 -m pip install -r requirements.txt

# Run Django migrations
echo "🗄️  Running database migrations..."
python3 manage.py migrate

# Create superuser (optional)
echo "👤 Create a superuser account? (y/n)"
read -r create_superuser
if [ "$create_superuser" = "y" ]; then
    python3 manage.py createsuperuser
fi

echo "✅ Development environment setup complete!"
echo ""
echo "🎯 To start development:"
echo "   python3 manage.py runserver  # Start Django server"
echo "   celery -A config worker       # Start Celery worker (new terminal)"
echo ""
echo "🐳 To use Docker instead:"
echo "   docker-compose up --build     # Start all services"
echo ""
echo "📱 Access the application:"
echo "   Django Admin: http://localhost:8000/admin/"
echo "   API: http://localhost:8000/api/v1/"