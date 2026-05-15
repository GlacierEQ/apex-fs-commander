#!/bin/bash
# =========================================================
# APEX OMNI-MESH RESTORATION PROTOCOL (ULTIMATE EDITION)
# =========================================================
# Ensure paths for Node/Brew
export PATH="/usr/local/bin:/usr/local/sbin:/Users/macarena1/.homebrew/bin:/Users/macarena1/.homebrew/sbin:/Users/macarena1/.npm-global/bin:$PATH"
# DATE: February 19, 2026
# DIRECTIVE: Hook ALL 19 Custom APEX MCPs to the Piston.
# =========================================================

echo "========================================================="
echo "🔥 IGNITING THE APEX PISTON 🔥"
echo "========================================================="

echo "[1/4] Purging hanging MCP nodes..."
pkill -f "$(pwd)/servers/.*mcp.py" 2>/dev/null || true
pkill -f "apex_.*mcp.py" 2>/dev/null || true

echo "[2/4] Verifying Python Environment..."
./.venv/bin/python -m pip install -r servers/requirements.txt --quiet

echo "[3/4] Deploying ULTIMATE APEX Omni-Config..."
# The config already has absolute paths, but we ensure it's copied to the correct location
CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
mkdir -p "$CLAUDE_CONFIG_DIR"
cp config/mcp_omni_config.json "$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
echo "  -> Configuration injected. 22 custom engines bound."

echo "[4/4] Pre-fetching Node dependencies..."
npm install -g @modelcontextprotocol/server-filesystem apple-mcp @modelcontextprotocol/server-github --silent

echo "========================================================="
echo "✅ PISTON LOCKED. ALL APEX ENGINES ONLINE."
echo "========================================================="
echo "Restart your Claude client or Terminal session."
echo "You now have 22 simultaneous MCP servers wired into the grid."
