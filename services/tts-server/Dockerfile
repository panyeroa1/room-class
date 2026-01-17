FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including g++ for pkuseg/chatterbox)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    git-lfs \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Pre-install numpy (required at setup.py time for pkuseg/chatterbox)
RUN pip install --no-cache-dir numpy>=1.24.0

# Install remaining requirements
RUN pip install --no-cache-dir -r requirements.txt

# Install Kokoro from git
RUN pip install git+https://github.com/hexgrad/kokoro.git || echo "Kokoro install skipped"

# Download Supertonic models (approx 200MB)
RUN git lfs install && \
    mkdir -p models && \
    git clone https://huggingface.co/Supertone/supertonic-2 models/supertonic && \
    rm -rf models/supertonic/.git

# Copy server code
COPY . .

# Create voices directory
RUN mkdir -p voices

# Expose port
EXPOSE 8002

# Run server
CMD ["python", "server.py"]
