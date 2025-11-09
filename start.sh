#!/bin/bash
# Quick start script for GH Triage Lite

echo "🚀 Starting GH Triage Lite..."
echo ""

# Check if NVIDIA_API_KEY is set
if [ -z "$NVIDIA_API_KEY" ]; then
    echo "⚠️  Warning: NVIDIA_API_KEY not set!"
    echo "   Export it with: export NVIDIA_API_KEY='your-key-here'"
    echo ""
fi

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

echo "✅ Starting server on http://localhost:8000"
echo ""
echo "📝 Endpoints:"
echo "   - Web UI:      http://localhost:8000"
echo "   - Health:      http://localhost:8000/healthz"
echo "   - API Docs:    http://localhost:8000/docs"
echo "   - Triage:      http://localhost:8000/triage?repo=owner/name"
echo ""

python -m app.app

