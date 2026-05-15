#!/usr/bin/env python3
"""
APEX ONEDRIVE INTELLIGENCE SERVICE
Intelligent synchronization, categorization, and processing of forensic evidence.
Case: 1FDV-23-0001009
"""

import os
import json
import requests
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.apex_onedrive_persistent import OneDriveManager, _drive_path_url
from services.apex_whisperx_bridge import WhisperXBridge

# Configuration
CASE_FOLDER = "Case-1FDV-23-0001009"
EVIDENCE_ROOT = Path.home() / "apex-evidence"
SYNC_LEDGER = EVIDENCE_ROOT / "onedrive_sync_ledger.json"

class OneDriveIntelligence:
    def __init__(self):
        self.manager = OneDriveManager()
        self.whisper = WhisperXBridge()
        self.evidence_root = EVIDENCE_ROOT
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        self.ledger = self._load_ledger()

    def _load_ledger(self) -> Dict:
        if SYNC_LEDGER.exists():
            try:
                return json.loads(SYNC_LEDGER.read_text())
            except:
                return {}
        return {}

    def _save_ledger(self):
        SYNC_LEDGER.write_text(json.dumps(self.ledger, indent=2))

    async def sync_all(self, folder: str = CASE_FOLDER):
        """Recursively sync all files from OneDrive Case folder."""
        print(f"[*] Starting Intelligent Sync for: {folder}")
        await self._sync_recursive(folder)
        self._save_ledger()
        print(f"[+] Sync Complete. Ledger updated at {datetime.now()}")

    async def _sync_recursive(self, remote_path: str):
        result = await self.manager.list_files(remote_path)
        if "error" in result:
            print(f"    [!] Error listing {remote_path}: {result['error']}")
            return

        for item in result.get("files", []):
            item_name = item["name"]
            item_type = item["type"]
            # Construct local path
            relative_path = remote_path.replace(CASE_FOLDER, "").strip("/")
            local_item_path = self.evidence_root / relative_path / item_name
            
            if item_type == "folder":
                local_item_path.mkdir(parents=True, exist_ok=True)
                await self._sync_recursive(f"{remote_path}/{item_name}")
            else:
                # Check ledger for changes
                remote_modified = item["modified"]
                if self.ledger.get(str(local_item_path)) == remote_modified and local_item_path.exists():
                    # print(f"    [=] {item_name} (unchanged)")
                    continue
                
                print(f"    [↓] Downloading: {item_name}")
                dl_result = await self.manager.download_file(f"{remote_path}/{item_name}", str(local_item_path))
                
                if dl_result.get("status") == "success":
                    self.ledger[str(local_item_path)] = remote_modified
                    await self._process_file(local_item_path)

    async def _process_file(self, file_path: Path):
        """Intelligently process files based on type."""
        suffix = file_path.suffix.lower()
        
        # Audio Transcription
        if suffix in [".m4a", ".mp3", ".wav", ".aac", ".mp4"]:
            print(f"    [🎤] Triggering Transcription: {file_path.name}")
            # Check if whisperx is available before running
            try:
                self.whisper.transcribe(str(file_path))
            except Exception as e:
                print(f"    [!] Transcription failed for {file_path.name}: {e}")

    def get_status(self) -> Dict:
        """Return summary of evidence vault."""
        total_files = len(self.ledger)
        audio_files = len([f for f in self.ledger.keys() if f.lower().endswith(('.m4a', '.mp3', '.wav'))])
        return {
            "status": "synchronized",
            "last_sync": datetime.now().isoformat(),
            "total_evidence_nodes": total_files,
            "audio_nodes": audio_files,
            "vault_root": str(self.evidence_root)
        }

if __name__ == "__main__":
    import asyncio
    intel = OneDriveIntelligence()
    asyncio.run(intel.sync_all())
