#!/bin/bash

# ============================================
# AutoEdge AI — One-Click Launcher
# Starts all 5 services in separate terminals
# ============================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "🚗 AutoEdge AI — Starting all services..."
echo "==========================================="
echo ""

# Check dependencies
check_dep() {
  if ! command -v $1 &> /dev/null; then
    echo "❌ $1 not found. Please install it first."
    exit 1
  fi
}

check_dep ollama
check_dep uvicorn
check_dep n8n
check_dep ngrok
check_dep python3

echo "✅ All dependencies found"
echo ""

# Kill any existing processes on our ports
echo "🧹 Cleaning up old processes..."
fuser -k 8000/tcp 2>/dev/null
fuser -k 3000/tcp 2>/dev/null
fuser -k 3002/tcp 2>/dev/null
sleep 1

# Detect terminal emulator
if command -v gnome-terminal &> /dev/null; then
  TERM_CMD="gnome-terminal --"
elif command -v xterm &> /dev/null; then
  TERM_CMD="xterm -e"
elif command -v konsole &> /dev/null; then
  TERM_CMD="konsole -e"
else
  echo "⚠️  No GUI terminal found. Running in background mode..."
  TERM_CMD=""
fi

launch() {
  local title=$1
  local cmd=$2
  local dir=$3

  if [ -n "$TERM_CMD" ]; then
    if command -v gnome-terminal &> /dev/null; then
      gnome-terminal --title="$title" -- bash -c "cd $dir && $cmd; exec bash" &
    else
      $TERM_CMD bash -c "cd $dir && $cmd; exec bash" &
    fi
  else
    # Background mode — log to files
    cd "$dir" && eval "$cmd" >> "$PROJECT_DIR/logs/${title}.log" 2>&1 &
    echo "  Started $title (PID: $!)"
  fi
  sleep 1
}

# Create logs dir for background mode
mkdir -p "$PROJECT_DIR/logs"

echo "🚀 Launching services..."
echo ""

# 1. FastAPI Backend
echo "  [1/5] FastAPI Backend (port 8000)..."
launch "AutoEdge-Backend" \
  "conda run -n automation uvicorn main:app --host 0.0.0.0 --port 8000 --reload" \
  "$PROJECT_DIR/backend"

# 2. n8n
echo "  [2/5] n8n Workflow Engine (port 5678)..."
launch "AutoEdge-n8n" \
  "NODE_OPTIONS='--dns-result-order=ipv4first' n8n start" \
  "$PROJECT_DIR"

# 3. ngrok
echo "  [3/5] ngrok tunnel (exposes port 8000)..."
launch "AutoEdge-ngrok" \
  "ngrok http 8000" \
  "$PROJECT_DIR"

# 4. Dashboard
echo "  [4/5] Dashboard (port 3002)..."
launch "AutoEdge-Dashboard" \
  "python3 -m http.server 3002" \
  "$PROJECT_DIR/dashboard"

# 5. Chat UI
echo "  [5/5] Chat UI (port 3000)..."
launch "AutoEdge-ChatUI" \
  "python3 -m http.server 3000" \
  "$PROJECT_DIR/frontend"

echo ""
echo "==========================================="
echo "✅ All services launched!"
echo ""
echo "  Chat UI   → http://localhost:3000"
echo "  Dashboard → http://localhost:3002"
echo "  API Docs  → http://localhost:8000/docs"
echo "  n8n       → http://localhost:5678"
echo ""
echo "  ⚠️  Wait 10 seconds for all services to start"
echo "  ⚠️  Use Chrome for voice input"
echo "  ⚠️  Activate n8n workflow at localhost:5678"
echo "==========================================="
echo ""

# Open browser tabs after delay
sleep 8
if command -v xdg-open &> /dev/null; then
  echo "🌐 Opening browser tabs..."
  xdg-open "http://localhost:3000" &
  sleep 1
  xdg-open "http://localhost:3002" &
fi

echo "🎯 AutoEdge AI is ready!"
