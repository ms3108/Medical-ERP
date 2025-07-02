#!/bin/bash

echo "🏥 Starting AI-Enhanced Clinic ERP System..."
echo "=============================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "📦 Building and starting services..."
docker-compose up -d --build

echo "⏳ Waiting for services to start..."
sleep 30

echo "🔍 Checking service health..."

# Check Patient API
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Patient API is running at http://localhost:8000"
else
    echo "❌ Patient API is not responding"
fi

# Check Scheduling Service
if curl -s http://localhost:8001/api/ > /dev/null; then
    echo "✅ Scheduling Service is running at http://localhost:8001"
else
    echo "❌ Scheduling Service is not responding"
fi

# Check AI Memory Service
if curl -s http://localhost:8002/health > /dev/null; then
    echo "✅ AI Memory Service is running at http://localhost:8002"
else
    echo "❌ AI Memory Service is not responding"
fi

# Check Billing Service
if curl -s http://localhost:8003/health > /dev/null; then
    echo "✅ Billing Service is running at http://localhost:8003"
else
    echo "❌ Billing Service is not responding"
fi

echo ""
echo "🎉 Clinic ERP System is ready!"
echo ""
echo "📋 Service URLs:"
echo "   Patient API:        http://localhost:8000/docs"
echo "   Scheduling Service: http://localhost:8001/api/"
echo "   AI Memory Service:  http://localhost:8002/docs"
echo "   Billing Service:    http://localhost:8003/docs"
echo "   Airflow:           http://localhost:8080 (admin/admin)"
echo "   Grafana:           http://localhost:3000 (admin/admin)"
echo "   Prometheus:        http://localhost:9090"
echo ""
echo "📚 See README.md for detailed usage instructions"
echo ""
echo "🛑 To stop the system, run: docker-compose down" 