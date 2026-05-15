#!/usr/bin/env python3
"""
APEX AUTO-TRANSCRIBE
Automatically scans forensic evidence folders for audio/video files and transcribes them using WhisperX.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add project root to path for services import
sys.path.append(str(Path(__file__).parent.parent))
from services.apex_whisperx_bridge import WhisperXBridge

# Configuration
ORGANIZED_DIR = Path("/Users/macarena1/Library/CloudStorage/Dropbox-Kahalainspector/Kahala Home Inspectors/Case_1FDV-23-0001009_ORGANIZED")
EVIDENCE_MEDIA_DIR = ORGANIZED_DIR / "02_EVIDENCE/02g_Photos_Videos"
TRANSCRIPT_DIR = ORGANIZED_DIR / "02_EVIDENCE/02f_Communications/Transcripts"
STATE_FILE = Path("/Users/macarena1/dev/projects/apex-fs-commander/logs/auto_transcribe_state.json")

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("APEX-AutoTranscribe")

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            return {}
    return {}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))

def run_auto_transcribe(dry_run=False):
    logger.info("🚀 Starting APEX Auto-Transcription Scan...")
    
    if not EVIDENCE_MEDIA_DIR.exists():
        logger.error(f"Media evidence directory missing: {EVIDENCE_MEDIA_DIR}")
        return

    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    bridge = WhisperXBridge()

    # Supported media extensions
    extensions = {'.mp3', '.m4a', '.wav', '.mp4', '.mov', '.aac'}
    
    pending_files = []
    for item in EVIDENCE_MEDIA_DIR.iterdir():
        if item.is_file() and item.suffix.lower() in extensions:
            # Check if already transcribed
            if str(item) in state and state[str(item)].get("status") == "success":
                continue
            
            # Double check if transcript file exists manually (in case state was lost)
            expected_transcript = TRANSCRIPT_DIR / f"{item.stem}.json"
            if expected_transcript.exists():
                logger.info(f"  Transcript already exists for {item.name}, updating state.")
                state[str(item)] = {"status": "success", "file": str(expected_transcript)}
                continue
                
            pending_files.append(item)

    logger.info(f"📋 Found {len(pending_files)} files pending transcription.")

    for media_file in pending_files:
        logger.info(f"📝 Transcribing: {media_file.name}")
        
        if dry_run:
            logger.info(f"  [DRY-RUN] Would transcribe {media_file.name}")
            continue

        try:
            # Run transcription (defaulting to local, can be changed to remote=True if desired)
            result = bridge.transcribe(str(media_file), remote=False)
            
            if result.get("status") == "success":
                # Move transcript to the evidence transcripts folder
                src_transcript = Path(result["file"])
                dest_transcript = TRANSCRIPT_DIR / f"{media_file.stem}.json"
                
                # Copy the transcript data into the organized vault
                dest_transcript.write_text(json.dumps(result["data"], indent=2))
                
                state[str(media_file)] = {
                    "status": "success",
                    "file": str(dest_transcript),
                    "processed_at": os.path.getmtime(media_file)
                }
                logger.info(f"  ✅ Success: {dest_transcript.name}")
            else:
                logger.error(f"  ❌ Failed: {result.get('message')}")
                state[str(media_file)] = {"status": "error", "message": result.get("message")}
                
        except Exception as e:
            logger.error(f"  ❌ Critical Error: {e}")
            state[str(media_file)] = {"status": "error", "message": str(e)}

        # Save state after each file to allow resuming
        save_state(state)

    logger.info("🎉 Auto-Transcription Cycle Complete.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    run_auto_transcribe(dry_run=args.dry_run)
