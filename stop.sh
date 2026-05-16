#!/bin/bash

echo "🛑 Stopping AutoEdge AI services..."

fuser -k 8000/tcp 2>/dev/null && echo "  ✅ Backend stopped"
fuser -k 3000/tcp 2>/dev/null && echo "  ✅ Chat UI stopped"
fuser -k 3002/tcp 2>/dev/null && echo "  ✅ Dashboard stopped"
pkill -f "n8n start" 2>/dev/null && echo "  ✅ n8n stopped"
pkill -f "ngrok" 2>/dev/null && echo "  ✅ ngrok stopped"

echo ""
echo "All services stopped."
