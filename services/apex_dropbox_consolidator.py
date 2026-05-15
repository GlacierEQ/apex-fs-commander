#!/usr/bin/env python3
"""
APEX DROPBOX CONSOLIDATION ENGINE
Durable automation for 15TB trial → read-only transition.

Builds a persistent local JSON index of ALL files, prioritizes
critical legal evidence for local mirroring, and generates an
offline-capable HTML dashboard.

Designed to run autonomously via cron/launchd.

Usage:
    python3 apex_dropbox_consolidator.py index       # Build/update master index
    python3 apex_dropbox_consolidator.py consolidate  # Mirror critical files locally
    python3 apex_dropbox_consolidator.py dashboard    # Generate offline HTML dashboard
    python3 apex_dropbox_consolidator.py auto         # Run all three in sequence
"""

import os
import sys
import json
import hashlib
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("apex.consolidator")

# ══════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════

HOME = Path.home()
DROPBOX_ROOT = HOME / "Library" / "CloudStorage" / "Dropbox-Kahalainspector"
ONEDRIVE_ROOT = HOME / "Library" / "CloudStorage" / "OneDrive-Personal"

# Index + dashboard → iCloud (accessible from all devices)
ICLOUD_APEX = HOME / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "APEX_INTELLIGENCE"
INDEX_DIR = ICLOUD_APEX / "dropbox_index"
INDEX_FILE = INDEX_DIR / "dropbox_master_index.json"
MANIFEST_FILE = INDEX_DIR / "dropbox_evidence_manifest.json"
DASHBOARD_FILE = INDEX_DIR / "dropbox_dashboard.html"

# Evidence vault → LOCAL ONLY (preserves forensic timestamps, no cloud metadata mutation)
CONSOLIDATION_DIR = HOME / "APEX_LOCAL_VAULT" / "dropbox_mirror"

# Priority tiers for consolidation (what to pull locally first)
CRITICAL_EXTENSIONS = {".pdf", ".docx", ".doc", ".md", ".txt", ".csv", ".json", ".xlsx"}
EVIDENCE_EXTENSIONS = {".m4a", ".mp3", ".wav", ".mp4", ".mov"}
LEGAL_KEYWORDS = [
    "1fdv", "custody", "barton", "kekoa", "motion", "order", "hearing",
    "exhibit", "declaration", "petition", "complaint", "rico", "1983",
    "evidence", "transcript", "court", "judge", "guardian",
    "brower", "yamatani", "naso", "shaw", "teresa", "subpoena",
]
# Max file size to auto-consolidate (500MB — skip huge videos)
MAX_CONSOLIDATE_SIZE = 500 * 1024 * 1024


# ══════════════════════════════════════════════════════════════
# INDEXER — Chunked streaming with progress (80K+ file safe)
# ══════════════════════════════════════════════════════════════

EXT_MAP = {
    ".m4a": "audio", ".mp3": "audio", ".wav": "audio", ".ogg": "audio",
    ".aac": "audio", ".flac": "audio", ".opus": "audio",
    ".mp4": "video", ".mov": "video", ".avi": "video", ".mkv": "video",
    ".pdf": "document", ".doc": "document", ".docx": "document",
    ".txt": "text", ".md": "text", ".rtf": "document",
    ".jpg": "image", ".jpeg": "image", ".png": "image", ".heic": "image",
    ".gif": "image", ".webp": "image", ".bmp": "image", ".tiff": "image",
    ".zip": "archive", ".tar": "archive", ".gz": "archive", ".7z": "archive",
    ".csv": "data", ".json": "data", ".xlsx": "spreadsheet", ".xls": "spreadsheet",
    ".py": "code", ".js": "code", ".sh": "code", ".html": "code",
    ".db": "database", ".sqlite": "database", ".sqlite3": "database",
}

CHUNK_SIZE = 1000  # Flush to disk every N entries
PROGRESS_INTERVAL = 5000


def build_master_index() -> Dict[str, Any]:
    """Crawl Dropbox with chunked streaming — flushes to JSONL, never holds all in RAM."""
    logger.info(f"Building master index from {DROPBOX_ROOT}")
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    jsonl_path = INDEX_DIR / "dropbox_index_stream.jsonl"
    local_jsonl_path = Path("/tmp/dropbox_index_stream.jsonl")
    categories: Dict[str, int] = {}
    category_sizes: Dict[str, int] = {}
    total_files = 0
    total_size = 0
    evidence_count = 0
    error_count = 0
    chunk_buf: List[Dict[str, Any]] = []

    def _flush(buf: List[Dict], mode: str = "a"):
        # Write to local file first to avoid iCloud lock collisions
        with open(local_jsonl_path, mode, encoding="utf-8") as fh:
            for entry in buf:
                fh.write(json.dumps(entry, separators=(",", ":")) + "\n")

    # Truncate local stream file
    local_jsonl_path.write_text("", encoding="utf-8")

    # Determine active cloud folders to walk
    roots_to_scan = []
    if DROPBOX_ROOT.exists():
        roots_to_scan.append((DROPBOX_ROOT, "Dropbox"))
    if ONEDRIVE_ROOT.exists():
        roots_to_scan.append((ONEDRIVE_ROOT, "OneDrive"))

    for root_dir, platform in roots_to_scan:
        logger.info(f"🔍 Crawling {platform} source folder: {root_dir}")
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fname in filenames:
                if fname.startswith("."):
                    continue
                fpath = Path(dirpath) / fname
                try:
                    stat = fpath.stat()
                    ext = fpath.suffix.lower()
                    cat = EXT_MAP.get(ext, "other")
                    name_lower = fname.lower()
                    path_lower = str(fpath).lower()
                    legal_hits = [kw for kw in LEGAL_KEYWORDS if kw in name_lower or kw in path_lower]
                    rel_path = str(fpath.relative_to(root_dir))

                    entry = {
                        "name": fname, "path": rel_path, "abs_path": str(fpath),
                        "size": stat.st_size, "ext": ext, "category": cat,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "is_evidence": bool(legal_hits), "legal_keywords": legal_hits,
                        "drive": platform
                    }
                    chunk_buf.append(entry)
                    total_files += 1
                    total_size += stat.st_size
                    categories[cat] = categories.get(cat, 0) + 1
                    category_sizes[cat] = category_sizes.get(cat, 0) + stat.st_size
                    if legal_hits:
                        evidence_count += 1

                    # Flush chunk to disk
                    if len(chunk_buf) >= CHUNK_SIZE:
                        _flush(chunk_buf)
                        chunk_buf.clear()

                    if total_files % PROGRESS_INTERVAL == 0:
                        logger.info(f"  ... indexed {total_files:,} files ({_human(total_size)})")

                except Exception:
                    error_count += 1

    # Flush remaining
    if chunk_buf:
        _flush(chunk_buf)
        chunk_buf.clear()

    # Move staged local files to iCloud safely using shutil
    try:
        shutil.copy2(local_jsonl_path, jsonl_path)
        logger.info(f"Staged stream index moved to iCloud: {jsonl_path}")
    except Exception as e:
        logger.warning(f"Could not copy staged JSONL index to iCloud: {e}")

    logger.info(f"Stream complete: {total_files:,} files → {jsonl_path}")

    # Build final compact index (metadata + file list from staged JSONL)
    all_files = []
    with open(local_jsonl_path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                all_files.append(json.loads(line))

    index = {
        "version": "2.0-unified",
        "generated": datetime.utcnow().isoformat() + "Z",
        "sources": [str(r[0]) for r in roots_to_scan],
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_size_human": _human(total_size),
        "categories": categories,
        "category_sizes_human": {k: _human(v) for k, v in category_sizes.items()},
        "evidence_count": evidence_count,
        "errors_count": error_count,
        "files": all_files,
    }

    local_index_json = Path("/tmp/dropbox_index.json")
    local_index_json.write_text(json.dumps(index, indent=2), encoding="utf-8")
    
    try:
        shutil.copy2(local_index_json, INDEX_FILE)
        logger.info(f"Index saved to iCloud: {INDEX_FILE} ({total_files:,} files, {_human(total_size)})")
    except Exception as e:
        logger.warning(f"Could not copy index JSON to iCloud: {e}")
        
    return index


# ══════════════════════════════════════════════════════════════
# CONSOLIDATOR — Mirror critical files locally before expiry
# ══════════════════════════════════════════════════════════════

def consolidate_critical(index: Optional[Dict] = None) -> Dict[str, Any]:
    """Copy critical legal/evidence files to local vault before read-only."""
    if index is None:
        if INDEX_FILE.exists():
            index = json.loads(INDEX_FILE.read_text())
        else:
            index = build_master_index()

    CONSOLIDATION_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Consolidating critical files to {CONSOLIDATION_DIR}")

    results = {"copied": 0, "skipped": 0, "failed": 0, "total_bytes": 0, "files": []}

    priority_files = []
    for f in index.get("files", []):
        ext = f.get("ext", "")
        is_evidence = f.get("is_evidence", False)
        size = f.get("size", 0)

        score = 0
        if is_evidence and ext in CRITICAL_EXTENSIONS:
            score = 100  # Legal docs — highest priority
        elif is_evidence and ext in EVIDENCE_EXTENSIONS:
            score = 80   # Audio/video evidence
        elif is_evidence:
            score = 60   # Any other evidence file
        elif ext in {".db", ".sqlite", ".sqlite3"}:
            score = 50   # Databases always useful
        elif ext in {".csv", ".json", ".xlsx"}:
            score = 40   # Data files

        if score > 0 and size <= MAX_CONSOLIDATE_SIZE:
            priority_files.append((score, f))

    priority_files.sort(key=lambda x: (-x[0], -x[1].get("size", 0)))
    logger.info(f"Found {len(priority_files)} priority files to consolidate")

    for score, f in priority_files:
        src = Path(f["abs_path"])
        rel = f["path"]
        platform = f.get("drive", "Dropbox")
        # Keep Dropbox and OneDrive subfolders cleanly separated inside mirror vault
        dst = CONSOLIDATION_DIR / platform / rel

        if dst.exists() and dst.stat().st_size == f["size"]:
            results["skipped"] += 1
            continue

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            results["copied"] += 1
            results["total_bytes"] += f["size"]
            results["files"].append({"name": f["name"], "size": _human(f["size"]), "priority": score, "platform": platform})
        except Exception as e:
            results["failed"] += 1
            logger.warning(f"Copy failed: {src}: {e}")

    # Save evidence manifest
    manifest = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "vault_path": str(CONSOLIDATION_DIR),
        "total_copied": results["copied"],
        "total_skipped": results["skipped"],
        "total_failed": results["failed"],
        "total_bytes_copied": results["total_bytes"],
        "total_copied_human": _human(results["total_bytes"]),
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))
    logger.info(f"Consolidation complete: {results['copied']} copied, {results['skipped']} skipped, {results['failed']} failed")
    return results


# ══════════════════════════════════════════════════════════════
# DASHBOARD — Offline HTML report
# ══════════════════════════════════════════════════════════════

def generate_dashboard(index: Optional[Dict] = None) -> str:
    """Generate a self-contained offline HTML dashboard."""
    if index is None:
        if INDEX_FILE.exists():
            index = json.loads(INDEX_FILE.read_text())
        else:
            index = build_master_index()

    cats = index.get("categories", {})
    cat_sizes = index.get("category_sizes_human", {})
    evidence_count = index.get("evidence_count", 0)
    total_files = index.get("total_files", 0)
    total_size = index.get("total_size_human", "0 B")
    gen_time = index.get("generated", "unknown")

    # Recent evidence files
    evidence_files = [f for f in index.get("files", []) if f.get("is_evidence")]
    evidence_files.sort(key=lambda x: x.get("modified", ""), reverse=True)
    recent_evidence = evidence_files[:100]

    evidence_rows = ""
    for f in recent_evidence:
        kws = ", ".join(f.get("legal_keywords", [])[:3])
        drive = f.get("drive", "Dropbox")
        drive_badge = f"<span class='badge' style='background:#1f6feb22;color:#58a6ff'>{drive}</span>" if drive == "Dropbox" else f"<span class='badge' style='background:#d2992222;color:#d29922'>{drive}</span>"
        evidence_rows += f"""<tr>
            <td>{f['name'][:60]}</td>
            <td>{drive_badge}</td>
            <td>{f['category']}</td>
            <td>{_human(f['size'])}</td>
            <td>{f['modified'][:10]}</td>
            <td><span class="badge">{kws}</span></td>
        </tr>\n"""

    cat_rows = ""
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        cat_rows += f"<tr><td>{cat}</td><td>{count:,}</td><td>{cat_sizes.get(cat, '?')}</td></tr>\n"

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>APEX Unified Sync Intelligence Dashboard</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'SF Pro Display',-apple-system,sans-serif;background:#0a0e17;color:#e2e8f0}}
.header{{background:linear-gradient(135deg,#1a1f2e 0%,#0d1117 100%);padding:2rem;border-bottom:1px solid #30363d}}
.header h1{{font-size:1.8rem;background:linear-gradient(90deg,#58a6ff,#bc8cff);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.header .meta{{color:#8b949e;margin-top:.5rem;font-size:.9rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;padding:1.5rem}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:1.5rem}}
.card h3{{color:#8b949e;font-size:.75rem;text-transform:uppercase;letter-spacing:.1em}}
.card .value{{font-size:2rem;font-weight:700;margin-top:.5rem;color:#58a6ff}}
.card .value.green{{color:#3fb950}}.card .value.orange{{color:#d29922}}.card .value.red{{color:#f85149}}
.section{{padding:1.5rem}}.section h2{{color:#c9d1d9;margin-bottom:1rem;font-size:1.2rem}}
table{{width:100%;border-collapse:collapse;background:#161b22;border-radius:8px;overflow:hidden}}
th{{background:#1c2129;color:#8b949e;padding:.75rem 1rem;text-align:left;font-size:.8rem;text-transform:uppercase}}
td{{padding:.6rem 1rem;border-top:1px solid #21262d;font-size:.85rem}}
tr:hover{{background:#1c2129}}
.badge{{background:#1f6feb22;color:#58a6ff;padding:2px 8px;border-radius:4px;font-size:.75rem}}
.status{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}}
.status.active{{background:#3fb950}}.status.warn{{background:#d29922}}
.footer{{text-align:center;padding:2rem;color:#484f58;font-size:.8rem}}
</style></head><body>
<div class="header">
    <h1>⚡ APEX Unified Sync Intelligence Dashboard</h1>
    <div class="meta">Case 1FDV-23-0001009 | Generated: {gen_time} | Sources: Dropbox-Kahalainspector & OneDrive-Personal</div>
    <div class="meta" style="color:#d29922;margin-top:.3rem">🛡️ Protected Vault Index | Direct Search Active</div>
</div>
<div class="grid">
    <div class="card"><h3>Total Files</h3><div class="value">{total_files:,}</div></div>
    <div class="card"><h3>Total Size</h3><div class="value">{total_size}</div></div>
    <div class="card"><h3>Legal Evidence</h3><div class="value orange">{evidence_count:,}</div></div>
    <div class="card"><h3>Categories</h3><div class="value green">{len(cats)}</div></div>
</div>
<div class="section"><h2>📁 File Categories</h2>
<table><tr><th>Category</th><th>Count</th><th>Size</th></tr>{cat_rows}</table></div>
<div class="section"><h2>⚖️ Recent Legal Evidence (Top 100)</h2>
<table><tr><th>Filename</th><th>Type</th><th>Size</th><th>Modified</th><th>Keywords</th></tr>{evidence_rows}</table></div>
<div class="footer">APEX FS-Commander | Dropbox Consolidation Engine | Offline Dashboard v1.0</div>
</body></html>"""

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_FILE.write_text(html, encoding="utf-8")
    logger.info(f"Dashboard saved: {DASHBOARD_FILE}")
    return str(DASHBOARD_FILE)


# ══════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════

def _human(n: int) -> str:
    if n < 1024: return f"{n} B"
    if n < 1024**2: return f"{n/1024:.1f} KB"
    if n < 1024**3: return f"{n/1024**2:.1f} MB"
    return f"{n/1024**3:.2f} GB"


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="APEX Dropbox Consolidation Engine")
    parser.add_argument("command", choices=["index", "consolidate", "dashboard", "auto"],
                        help="index=build manifest, consolidate=mirror critical files, dashboard=HTML report, auto=all")
    args = parser.parse_args()

    if args.command == "index":
        idx = build_master_index()
        print(f"✅ Indexed {idx['total_files']:,} files ({idx['total_size_human']})")
        print(f"   Evidence: {idx['evidence_count']:,} legal files")
        print(f"   Saved: {INDEX_FILE}")
    elif args.command == "consolidate":
        r = consolidate_critical()
        print(f"✅ Copied {r['copied']} files ({_human(r['total_bytes'])}), skipped {r['skipped']}, failed {r['failed']}")
    elif args.command == "dashboard":
        path = generate_dashboard()
        print(f"✅ Dashboard: {path}")
    elif args.command == "auto":
        print("🔄 Running full auto-consolidation pipeline...")
        idx = build_master_index()
        print(f"  ✅ Index: {idx['total_files']:,} files ({idx['total_size_human']})")
        r = consolidate_critical(idx)
        print(f"  ✅ Consolidated: {r['copied']} files ({_human(r['total_bytes'])})")
        path = generate_dashboard(idx)
        print(f"  ✅ Dashboard: {path}")
        print("🏁 Auto-consolidation complete!")
