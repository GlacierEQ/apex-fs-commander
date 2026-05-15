#!/usr/bin/env bash
# ============================================================
# APEX REMOTE WHISPERX DEPLOYER
# Setup high-fidelity transcription on a remote GPU/CPU node.
# ============================================================

set -e

REMOTE_HOST=${1:-$WHISPERX_REMOTE_HOST}
REMOTE_USER=${2:-$WHISPERX_REMOTE_USER}
REMOTE_PORT=${3:-$WHISPERX_REMOTE_PORT}

if [ -z "$REMOTE_HOST" ]; then
    echo "Usage: ./DEPLOY_REMOTE_WHISPERX.sh <remote_host> [remote_user] [remote_port]"
    exit 1
fi

echo "🚀 INITIATING REMOTE WHISPERX SETUP ON $REMOTE_HOST..."

# SSH command template
SSH="ssh -p $REMOTE_PORT $REMOTE_USER@$REMOTE_HOST"

# 1. Install System Deps (Detection logic for Alpine/Ubuntu)
echo "[1/4] Installing system dependencies..."
$SSH "if command -v apk &>/dev/null; then 
        sudo apk add ffmpeg git python3 py3-pip build-base python3-dev;
      else 
        sudo apt-get update && sudo apt-get install -y ffmpeg git python3-pip python3-dev build-essential;
      fi"

# 2. Setup Virtual Environment (Optional but recommended)
echo "[2/4] Setting up Python environment..."
$SSH "python3 -m pip install --upgrade pip && \
      pip install --user virtualenv && \
      python3 -m virtualenv ~/whisperx_env && \
      source ~/whisperx_env/bin/activate"

# 3. Install WhisperX & Torch (GPU Accelerated)
echo "[3/4] Installing WhisperX (GPU Accelerated)..."
$SSH "source ~/whisperx_env/bin/activate && \
      if command -v nvidia-smi &>/dev/null; then \
        echo 'NVIDIA GPU detected. Installing CUDA-optimized Torch...'; \
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118; \
      else \
        echo 'No GPU detected. Falling back to CPU Torch...'; \
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
      fi && \
      pip install whisperx"

# 4. Verify & Pre-load Models
echo "[4/4] Verifying & Pre-loading Forensic Models..."
$SSH "source ~/whisperx_env/bin/activate && \
      whisperx --version && \
      echo 'Pre-loading large-v3 model...' && \
      python3 -c 'import whisperx; whisperx.load_model(\"large-v3\", \"cpu\")' "

echo "✅ REMOTE FORENSIC WHISPERX DEPLOYED!"
echo "You can now use 'apexgo whisperx transcribe --remote' to offload tasks."
