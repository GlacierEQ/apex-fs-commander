#!/usr/bin/env python3
"""
APEX WHISPERX BRIDGE
High-fidelity transcription bridge supporting local and remote execution.
"""

import os
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("APEX-WhisperX")

class WhisperXBridge:
    def __init__(self):
        self.remote_host = os.environ.get("WHISPERX_REMOTE_HOST")
        self.remote_user = os.environ.get("WHISPERX_REMOTE_USER", "casey")
        self.remote_port = os.environ.get("WHISPERX_REMOTE_PORT", "2222")
        self.hf_token = os.environ.get("HF_TOKEN") # Required for diarization
        self.local_output_dir = Path.home() / "apex-fs-commander" / "transcripts"
        self.local_output_dir.mkdir(parents=True, exist_ok=True)

    def transcribe(self, file_path: str, remote: bool = False, diarize: bool = True) -> Dict[str, Any]:
        """
        Transcribe an audio file using WhisperX with forensic precision.
        """
        if remote and self.remote_host:
            return self._transcribe_remote(file_path, diarize)
        return self._transcribe_local(file_path, diarize)

    def _transcribe_local(self, file_path: str, diarize: bool) -> Dict[str, Any]:
        """Execute WhisperX locally with diarization support."""
        logger.info(f"Initiating local WhisperX transcription for: {file_path}")
        try:
            cmd = [
                "whisperx",
                file_path,
                "--output_dir", str(self.local_output_dir),
                "--output_format", "json",
                "--compute_type", "int8",
                "--model", "base",
                "--language", "en"
            ]
            
            if diarize and self.hf_token:
                cmd.extend(["--diarize", "--hf_token", self.hf_token])
            
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            output_file = self.local_output_dir / f"{Path(file_path).stem}.json"
            
            if output_file.exists():
                return {
                    "status": "success",
                    "method": "local",
                    "file": str(output_file),
                    "data": json.loads(output_file.read_text())
                }
            return {"status": "error", "message": "Transcription completed but output file missing."}
            
        except Exception as e:
            logger.error(f"Local transcription failed: {e}")
            return {"status": "error", "message": str(e)}

    def _transcribe_remote(self, file_path: str, diarize: bool) -> Dict[str, Any]:
        """Execute Maximized WhisperX on a remote GPU host via SSH."""
        logger.info(f"Initiating remote WhisperX (FORENSIC) on {self.remote_host} for: {file_path}")
        remote_path = f"/tmp/{Path(file_path).name}"
        
        try:
            # 1. SCP file to remote
            scp_cmd = ["scp", "-P", self.remote_port, file_path, f"{self.remote_user}@{self.remote_host}:{remote_path}"]
            subprocess.run(scp_cmd, check=True)
            
            # 2. Run WhisperX remotely (Large-V3 + Diarization + Alignment)
            diarize_flag = f"--diarize --hf_token {self.hf_token}" if diarize and self.hf_token else ""
            remote_cmd = (
                f"source ~/whisperx_env/bin/activate && "
                f"whisperx {remote_path} "
                f"--output_dir /tmp "
                f"--output_format json "
                f"--compute_type float16 " 
                f"--model large-v3 "
                f"--align_model WAV2VEC2_ASR_LARGE_LV60_SELF_960H "
                f"{diarize_flag}"
            )
            
            ssh_cmd = ["ssh", "-p", self.remote_port, f"{self.remote_user}@{self.remote_host}", remote_cmd]
            subprocess.run(ssh_cmd, check=True)
            
            # 3. SCP result back
            remote_result = f"/tmp/{Path(file_path).stem}.json"
            local_result = self.local_output_dir / f"{Path(file_path).stem}_remote.json"
            
            scp_back_cmd = ["scp", "-P", self.remote_port, f"{self.remote_user}@{self.remote_host}:{remote_result}", str(local_result)]
            subprocess.run(scp_back_cmd, check=True)
            
            return {
                "status": "success",
                "method": "remote",
                "file": str(local_result),
                "data": json.loads(local_result.read_text())
            }
            
        except Exception as e:
            logger.error(f"Remote transcription failed: {e}")
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Test script
    import sys
    if len(sys.argv) > 1:
        bridge = WhisperXBridge()
        res = bridge.transcribe(sys.argv[1], remote=("--remote" in sys.argv))
        print(json.dumps(res, indent=2))
