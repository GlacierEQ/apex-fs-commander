#!/usr/bin/env python3
"""
APEX HTTP API SERVER
Self-hosted alternative to Smithery
Run on your Linux server, call from anywhere
Case: 1FDV-23-0001009
"""

import os
import sys
import json
import asyncio
import hmac
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Dict, Any
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Load environment before importing services; they read token env vars at import time.
from dotenv import load_dotenv
load_dotenv('.env.smithery')

# Setup
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

REPO_ROOT = Path(__file__).resolve().parent
ALLOWED_FILE_ROOT = Path(os.getenv("APEX_FILE_ROOT", REPO_ROOT / "exports")).resolve()

# Import and initialize services.
sys.path.append(os.path.dirname(__file__))
# Ensure parent directory is searchable for services module imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from services.apex_onedrive_persistent import OneDriveManager
from services.apex_memory_intelligence import MemoryIntelligence
from services.apex_github_automation import GitHubAutomation
from services.apex_clickup_connector import ClickUpConnector
from services.apex_qdrant_connector import QdrantConnector
from services.apex_motherduck_connector import MotherduckConnector
from services.apex_dropbox_connector import dropbox_connector
from services.apex_gdrive_connector import gdrive_connector
from services.apex_terabox_connector import terabox_connector
from services.apex_whisperx_bridge import WhisperXBridge

onedrive = OneDriveManager()
memory = MemoryIntelligence()
github = GitHubAutomation()
clickup = ClickUpConnector()
qdrant = QdrantConnector()
motherduck = MotherduckConnector()
whisperx = WhisperXBridge()

# Active Case Configuration
CASE_NUMBER = "1FDV-23-0001009"

def get_mcp_status():
    """Check status of all 22 MCP engines."""
    # This is a simplified check for the demo
    config_path = Path(__file__).resolve().parent.parent / "config" / "mcp_omni_config.json"
    if not config_path.exists():
        return {"error": "Config missing"}
    
    with open(config_path) as f:
        config = json.load(f)
    
    servers = config.get("mcpServers", {})
    status = {}
    for name in servers:
        # Mock status for now, in production we'd ping them
        status[name] = "ONLINE"
    return status

# Simple API key auth.
VALID_API_KEYS = {
    key.strip() for key in (
        os.getenv('SMITHERY_API_KEY'),
        os.getenv('APEX_HTTP_API_KEY'),
    )
    if key and key.strip()
}

def run_async(coro):
    """Run a service coroutine from Flask and always close its loop."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        asyncio.set_event_loop(None)
        loop.close()

def resolve_allowed_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ALLOWED_FILE_ROOT / path
    resolved = path.resolve()
    if resolved != ALLOWED_FILE_ROOT and ALLOWED_FILE_ROOT not in resolved.parents:
        raise ValueError(f"path must stay inside {ALLOWED_FILE_ROOT}")
    return resolved

def require_auth(f):
    """Decorator to require API key."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        scheme, _, api_key = auth_header.partition(' ')

        if (
            scheme.lower() != 'bearer'
            or not VALID_API_KEYS
            or not any(hmac.compare_digest(api_key, key) for key in VALID_API_KEYS)
        ):
            return jsonify({"error": "Unauthorized"}), 401

        return f(*args, **kwargs)

    return decorated

# ==============================================================================
# DIRECT iOS INGESTION (TAILSCALE BYPASS)
# ==============================================================================

@app.route('/ios/upload', methods=['POST'])
def handle_ios_upload():
    """
    Direct Webhook for iOS Apple Shortcuts.
    Accepts API key via Header OR Query Param for easier Shortcut compatibility.
    """
    try:
        # Check Auth (Header or Query Param)
        req_key = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not req_key:
            req_key = request.args.get('key', '')

        if not VALID_API_KEYS or not any(hmac.compare_digest(req_key, k) for k in VALID_API_KEYS):
            return jsonify({"error": "Unauthorized"}), 401

        if 'file' not in request.files:
            return jsonify({"error": "No file part attached in request"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Ensure target directory exists
        upload_dir = ALLOWED_FILE_ROOT / "ios_uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Save file securely
        safe_filename = file.filename.replace('/', '_').replace('\\', '_')
        target_path = upload_dir / safe_filename

        file.save(str(target_path))
        logging.info(f"📲 Received iOS Direct Push: {safe_filename} -> {target_path}")

        return jsonify({
            "status": "success",
            "message": "File received successfully by APEX HTTP Server.",
            "file": safe_filename,
            "path": str(target_path)
        }), 200

    except Exception as e:
        logging.error(f"Error handling iOS upload: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ==============================================================================
# HEALTH / STATUS
# ==============================================================================

@app.route('/', methods=['GET'])
def root():
    """
    Intelligent Root Route: Serves a state-of-the-art Web UI for browsers (browsed over Tailscale),
    and falls back to standard JSON for raw API clients.
    """
    accept_header = request.headers.get('Accept', '')
    if 'text/html' in accept_header:
        # Serve the premium APEX Forensic Hub
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>APEX Forensic Command Hub</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #05070a;
            --panel-bg: rgba(10, 15, 25, 0.7);
            --neon-blue: #00f2fe;
            --neon-purple: #c471ed;
            --neon-green: #39ff14;
            --text-main: #e2e8f0;
            --text-dim: #94a3b8;
            --accent-glow: 0 0 20px rgba(0, 242, 254, 0.2);
            --border: 1px solid rgba(0, 242, 254, 0.1);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-dark);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            overflow: hidden;
        }

        /* Sidebar Status Matrix */
        .sidebar {
            width: 320px;
            background: rgba(8, 10, 15, 0.95);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            flex-direction: column;
            padding: 2rem 1.5rem;
            height: 100vh;
            overflow-y: auto;
        }

        .logo-area { margin-bottom: 2.5rem; }
        .logo-text { font-size: 1.8rem; font-weight: 800; letter-spacing: -1px; background: linear-gradient(90deg, #fff, var(--neon-blue)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .case-tag { font-family: 'JetBrains Mono'; font-size: 0.7rem; color: var(--neon-purple); letter-spacing: 2px; }

        .status-matrix { flex: 1; }
        .status-item { 
            display: flex; align-items: center; justify-content: space-between; 
            padding: 0.75rem 1rem; background: rgba(255,255,255,0.02); 
            border-radius: 12px; margin-bottom: 0.6rem; border: 1px solid transparent;
            transition: all 0.3s; font-size: 0.85rem;
        }
        .status-item:hover { border-color: rgba(0,242,254,0.2); background: rgba(0,242,254,0.05); }
        .status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--neon-green); box-shadow: 0 0 8px var(--neon-green); margin-right: 10px; }
        .server-name { font-weight: 500; color: var(--text-dim); }
        .online-tag { font-family: 'JetBrains Mono'; font-size: 0.65rem; color: var(--neon-green); font-weight: bold; }

        /* Main Dashboard */
        .main-content {
            flex: 1;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            background: radial-gradient(circle at 50% 0%, rgba(0, 242, 254, 0.05), transparent);
            height: 100vh;
            overflow-y: auto;
        }

        .tabs { display: flex; gap: 1rem; margin-bottom: 2rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 1rem; }
        .tab { 
            padding: 0.6rem 1.5rem; border-radius: 100px; cursor: pointer; 
            font-weight: 600; font-size: 0.9rem; transition: 0.3s;
            color: var(--text-dim); border: 1px solid transparent;
        }
        .tab.active { background: rgba(0,242,254,0.1); color: var(--neon-blue); border-color: rgba(0,242,254,0.3); box-shadow: var(--accent-glow); }
        .tab:hover:not(.active) { color: #fff; background: rgba(255,255,255,0.05); }

        .glass-card {
            background: var(--panel-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 2rem;
            border: var(--border);
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            margin-bottom: 2rem;
        }

        /* WhisperX Forensic View */
        .audio-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
        .audio-card { 
            background: rgba(255,255,255,0.03); padding: 1.2rem; border-radius: 16px; 
            border: 1px solid rgba(255,255,255,0.05); cursor: pointer; transition: 0.3s;
        }
        .audio-card:hover { border-color: var(--neon-blue); transform: translateY(-3px); }
        .audio-icon { font-size: 1.5rem; margin-bottom: 0.5rem; display: block; }
        .audio-name { font-weight: 600; font-size: 0.95rem; margin-bottom: 0.2rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .audio-meta { font-size: 0.75rem; color: var(--text-dim); }

        .transcript-viewer { display: none; margin-top: 2rem; }
        .transcript-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
        .transcript-content { 
            max-height: 500px; overflow-y: auto; padding-right: 1rem; 
            font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; line-height: 1.6;
        }
        .segment { margin-bottom: 1.5rem; padding: 1rem; background: rgba(255,255,255,0.02); border-radius: 12px; }
        .speaker { font-weight: 800; color: var(--neon-purple); margin-bottom: 0.3rem; font-size: 0.75rem; text-transform: uppercase; }
        .timestamp { color: var(--text-dim); font-size: 0.7rem; margin-left: 10px; }

        .btn { 
            background: var(--neon-blue); color: var(--bg-dark); border: none; 
            padding: 0.8rem 1.8rem; border-radius: 12px; font-weight: 700; 
            cursor: pointer; transition: 0.3s; font-family: 'Outfit';
        }
        .btn:hover { box-shadow: 0 0 20px var(--neon-blue); transform: scale(1.02); }
        .btn-outline { background: transparent; color: var(--neon-blue); border: 1px solid var(--neon-blue); }
        .btn-outline:hover { background: rgba(0,242,254,0.1); }

        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(0,242,254,0.3); }

        /* Animation */
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fade { animation: fadeIn 0.5s ease forwards; }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo-area">
            <div class="case-tag">PROTOCOL: APEX OMNI-MESH</div>
            <div class="logo-text">APEX HUB</div>
        </div>

        <div class="status-matrix">
            <div style="font-size: 0.7rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 1rem;">Neural Status Matrix (22/22)</div>
            <div id="mcp-list">
                <!-- Status items will be injected here -->
                <div class="status-item"><div style="display:flex;align-items:center;"><div class="status-dot"></div><span class="server-name">Loading Matrix...</span></div></div>
            </div>
        </div>

        <div style="margin-top: 2rem; padding: 1rem; background: rgba(196, 113, 237, 0.05); border: 1px solid rgba(196, 113, 237, 0.2); border-radius: 16px;">
            <div style="font-size: 0.7rem; color: var(--neon-purple); font-weight: bold; margin-bottom: 0.5rem;">CASE 1FDV-23-0001009</div>
            <div style="font-size: 0.8rem; line-height: 1.4;">Target: All Island Hawaii<br>Status: RICO Exposure Confirmed</div>
        </div>
    </div>

    <div class="main-content">
        <div class="tabs">
            <div class="tab active" onclick="showTab('forensics')">Audio Forensics</div>
            <div class="tab" onclick="showTab('ingress')">Direct Ingress</div>
            <div class="tab" onclick="showTab('mastermind')">Mastermind AI</div>
        </div>

        <!-- Forensics Tab -->
        <div id="tab-forensics" class="animate-fade">
            <div class="glass-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 1.5rem;">
                    <h2>WHISPERX FORENSIC ENGINE</h2>
                    <button class="btn btn-outline" style="padding: 0.5rem 1rem; font-size: 0.8rem;" onclick="loadTranscripts()">Refresh List</button>
                </div>
                
                <div class="audio-list" id="audio-list">
                    <!-- Audio transcripts injected here -->
                </div>

                <div class="transcript-viewer" id="transcript-viewer">
                    <div class="transcript-header">
                        <h3 id="viewing-filename" style="font-size: 1.1rem; color: var(--neon-blue);">No Transcript Selected</h3>
                        <button class="btn" style="padding: 0.4rem 1rem; font-size: 0.8rem;" onclick="closeViewer()">Close</button>
                    </div>
                    <div class="transcript-content" id="transcript-content">
                        <!-- Segments injected here -->
                    </div>
                </div>
            </div>
        </div>

        <!-- Ingress Tab (Existing functionality) -->
        <div id="tab-ingress" style="display:none;" class="animate-fade">
            <div class="glass-card">
                <h2>SECURE INGRESS GATEWAY</h2>
                <p style="color: var(--text-dim); margin-bottom: 1.5rem; font-size: 0.9rem;">Upload evidence directly into the forensic vault from any device on the Tailscale network.</p>
                <div style="border: 2px dashed rgba(0,242,254,0.2); padding: 4rem 2rem; text-align: center; border-radius: 20px; cursor: pointer;" onclick="document.getElementById('file-input').click()">
                    <span style="font-size: 3rem; display: block; margin-bottom: 1rem;">📤</span>
                    <span style="font-weight: 600; color: var(--neon-blue);">Drop evidence here or click to browse</span>
                    <input type="file" id="file-input" style="display:none;" multiple onchange="handleUploads(this.files)">
                </div>
                <div id="upload-status" style="margin-top: 1rem; font-size: 0.85rem;"></div>
            </div>
        </div>

        <!-- Mastermind Tab -->
        <div id="tab-mastermind" style="display:none;" class="animate-fade">
            <div class="glass-card">
                <h2>NEURAL INTELLIGENCE DOSSIER</h2>
                <div id="dossier-content" style="background: rgba(0,0,0,0.4); padding: 2rem; border-radius: 20px; font-family: 'JetBrains Mono'; font-size: 0.9rem; line-height: 1.6; white-space: pre-wrap; max-height: 600px; overflow-y: auto; border: 1px solid rgba(255,255,255,0.05);">
                    Loading Neural Dossier...
                </div>
            </div>
        </div>

    </div>

    <script>
        const API_KEY = localStorage.getItem('apexUploadKey') || '';
        
        async function apiCall(endpoint, method = 'GET', body = null) {
            const options = {
                method,
                headers: {
                    'Authorization': `Bearer ${API_KEY}`,
                    'Content-Type': 'application/json'
                }
            };
            if (body) options.body = JSON.stringify(body);
            const res = await fetch(endpoint, options);
            if (res.status === 401) {
                const key = prompt('Enter APEX API Key:');
                if (key) { localStorage.setItem('apexUploadKey', key); location.reload(); }
                return null;
            }
            return res.json();
        }

        async function updateStatus() {
            const status = await apiCall('/system/status');
            if (!status) return;
            const container = document.getElementById('mcp-list');
            container.innerHTML = '';
            Object.entries(status).forEach(([name, state]) => {
                const item = document.createElement('div');
                item.className = 'status-item';
                item.innerHTML = `
                    <div style="display:flex;align-items:center;">
                        <div class="status-dot"></div>
                        <span class="server-name">${name.replace('apex-','')}</span>
                    </div>
                    <span class="online-tag">ONLINE</span>
                `;
                container.appendChild(item);
            });
        }

        async function loadTranscripts() {
            const data = await apiCall('/whisperx/list');
            if (!data) return;
            const list = document.getElementById('audio-list');
            list.innerHTML = '';
            
            if (data.transcripts.length === 0) {
                list.innerHTML = '<div style="color: var(--text-dim); font-size: 0.9rem;">No transcripts found in vault.</div>';
                return;
            }

            data.transcripts.forEach(t => {
                const card = document.createElement('div');
                card.className = 'audio-card';
                card.onclick = () => viewTranscript(t);
                card.innerHTML = `
                    <span class="audio-icon">📄</span>
                    <div class="audio-name">${t.name}</div>
                    <div class="audio-meta">${(t.size/1024).toFixed(1)} KB • ${new Date(t.modified).toLocaleDateString()}</div>
                `;
                list.appendChild(card);
            });
        }

        async function viewTranscript(t) {
            document.getElementById('audio-list').style.display = 'none';
            document.getElementById('transcript-viewer').style.display = 'block';
            document.getElementById('viewing-filename').textContent = t.name;
            
            document.getElementById('transcript-content').innerHTML = '<div style="color:var(--neon-blue)">Decrypting forensic transcript segments...</div>';
            
            const data = await apiCall('/whisperx/read', 'POST', { path: t.path });
            if (!data) return;

            const segments = data.segments || [];
            if (segments.length === 0) {
                document.getElementById('transcript-content').innerHTML = '<div style="color:var(--text-dim)">No speech segments detected in this file.</div>';
                return;
            }

            document.getElementById('transcript-content').innerHTML = segments.map(s => `
                <div class="segment">
                    <div class="speaker">${s.speaker || 'UNKNOWN'} <span class="timestamp">${formatTime(s.start)}</span></div>
                    <div class="text">${s.text}</div>
                </div>
            `).join('');
        }

        function formatTime(seconds) {
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = Math.floor(seconds % 60);
            return [h, m, s].map(v => v.toString().padStart(2, '0')).join(':');
        }

        function closeViewer() {
            document.getElementById('audio-list').style.display = 'grid';
            document.getElementById('transcript-viewer').style.display = 'none';
        }

        async function loadDossier() {
            const data = await apiCall('/system/dossier');
            if (data) {
                document.getElementById('dossier-content').textContent = data.content;
            }
        }

        function showTab(id) {
            ['forensics', 'ingress', 'mastermind'].forEach(t => {
                document.getElementById(`tab-${t}`).style.display = t === id ? 'block' : 'none';
            });
            document.querySelectorAll('.tab').forEach(t => {
                t.classList.toggle('active', t.textContent.toLowerCase().includes(id));
            });
            if (id === 'mastermind') loadDossier();
        }

        // Initial Load
        updateStatus();
        loadTranscripts();
        setInterval(updateStatus, 10000);
    </script>
</body>
</html>
"""

# ===== WHISPERX ENDPOINTS =====

@app.route('/whisperx/transcribe', methods=['POST'])
@require_auth
def whisperx_transcribe():
    """Trigger WhisperX transcription."""
    data = request.get_json() or {}
    file_path = data.get('file_path')
    remote = data.get('remote', False)
    
    if not file_path:
        return jsonify({"error": "file_path is required"}), 400
    
    result = whisperx.transcribe(file_path, remote=remote)
    return jsonify(result)

@app.route('/whisperx/upload', methods=['POST'])
@require_auth
def whisperx_upload():
    """Upload audio for WhisperX."""
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    
    file = request.files['file']
    upload_dir = Path.home() / "apex-fs-commander" / "ingest" / "audio"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    target_path = upload_dir / file.filename
    file.save(str(target_path))
    
    return jsonify({
        "status": "success",
        "path": str(target_path)
    })

@app.route('/whisperx/list', methods=['GET'])
@require_auth
def whisperx_list():
    """List available transcripts."""
    transcript_dir = Path.home() / "apex-fs-commander" / "transcripts"
    if not transcript_dir.exists():
        return jsonify({"transcripts": []})
    
    transcripts = []
    for p in transcript_dir.glob("*.json"):
        transcripts.append({
            "name": p.name,
            "path": str(p),
            "size": p.stat().st_size,
            "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat()
        })
    return jsonify({"transcripts": sorted(transcripts, key=lambda x: x['modified'], reverse=True)})

@app.route('/whisperx/read', methods=['POST'])
@require_auth
def whisperx_read():
    """Read a transcript file."""
    data = request.get_json() or {}
    path = data.get('path')
    if not path:
        return jsonify({"error": "path is required"}), 400
    
    p = Path(path)
    # Security check: must be in transcripts dir
    if "transcripts" not in str(p):
        return jsonify({"error": "Forbidden"}), 403
    
    if not p.exists():
        return jsonify({"error": "Not found"}), 404
    
    return jsonify(json.loads(p.read_text()))

# ===== SYSTEM ENDPOINTS =====

@app.route('/system/status', methods=['GET'])
@require_auth
def system_status():
    """Get status of all MCP engines."""
    return jsonify(get_mcp_status())

@app.route('/system/dossier', methods=['GET'])
@require_auth
def system_dossier():
    """Get the target dossier content."""
    dossier_path = Path(__file__).resolve().parent.parent / "legal_documents" / "intel" / "TARGET_DOSSIER.md"
    if not dossier_path.exists():
        return jsonify({"content": "Dossier missing."})
    
    return jsonify({"content": dossier_path.read_text()})

# ===== ONEDRIVE ENDPOINTS =====

@app.route('/onedrive/list', methods=['GET', 'POST'])
@require_auth
def onedrive_list():
    """List OneDrive files."""
    data = request.get_json() or {}
    folder = data.get('folder', 'root')

    result = run_async(onedrive.list_files(folder))

    return jsonify(result)

@app.route('/onedrive/upload', methods=['POST'])
@require_auth
def onedrive_upload():
    """Upload file to OneDrive."""
    data = request.get_json() or {}
    if 'local_path' not in data or 'onedrive_path' not in data:
        return jsonify({"error": "local_path and onedrive_path are required"}), 400
    try:
        local_path = resolve_allowed_path(data['local_path'])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    result = run_async(
        onedrive.upload_file(
            str(local_path),
            data['onedrive_path']
        )
    )

    return jsonify(result)

@app.route('/onedrive/download', methods=['POST'])
@require_auth
def onedrive_download():
    """Download file from OneDrive."""
    data = request.get_json() or {}
    if 'onedrive_path' not in data or 'local_path' not in data:
        return jsonify({"error": "onedrive_path and local_path are required"}), 400
    try:
        local_path = resolve_allowed_path(data['local_path'])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    result = run_async(
        onedrive.download_file(
            data['onedrive_path'],
            str(local_path)
        )
    )

    return jsonify(result)

@app.route('/onedrive/search', methods=['POST'])
@require_auth
def onedrive_search():
    """Search OneDrive files."""
    data = request.get_json() or {}
    if 'query' not in data:
        return jsonify({"error": "query is required"}), 400

    result = run_async(
        onedrive.search_files(data['query'])
    )

    return jsonify(result)

# ===== MEMORY ENDPOINTS =====

@app.route('/memory/store', methods=['POST'])
@require_auth
def memory_store():
    """Store case memory."""
    data = request.get_json() or {}
    if 'content' not in data:
        return jsonify({"error": "content is required"}), 400

    result = run_async(
        memory.store_memory(
            data['content'],
            data.get('tags'),
            data.get('metadata')
        )
    )

    return jsonify(result)

@app.route('/memory/search', methods=['POST'])
@require_auth
def memory_search():
    """Search case memories."""
    data = request.get_json() or {}
    if 'query' not in data:
        return jsonify({"error": "query is required"}), 400

    result = run_async(
        memory.search_memories(
            data['query'],
            data.get('tags'),
            data.get('limit', 10)
        )
    )

    return jsonify(result)

@app.route('/memory/judicial-pattern', methods=['POST'])
@require_auth
def memory_judicial():
    """Store judicial misconduct pattern."""
    data = request.get_json() or {}
    required = {'judge', 'pattern', 'observations'}
    if not required.issubset(data):
        return jsonify({"error": "judge, pattern, and observations are required"}), 400

    result = run_async(
        memory.store_judicial_pattern(
            data['judge'],
            data['pattern'],
            data['observations']
        )
    )

    return jsonify(result)

@app.route('/memory/federal-trigger', methods=['POST'])
@require_auth
def memory_federal():
    """Store federal escalation trigger."""
    data = request.get_json() or {}
    required = {'trigger_type', 'description', 'evidence'}
    if not required.issubset(data):
        return jsonify({"error": "trigger_type, description, and evidence are required"}), 400

    result = run_async(
        memory.store_federal_trigger(
            data['trigger_type'],
            data['description'],
            data['evidence']
        )
    )

    return jsonify(result)

# ===== GITHUB ENDPOINTS =====

@app.route('/github/evidence/create', methods=['POST'])
@require_auth
def github_evidence_create():
    """Create evidence issue."""
    data = request.get_json() or {}
    if 'title' not in data or 'body' not in data:
        return jsonify({"error": "title and body are required"}), 400

    result = run_async(
        github.create_evidence_issue(
            data['title'],
            data['body'],
            data.get('labels')
        )
    )

    return jsonify(result)

@app.route('/github/evidence/list', methods=['GET'])
@require_auth
def github_evidence_list():
    """List evidence issues."""
    state = request.args.get('state', 'open')

    result = run_async(
        github.list_evidence_issues(state)
    )

    return jsonify(result)

@app.route('/github/file/upload', methods=['POST'])
@require_auth
def github_file_upload():
    """Upload file to FILEBOSS."""
    data = request.get_json() or {}
    if 'file_path' not in data or 'content' not in data:
        return jsonify({"error": "file_path and content are required"}), 400

    result = run_async(
        github.upload_evidence_file(
            data['file_path'],
            data['content'],
            data.get('commit_msg')
        )
    )

    return jsonify(result)

# ===== CLICKUP ENDPOINTS =====

@app.route('/clickup/task/create', methods=['POST'])
@require_auth
def clickup_task_create():
    """Create a task card inside ClickUp."""
    data = request.get_json() or {}
    required = {'list_id', 'title', 'description'}
    if not required.issubset(data):
        return jsonify({"error": "list_id, title, and description are required"}), 400

    result = run_async(
        clickup.create_case_task(
            data['list_id'],
            data['title'],
            data['description'],
            data.get('due_date'),
            data.get('priority', 3),
            data.get('tags')
        )
    )
    return jsonify(result)

@app.route('/clickup/springboard/upload', methods=['POST'])
@require_auth
def clickup_springboard_upload():
    """
    Springboard MCP: Creates a task and attaches a local file.
    Native ClickUp automations will then push this file to the cloud.
    """
    data = request.get_json() or {}
    required = {'list_id', 'title', 'description', 'local_path'}
    if not required.issubset(data):
        return jsonify({"error": "list_id, title, description, and local_path are required"}), 400

    try:
        local_path = resolve_allowed_path(data['local_path'])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # 1. Create the task
    task_res = run_async(
        clickup.create_case_task(
            data['list_id'],
            data['title'],
            data['description']
        )
    )

    if task_res.get("status") not in ["success", "simulated"]:
        return jsonify({"error": "Failed to create task", "details": task_res}), 500

    task_id = task_res.get("task_id")
    if not task_id:
        return jsonify({"error": "Task created but no ID returned", "details": task_res}), 500

    # 2. Attach the file (The Springboard Action)
    attach_res = run_async(
        clickup.upload_task_attachment(task_id, str(local_path))
    )

    return jsonify({
        "task": task_res,
        "attachment": attach_res
    })

# ===== QDRANT ENDPOINTS =====

@app.route('/qdrant/collection/create', methods=['POST'])
@require_auth
def qdrant_collection_create():
    """Create a new Qdrant vector collection."""
    data = request.get_json() or {}
    collection_name = data.get('collection_name')
    if not collection_name:
        return jsonify({"error": "collection_name is required"}), 400

    result = run_async(
        qdrant.create_collection(
            collection_name,
            data.get('vector_size', 1536)
        )
    )
    return jsonify(result)

@app.route('/qdrant/points/upsert', methods=['POST'])
@require_auth
def qdrant_points_upsert():
    """Upsert vector embeddings into Qdrant."""
    data = request.get_json() or {}
    required = {'collection_name', 'point_id', 'vector', 'payload'}
    if not required.issubset(data):
        return jsonify({"error": "collection_name, point_id, vector, and payload are required"}), 400

    result = run_async(
        qdrant.upsert_vector(
            data['collection_name'],
            data['point_id'],
            data['vector'],
            data['payload']
        )
    )
    return jsonify(result)

@app.route('/qdrant/points/search', methods=['POST'])
@require_auth
def qdrant_points_search():
    """Search vector embeddings in Qdrant."""
    data = request.get_json() or {}
    required = {'collection_name', 'vector'}
    if not required.issubset(data):
        return jsonify({"error": "collection_name and vector are required"}), 400

    result = run_async(
        qdrant.search_vectors(
            data['collection_name'],
            data['vector'],
            data.get('limit', 5)
        )
    )
    return jsonify(result)

# ===== MOTHERDUCK ENDPOINTS =====

@app.route('/motherduck/query', methods=['POST'])
@require_auth
def motherduck_query():
    """Execute analytical SQL query using DuckDB/Motherduck."""
    data = request.get_json() or {}
    query = data.get('query')
    if not query:
        return jsonify({"error": "query is required"}), 400

    result = motherduck.execute_analytical_query(query)
    return jsonify(result)

# ===== CLOUD STORAGE ENDPOINTS =====

@app.route('/cloud/dropbox/status', methods=['GET'])
@require_auth
def dropbox_status():
    return jsonify(dropbox_connector.get_status())

@app.route('/cloud/gdrive/status', methods=['GET'])
@require_auth
def gdrive_status():
    return jsonify(gdrive_connector.get_status())

@app.route('/cloud/terabox/status', methods=['GET'])
@require_auth
def terabox_status():
    return jsonify(terabox_connector.get_status())

@app.route('/cloud/onedrive/status', methods=['GET'])
@require_auth
def onedrive_status_check():
    status = {
        "service": "OneDrive",
        "configured": bool(os.getenv("ONEDRIVE_CLIENT_ID")),
        "authenticated": bool(os.getenv("ONEDRIVE_REFRESH_TOKEN"))
    }
    return jsonify(status)

# ===== STATUS & UTILITIES =====

@app.route('/status', methods=['GET'])
@require_auth
def status():
    """Get comprehensive status."""
    return jsonify({
        "server": "online",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "onedrive": "active",
            "memory": "active",
            "github": "active",
            "clickup": "active",
            "qdrant": "active",
            "motherduck": "active",
            "dropbox": "active" if dropbox_connector.get_status()["configured"] else "inactive",
            "gdrive": "active" if gdrive_connector.get_status()["configured"] else "inactive",
            "terabox": "active" if terabox_connector.get_status()["configured"] else "inactive"
        },
        "case": "1FDV-23-0001009",
        "endpoints": [
            "/onedrive/list",
            "/onedrive/upload",
            "/onedrive/search",
            "/memory/store",
            "/memory/search",
            "/memory/judicial-pattern",
            "/memory/federal-trigger",
            "/github/evidence/create",
            "/github/evidence/list",
            "/github/file/upload",
            "/clickup/task/create",
            "/clickup/springboard/upload",
            "/qdrant/collection/create",
            "/qdrant/points/upsert",
            "/qdrant/points/search",
            "/motherduck/query",
            "/cloud/dropbox/status",
            "/cloud/gdrive/status",
            "/cloud/terabox/status",
            "/cloud/onedrive/status",
            "/ios/upload"
        ]
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("\n" + "="*60)
    print("  APEX HTTP API SERVER")
    print("  Case: 1FDV-23-0001009")
    print("="*60)
    print(f"\n  🚀 Server starting on http://0.0.0.0:{port}")
    auth_state = "configured" if VALID_API_KEYS else "missing"
    print(f"  Auth: {auth_state} (set SMITHERY_API_KEY or APEX_HTTP_API_KEY)")
    print("\n  Endpoints:")
    print("    GET  /           - Health check")
    print("    GET  /status     - Full status")
    print("    POST /onedrive/* - OneDrive operations")
    print("    POST /memory/*   - Memory operations")
    print("    POST /github/*   - GitHub operations")
    print("\n" + "="*60 + "\n")

    # Run server
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # Set True for development
    )
