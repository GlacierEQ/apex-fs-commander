#!/usr/bin/env python3
# ==============================================================================
# APEX FORENSIC ORGANIZER — Chunk-Powered Multi-Tier Classifier
# Platform: macOS, iOS iSH
# Case: 1FDV-23-0001009 | GlacierEQ / Casey Barton
# ==============================================================================

import os
import sys
import json
import hashlib
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Core Paths
DROPBOX_ROOT = Path("/Users/macarena1/Library/CloudStorage/Dropbox-Kahalainspector/Kahala Home Inspectors")
ORGANIZED_DIR = DROPBOX_ROOT / "Case_1FDV-23-0001009_ORGANIZED"
STATE_FILE = ORGANIZED_DIR / "dropbox_organization_state.json"

# Forensic Categories
CATEGORIES = {
    "01_COURT_FILINGS/01a_Docket_Entries": [r"docket", r"filing", r"court_view", r"case_view", r"minutes", r"dkt", r"my case view"],
    "01_COURT_FILINGS/01b_Casey_Motions": [r"motion.*casey", r"petition.*casey", r"motion.*glacier", r"visitation_enforcement"],
    "01_COURT_FILINGS/01c_Teresa_Brower_Motions": [r"motion.*teresa", r"petition.*teresa", r"motion.*brower"],
    "01_COURT_FILINGS/01d_Court_Orders": [r"order", r"judgment", r"decree", r"ruling", r"custody_order"],
    "01_COURT_FILINGS/01e_Notices": [r"notice", r"summons", r"subpoena"],
    "02_EVIDENCE/02c_Medical_Records": [r"medical", r"doctor", r"hospital", r"therapy", r"prescription", r"pediatrician", r"clinic"],
    "02_EVIDENCE/02d_School_Records": [r"school", r"report_card", r"teacher", r"grade", r"attendance", r"enrollment", r"classroom"],
    "02_EVIDENCE/02e_Financial": [r"bank", r"statement", r"tax", r"invoice", r"receipt", r"payment", r"child_support", r"check"],
    "02_EVIDENCE/02f_Communications": [r"sms", r"chat", r"message", r"email", r"whatsapp", r"text", r"call_log", r"conversation", r"transcript"],
    "02_EVIDENCE/02g_Photos_Videos": [r"\.jpg$", r"\.png$", r"\.heic$", r"\.m4a$", r"\.mp3$", r"\.mp4$", r"\.mov$", r"\.wav$", r"audio", r"recording"],
    "03_DISCOVERY/03a_Requests_Sent": [r"discovery_request", r"interrogatories_sent", r"production_request"],
    "03_DISCOVERY/03b_Responses_Received": [r"discovery_response", r"production_received"],
    "04_LEGAL_RESEARCH/04a_Hawaii_Case_Law": [r"case_law", r"hawaii_ruling", r"opinion"],
    "04_LEGAL_RESEARCH/04b_Statutes": [r"statute", r"hrs_", r"hawaii_revised"],
    "09_REFERENCE/09e_Tracking_Spreadsheets": [r"\.xlsx$", r"\.csv$", r"tracker", r"spreadsheet", r"log_sheet"],
    "11_TECH_TOOLS/11a_Software_Installers": [r"\.deb$", r"\.dmg$", r"\.exe$", r"\.apk$", r"\.appimage$", r"\.pkg\.tar"],
    "11_TECH_TOOLS/11b_System_Backups": [r"antigravity", r"backup", r"\.tar\.gz$", r"takeout", r"\.tar$"],
    "11_TECH_TOOLS/11c_Apex_Code": [r"apex", r"genesis_prime", r"\.jsx$", r"\.py$", r"\.sh$"]
}

# Source Directories to Scan
SOURCES = [
    Path("/Users/macarena1/Library/CloudStorage/Dropbox-Kahalainspector/Kahala Home Inspectors"),
    Path("/Users/macarena1/Library/CloudStorage/Dropbox-Kahalainspector/Kahalainspector Team Folder")
]

def get_file_md5(file_path: Path) -> str:
    """Calculate a fast fingerprint (Size + MTime) instead of full MD5 for cloud efficiency."""
    try:
        stat_info = file_path.stat()
        # Fast fingerprint: Size + Last Modified Time
        fingerprint = f"{stat_info.st_size}_{stat_info.st_mtime}"
        return hashlib.md5(fingerprint.encode()).hexdigest()
    except Exception:
        return ""

def load_state() -> Dict[str, Any]:
    """Load processing state to support incremental chunk updates."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"processed_files": {}, "stats": {}}
    return {"processed_files": {}, "stats": {}}

def save_state(state: Dict[str, Any]):
    """Save processing state to guarantee progress is safe."""
    ORGANIZED_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

def classify_file(file_path: Path) -> str:
    """Classify file into correct forensic subdirectory using regex matchers."""
    name_lower = file_path.name.lower()
    # Check if part of the TARGET DOSSIER or related intel
    if "dossier" in name_lower or "intel" in name_lower:
        return "11_TECH_TOOLS/11c_Apex_Code"
        
    parent_name = file_path.parent.name.lower()
    # Limit parent directory matching
    parent_check = parent_name if parent_name in ["1009", "android", "audio", "iphone", "one drive", "glaciergdrive"] else ""
    
    # 1. Attempt regex classification
    for category, patterns in CATEGORIES.items():
        for pat in patterns:
            if re.search(pat, name_lower) or (parent_check and re.search(pat, parent_check)):
                return category
                
    # 2. Fallback by extension
    ext = file_path.suffix.lower()
    if ext in [".m4a", ".mp3", ".wav", ".mp4", ".mov", ".jpg", ".heic", ".png"]:
        return "02_EVIDENCE/02g_Photos_Videos"
    if ext in [".xlsx", ".csv"]:
        return "09_REFERENCE/09e_Tracking_Spreadsheets"
    if ext in [".pdf", ".docx", ".doc"]:
        return "10_ARCHIVE/10c_Unclassified"
        
    return "10_ARCHIVE/10c_Unclassified"

def run_organization(chunk_size: int = 100, use_symlinks: bool = True):
    """
    Scan all Dropbox source folders, classify files, and organize them.
    Saves state in chunks of files to keep execution persistent and resumes seamlessly.
    """
    print(f"🚀 STARTING FORENSIC DROPBOX CLASSIFIER...")
    print(f"Mode: {'SYMLINK (Lightweight)' if use_symlinks else 'COPY (Preservation)'}")
    print(f"Destination Vault: {ORGANIZED_DIR}\n")

    state = load_state()
    processed_files = state.setdefault("processed_files", {})
    stats = state.setdefault("stats", {})

    total_scanned = 0
    total_organized = 0
    total_skipped = 0

    # Ensure all target categories directories exist
    for category in CATEGORIES.keys():
        (ORGANIZED_DIR / category).mkdir(parents=True, exist_ok=True)
    (ORGANIZED_DIR / "10_ARCHIVE/10c_Unclassified").mkdir(parents=True, exist_ok=True)

    pending_files = []

    # 1. Collect all files in source folders (top-level and selective subdirs)
    for src in SOURCES:
        if not src.exists():
            print(f"  ⚠️ Source folder missing: {src.name}")
            continue
        print(f"🔍 Scanning: {src.name}...")
        
        # Scan root
        for item in src.iterdir():
            if item.is_file():
                if item.name.startswith(".") or item.name == "Desktop.ini":
                    continue
                if ORGANIZED_DIR.name in str(item): # Avoid self-scanning
                    continue
                pending_files.append(item)
        
        # Selective recursive scan for known evidence buckets
        for sub in ["Android", "iPhone", "Audio", "GlacierGDRIVE"]:
            sub_path = src / sub
            if sub_path.exists() and sub_path.is_dir():
                print(f"   → Deep scanning: {sub}...")
                for item in sub_path.rglob("*"):
                    if item.is_file() and not item.name.startswith("."):
                        pending_files.append(item)

    print(f"\n📋 Total pending files discovered: {len(pending_files)}")

    # 2. Process in manageable chunks of 'chunk_size'
    for i in range(0, len(pending_files), chunk_size):
        chunk = pending_files[i:i+chunk_size]
        print(f"\n📦 Processing chunk {i // chunk_size + 1} ({len(chunk)} files)...")

        for file_path in chunk:
            total_scanned += 1
            src_str = str(file_path)

            # Skip if already processed and target exists
            if src_str in processed_files and processed_files[src_str].get("status") == "success":
                target_path = Path(processed_files[src_str]["destination"])
                if target_path.exists():
                    total_skipped += 1
                    continue

            # Classify file
            category = classify_file(file_path)
            target_subfolder = ORGANIZED_DIR / category
            dest_file = target_subfolder / file_path.name

            try:
                if use_symlinks:
                    if dest_file.exists() or dest_file.is_symlink():
                        dest_file.unlink()
                    os.symlink(file_path, dest_file)
                else:
                    shutil.copy2(file_path, dest_file)
                
                # Calculate MD5 for state tracking
                md5 = get_file_md5(file_path)
                
                # Mark as processed
                processed_files[src_str] = {
                    "status": "success",
                    "destination": str(dest_file),
                    "category": category,
                    "md5": md5,
                    "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
                    "processed_at": datetime.now().timestamp(),
                    "type": "symlink" if use_symlinks else "copy"
                }
                
                stats[category] = stats.get(category, 0) + 1
                total_organized += 1
                
            except Exception as e:
                print(f"  ❌ Error processing {file_path.name}: {str(e)}")
                processed_files[src_str] = {
                    "status": "error",
                    "error": str(e)
                }

        # Save state after completing each chunk block
        save_state(state)
        print(f"  💾 State persisted. Progress: {total_scanned}/{len(pending_files)} files.")

    print(f"\n🎉 DROPBOX ORGANIZING COMPLETED!")
    print(f"Total Scanned: {total_scanned}")
    print(f"Total Organized: {total_organized}")
    print(f"Total Skipped (already completed): {total_skipped}")

    # Display Breakdown of Organized Folders
    print("\n📊 EVIDENCE BREAKDOWN:")
    for cat, count in sorted(stats.items()):
        if count > 0:
            print(f"  📂 {cat}: {count} files")

if __name__ == "__main__":
    run_organization()
