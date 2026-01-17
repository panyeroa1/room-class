#!/bin/bash
# Run local STT/TTS servers without Docker

set -e

echo "========================================"
echo "Eburon Local STT/TTS Server Launcher"
echo "========================================"

# Check Path to Python 3.13
PYTHON_BIN=$(command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3.10 || command -v python3)

echo "Using Python: $PYTHON_BIN"

# Create virtual environment if not exists or wrong version
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with $PYTHON_BIN..."
    "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate

# Install dependencies using uv for speed and reliability
echo ""
echo "[1/4] Installing STT dependencies..."
uv pip install -r services/stt-server/requirements.txt

echo "[2/4] Installing TTS dependencies..."
uv pip install -r services/tts-server/requirements.txt

# Try to install Kokoro
echo "[3/4] Installing Kokoro TTS..."
uv pip install kokoro 2>/dev/null || echo "Note: Kokoro may need manual install from git"

# Start servers
echo ""
echo "[4/4] Starting servers..."
echo "========================================"

# Start STT server in background
echo "Starting STT Server on port 8001..."
cd services/stt-server
python server.py &
STT_PID=$!
cd ../..

# Start TTS server in background
echo "Starting TTS Server on port 8002..."
cd services/tts-server  
python server.py &
TTS_PID=$!
cd ../..

echo ""
echo "========================================"
echo "Servers running!"
echo "  STT: http://localhost:8001 (PID: $STT_PID)"
echo "  TTS: http://localhost:8002 (PID: $TTS_PID)"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "========================================"

# Trap Ctrl+C to kill both servers
trap "echo 'Stopping servers...'; kill $STT_PID $TTS_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Wait for servers
wait
