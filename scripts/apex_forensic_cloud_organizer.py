#!/usr/bin/env python3
# ==============================================================================
# APEX FORENSIC CLOUD ORGANIZER — Chunk-Powered Multi-Tier Classifier
# Platform: macOS, iOS iSH
# Case: 1FDV-23-0001009 | GlacierEQ / Casey Barton
# ==============================================================================

import os
import sys
import json
import hashlib
import shutil
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Core Paths
DEFAULT_DROPBOX_ORG = Path("/Users/macarena1/Library/CloudStorage/Dropbox-Kahalainspector/Kahala Home Inspectors/Case_1FDV-23-0001009_ORGANIZED")
DEFAULT_ONEDRIVE_SRC = Path("/Users/macarena1/Library/CloudStorage/OneDrive-Personal/Documents")
ONEDRIVE_VAULT = Path("/Users/macarena1/Library/CloudStorage/OneDrive-Personal/Case_1FDV-23-0001009_ORGANIZED")
ICLOUD_VAULT = Path("/Users/macarena1/Library/Mobile Documents/com~apple~CloudDocs")

STATE_FILE = Path("/Users/macarena1/dev/projects/apex-fs-commander/logs/cloud_organization_state.json")
MANIFEST_OUT = Path("/Users/macarena1/dev/projects/apex-fs-commander/logs/FORENSIC_CLOUD_MANIFEST.md")


# Emojis for beautiful reports
EMOJIS = {
    "docket": "⚖️",
    "motion": "📝",
    "order": "📜",
    "notice": "🔔",
    "medical": "🏥",
    "school": "🏫",
    "financial": "💳",
    "phone": "📞",
    "chat": "💬",
    "media": "🎬",
    "discovery": "🔍",
    "research": "📚",
    "tracking": "📊",
    "unclassified": "🗂️"
}

# Advanced Forensic Multi-Tier Classifier Taxonomy
ONEDRIVE_TAXONOMY = {
    "01_COURT_FILINGS/01a_Docket_Entries": [r"docket", r"filing", r"court_view", r"case_view", r"minutes", r"dkt", r"my case view"],
    "01_COURT_FILINGS/01b_Casey_Motions": [r"motion.*casey", r"petition.*casey", r"motion.*glacier", r"visitation_enforcement"],
    "01_COURT_FILINGS/01c_Teresa_Brower_Motions": [r"motion.*teresa", r"petition.*teresa", r"motion.*brower"],
    "01_COURT_FILINGS/01d_Court_Orders": [r"order", r"judgment", r"decree", r"ruling", r"custody_order"],
    "01_COURT_FILINGS/01e_Notices": [r"notice", r"summons", r"subpoena"],
    "02_EVIDENCE/02c_Medical_Records": [r"medical", r"doctor", r"hospital", r"therapy", r"prescription", r"pediatrician", r"clinic"],
    "02_EVIDENCE/02d_School_Records": [r"school", r"report_card", r"teacher", r"grade", r"attendance", r"enrollment", r"classroom"],
    "02_EVIDENCE/02e_Financial": [r"bank", r"statement", r"tax", r"invoice", r"receipt", r"payment", r"child_support", r"check"],
    "02_EVIDENCE/02f_Communications/Phone_Records": [r"\b\d{10}\b"], # Regex for 10-digit numbers!
    "02_EVIDENCE/02f_Communications/Chats_and_Emails": [r"sms", r"chat", r"message", r"email", r"whatsapp", r"text", r"call_log", r"conversation", r"transcript"],
    "02_EVIDENCE/02g_Photos_Videos": [r"\.jpg$", r"\.png$", r"\.heic$", r"\.m4a$", r"\.mp3$", r"\.mp4$", r"\.mov$", r"\.wav$", r"audio", r"recording"],
    "03_DISCOVERY/03a_Requests_Sent": [r"discovery_request", r"interrogatories_sent", r"production_request"],
    "03_DISCOVERY/03b_Responses_Received": [r"discovery_response", r"production_received"],
    "04_LEGAL_RESEARCH/04a_Hawaii_Case_Law": [r"case_law", r"hawaii_ruling", r"opinion"],
    "04_LEGAL_RESEARCH/04b_Statutes": [r"statute", r"hrs_", r"hawaii_revised"],
    "09_REFERENCE/09e_Tracking_Spreadsheets": [r"\.xlsx$", r"\.csv$", r"tracker", r"spreadsheet", r"log_sheet"]
}

# Mapping classifications to iCloud Emoji-Prefixed folder structure
ICLOUD_MAPPING = {
    "01_COURT_FILINGS/01a_Docket_Entries": "⚖️_LEGAL_OPS/Court_Filings",
    "01_COURT_FILINGS/01b_Casey_Motions": "⚖️_LEGAL_OPS/Court_Filings",
    "01_COURT_FILINGS/01c_Teresa_Brower_Motions": "⚖️_LEGAL_OPS/Court_Filings",
    "01_COURT_FILINGS/01d_Court_Orders": "⚖️_LEGAL_OPS/Court_Filings",
    "01_COURT_FILINGS/01e_Notices": "⚖️_LEGAL_OPS/Court_Filings",
    "02_EVIDENCE/02c_Medical_Records": "⚖️_LEGAL_OPS/Medical_Records",
    "02_EVIDENCE/02d_School_Records": "⚖️_LEGAL_OPS/School_Records",
    "02_EVIDENCE/02e_Financial": "📝_DOCUMENTS/Financial",
    "02_EVIDENCE/02f_Communications/Phone_Records": "📝_DOCUMENTS/Phone_Records",
    "02_EVIDENCE/02f_Communications/Chats_and_Emails": "📝_DOCUMENTS/Chats_and_Emails",
    "02_EVIDENCE/02g_Photos_Videos": "🎬_MEDIA",
    "03_DISCOVERY/03a_Requests_Sent": "⚖️_LEGAL_OPS/Discovery",
    "03_DISCOVERY/03b_Responses_Received": "⚖️_LEGAL_OPS/Discovery",
    "04_LEGAL_RESEARCH/04a_Hawaii_Case_Law": "⚖️_LEGAL_OPS/Legal_Research",
    "04_LEGAL_RESEARCH/04b_Statutes": "⚖️_LEGAL_OPS/Legal_Research",
    "09_REFERENCE/09e_Tracking_Spreadsheets": "🧠_KNOWLEDGE_BANK"
}

def get_file_hashes(file_path: Path) -> Tuple[str, str]:
    """Calculate both SHA-256 and MD5 hashes of a file efficiently in 64KB chunks."""
    sha256_hasher = hashlib.sha256()
    md5_hasher = hashlib.md5()
    try:
        # Avoid opening 0-byte files (can hang on cloud storage placeholders)
        if file_path.stat().st_size == 0:
            return "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "d41d8cd98f00b204e9800998ecf8427e"
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256_hasher.update(chunk)
                md5_hasher.update(chunk)
        return sha256_hasher.hexdigest(), md5_hasher.hexdigest()
    except Exception:
        return "", ""

def load_state() -> Dict[str, Any]:
    """Load processing state to support incremental chunk updates."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"processed_files": {}, "stats": {}}
    return {"processed_files": {}, "stats": {}}

def save_state(state: Dict[str, Any]):
    """Save processing state securely."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

def classify_file(file_path: Path) -> Tuple[str, str]:
    """Classify file and return category code and classification reasoning."""
    name_lower = file_path.name.lower()
    
    # Check for 10-digit phone number in name (e.g., 5126038798.pdf)
    # Exclude other extension numbers or short sequences
    clean_name = file_path.stem
    if re.search(r'^\d{10}$', clean_name) or (len(clean_name) == 10 and clean_name.isdigit()):
        return "02_EVIDENCE/02f_Communications/Phone_Records", "10-digit numeric naming pattern represents phone/background check file"

    # Attempt standard regex matching
    for category, patterns in ONEDRIVE_TAXONOMY.items():
        # Skip the phone regex check here as it is handled specifically above
        if category == "02_EVIDENCE/02f_Communications/Phone_Records":
            continue
        for pat in patterns:
            if re.search(pat, name_lower):
                return category, f"Matches pattern: {pat}"

    # General extension fallbacks
    ext = file_path.suffix.lower()
    if ext in [".m4a", ".mp3", ".wav", ".mp4", ".mov"]:
        return "02_EVIDENCE/02g_Photos_Videos", "Audio/video extension classification"
    if ext in [".jpg", ".heic", ".png", ".jpeg"]:
        return "02_EVIDENCE/02g_Photos_Videos", "Image extension classification"
    if ext in [".xlsx", ".csv"]:
        return "09_REFERENCE/09e_Tracking_Spreadsheets", "Spreadsheet extension classification"
    if ext in [".pdf", ".docx", ".doc"]:
        return "10_ARCHIVE/10c_Unclassified", "Unclassified document fallback"

    return "10_ARCHIVE/10c_Unclassified", "Default fallback category"

def check_online_only(file_path: Path) -> bool:
    """Check if file is an online-only placeholder on macOS (returns True if dataless)."""
    try:
        stat_info = file_path.stat()
        # On macOS, dataless/online files have st_blocks == 0 despite reporting positive size
        if stat_info.st_size > 0 and stat_info.st_blocks == 0:
            return True
        return False
    except Exception:
        return False

def generate_markdown_manifest(state: Dict[str, Any]):
    """Generate a clean, professional forensic manifest markdown report of all processed files."""
    stats = state.get("stats", {})
    processed = state.get("processed_files", {})
    
    lines = [
        "# APEX Forensic Cloud Organization Manifest",
        f"**Compiled At**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} HST  ",
        "**Status**: 🟢 ACTIVE & INTEGRITY SECURED  ",
        "",
        "## 📊 Summary Statistics",
        "| Category | Files Organized | Icon |",
        "| :--- | :---: | :---: |"
    ]
    
    for category, count in sorted(stats.items()):
        if count > 0:
            # Determine appropriate icon
            icon = "🗂️"
            for key, val in EMOJIS.items():
                if key in category.lower():
                    icon = val
                    break
            lines.append(f"| `{category}` | **{count}** | {icon} |")
            
    lines.extend([
        "",
        "---",
        "",
        "## 📁 Detailed Audit Trail (Last 100 Files)",
        "| Original Filename | Hash (SHA-256) | Category | Size (KB) |",
        "| :--- | :--- | :--- | :---: |"
    ])
    
    # Sort processed files by processed_at timestamp descending and show last 100
    sorted_items = sorted(
        [(k, v) for k, v in processed.items() if v.get("status") == "success"],
        key=lambda x: x[1].get("processed_at", 0),
        reverse=True
    )[:100]
    
    for src, info in sorted_items:
        name = Path(src).name
        sha = info.get("sha256", "N/A")[:12] + "..." if info.get("sha256") else "N/A"
        category = info.get("category", "Unclassified")
        size_kb = f"{info.get('size_bytes', 0) / 1024:.1f}"
        lines.append(f"| {name} | `{sha}` | `{category}` | {size_kb} |")
        
    MANIFEST_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"📄 Forensic manifest markdown generated successfully at {MANIFEST_OUT.name}")

def run_organization(dry_run: bool = False, chunk_size: int = 100, source_folder: Path = DEFAULT_ONEDRIVE_SRC, recursive: bool = False):
    """Scan the target source directory, classify files, copy to vaults, save state in chunks."""
    print("=" * 78)
    print(f"🔥 APEX FORENSIC CLOUD CLASSIFIER - {'DRY RUN' if dry_run else 'ACTIVE ENGINE'}")
    print("=" * 78)
    print(f"Source Folder:  {source_folder}")
    print(f"OneDrive Vault: {ONEDRIVE_VAULT}")
    print(f"iCloud Vault:   {ICLOUD_VAULT}")
    print(f"Recursive Scan: {recursive}")
    print("-" * 78)

    state = load_state()
    processed_files = state.setdefault("processed_files", {})
    stats = state.setdefault("stats", {})

    # Ensure source exists
    if not source_folder.exists():
        print(f"❌ Error: Source directory does not exist: {source_folder}")
        sys.exit(1)

    # Gather unorganized files
    pending_files = []
    if recursive:
        print("🔍 Scanning source directory recursively (skipping system/code directories)...")
        folders_to_skip = {'github', '.git', 'node_modules', 'custom office templates', '.trash', '.tmp.driveupload'}
        for root, dirs, files in os.walk(source_folder):
            # Prune directories in-place to prevent os.walk from entering skipped folders
            dirs[:] = [d for d in dirs if d.lower() not in folders_to_skip]
            for f in files:
                if f.startswith(".") or f == "Desktop.ini" or "Icon\r" in f:
                    continue
                pending_files.append(Path(root) / f)
    else:
        print("🔍 Scanning source directory root non-recursively (instant/safe mode)...")
        try:
            for item in source_folder.iterdir():
                if item.is_file():
                    if item.name.startswith(".") or item.name == "Desktop.ini" or "Icon\r" in item.name:
                        continue
                    pending_files.append(item)
        except Exception as e:
            print(f"❌ Error reading source directory root: {e}")
            sys.exit(1)

    print(f"📋 Discovered {len(pending_files)} files to organize.")

    if not pending_files:
        print("✅ No unorganized files found.")
        return

    # Process in chunks
    total_processed = 0
    total_copied_onedrive = 0
    total_copied_icloud = 0
    total_skipped = 0

    for i in range(0, len(pending_files), chunk_size):
        chunk = pending_files[i:i+chunk_size]
        print(f"\n📦 Processing chunk {i // chunk_size + 1} ({len(chunk)} files)...")

        for file_path in chunk:
            src_str = str(file_path)
            total_processed += 1

            # Check if already processed
            if src_str in processed_files and processed_files[src_str].get("status") == "success":
                # Ensure it still exists in destinations
                onedrive_dest = Path(processed_files[src_str].get("onedrive_dest", ""))
                icloud_dest = Path(processed_files[src_str].get("icloud_dest", ""))
                if (onedrive_dest.exists() or not onedrive_dest) and (icloud_dest.exists() or not icloud_dest):
                    total_skipped += 1
                    continue

            # Safe guard against online-only OneDrive files
            if check_online_only(file_path):
                print(f"  ⚠️ Skipping Online-Only Cloud Placeholder: {file_path.name}")
                processed_files[src_str] = {
                    "status": "online_only",
                    "reason": "File resides strictly in the cloud and must be downloaded manually before local hash auditing"
                }
                total_skipped += 1
                continue

            # Compute forensic hashes
            sha256, md5 = get_file_hashes(file_path)
            if not sha256:
                print(f"  ❌ Error: Unable to read file content for hashing: {file_path.name}")
                continue

            # Classify file
            category, reason = classify_file(file_path)
            print(f"  📂 Classifying {file_path.name[:35]} -> {category} ({reason})")

            # Setup target file destinations
            onedrive_dest_sub = ONEDRIVE_VAULT / category
            onedrive_target_file = onedrive_dest_sub / file_path.name

            # Resolve iCloud subfolder mapping
            icloud_folder_mapped = ICLOUD_MAPPING.get(category, "🗂️_ARCHIVES/Unclassified")
            icloud_dest_sub = ICLOUD_VAULT / icloud_folder_mapped
            icloud_target_file = icloud_dest_sub / file_path.name

            if dry_run:
                print(f"    [DRY-RUN] Would copy to OneDrive: {onedrive_target_file.name}")
                print(f"    [DRY-RUN] Would copy to iCloud:   {icloud_target_file.name}")
                processed_files[src_str] = {
                    "status": "dry_run",
                    "category": category,
                    "reason": reason,
                    "sha256": sha256
                }
                continue

            # Active Mode - File Copies with Metadata Preservation
            success_onedrive = False
            success_icloud = False

            # Create destination dirs
            onedrive_dest_sub.mkdir(parents=True, exist_ok=True)
            if ICLOUD_VAULT.exists():
                icloud_dest_sub.mkdir(parents=True, exist_ok=True)

            # Copy to OneDrive Organized Vault
            try:
                shutil.copy2(file_path, onedrive_target_file)
                success_onedrive = True
                total_copied_onedrive += 1
            except Exception as e:
                print(f"    ❌ Error copying to OneDrive: {str(e)}")

            # Copy to iCloud Vault
            if ICLOUD_VAULT.exists():
                try:
                    shutil.copy2(file_path, icloud_target_file)
                    success_icloud = True
                    total_copied_icloud += 1
                except Exception as e:
                    print(f"    ❌ Error copying to iCloud: {str(e)}")
            else:
                print("    ℹ️ iCloud vault path not active on this node. Skipping iCloud replication.")

            if success_onedrive or success_icloud:
                processed_files[src_str] = {
                    "status": "success",
                    "onedrive_dest": str(onedrive_target_file) if success_onedrive else "",
                    "icloud_dest": str(icloud_target_file) if success_icloud else "",
                    "category": category,
                    "sha256": sha256,
                    "md5": md5,
                    "size_bytes": file_path.stat().st_size,
                    "reason": reason,
                    "processed_at": datetime.now().timestamp()
                }
                stats[category] = stats.get(category, 0) + 1

        # Save progress and generate manifest after completing each chunk
        if not dry_run:
            save_state(state)
            generate_markdown_manifest(state)
            print(f"  💾 Progress persisted: {total_processed}/{len(pending_files)} files analyzed.")

    # Final Summary Report
    print("\n" + "=" * 78)
    print("🏆 FORENSIC CLOUD SYNCHRONIZATION COMPLETED")
    print("=" * 78)
    print(f"Total Scanned:      {total_processed}")
    print(f"Replicated to OneDrive: {total_copied_onedrive}")
    print(f"Replicated to iCloud:   {total_copied_icloud}")
    print(f"Skipped (Completed):    {total_skipped}")
    print("-" * 78)
    
    print("📊 FOLDER CLASSIFICATION AUDIT:")
    for cat, count in sorted(stats.items()):
        if count > 0:
            icon = EMOJIS.get(cat.split("/")[0].lower(), "🗂️")
            for key, val in EMOJIS.items():
                if key in cat.lower():
                    icon = val
                    break
            print(f"  {icon} {cat}: {count} files")
    print("=" * 78)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APEX Forensic Cloud Organizer")
    parser.add_argument("--dry-run", action="store_true", help="Simulate organization patterns without copying files")
    parser.add_argument("--recursive", action="store_true", help="Scan source directory recursively (skipping code/system directories)")
    parser.add_argument("--chunk-size", type=int, default=100, help="Batch boundary sizing to save state (default: 100)")
    parser.add_argument("--source", type=str, default=str(DEFAULT_ONEDRIVE_SRC), help="Target source path to analyze")
    args = parser.parse_args()

    run_organization(
        dry_run=args.dry_run,
        chunk_size=args.chunk_size,
        source_folder=Path(args.source),
        recursive=args.recursive
    )
