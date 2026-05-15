#!/usr/bin/env python3
"""
APEX AUDIO_PROCESSOR MCP SERVER
Purpose: Audio transcription and processing hub
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from mcp.server.fastmcp import FastMCP

from services.apex_whisperx_bridge import WhisperXBridge

mcp = FastMCP("APEX-Audio_processor-MCP")
bridge = WhisperXBridge()


@mcp.tool()
async def transcribe_audio(file_path: str, remote: bool = False) -> Dict[str, Any]:
    """
    Transcribe an audio file using high-fidelity WhisperX.
    Args:
        file_path: Path to the audio file.
        remote: Whether to use the remote GPU-enabled worker.
    """
    if not os.path.exists(file_path):
        return {"status": "error", "message": f"File not found: {file_path}"}
    
    return bridge.transcribe(file_path, remote=remote)

@mcp.tool()
async def extract_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract forensic metadata and audio properties.
    """
    if not os.path.exists(file_path):
        return {"status": "error", "message": f"File not found: {file_path}"}
        
    try:
        import subprocess
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {"status": "success", "metadata": json.loads(res.stdout)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    mcp.run()

