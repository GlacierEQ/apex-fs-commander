#!/bin/bash

# MANUAL FIX FOR MCP CONFIG
# Use this if automated setup had path issues

set -e

echo "🔧 MANUAL MCP CONFIG FIX"
echo ""

# Get repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📂 Repo root: $REPO_ROOT"
echo "📂 Home directory: $HOME"
echo ""

# Update the config with correct repo path
echo "[1/3] Updating config template..."
cp "$REPO_ROOT/config/mcp_config.json" "/tmp/apex_mcp_config.json"
cat /tmp/apex_mcp_config.json
echo "✅ Config updated"
echo ""

# Find where Perplexity actually stores configs
echo "[2/3] Searching for Perplexity config location..."

POSSIBLE_LOCATIONS=(
    "$HOME/.config/perplexity/mcp_config.json"
    "$HOME/.config/Perplexity/mcp_config.json"
    "$HOME/.perplexity/mcp_config.json"
    "$HOME/Library/Application Support/Perplexity/mcp_config.json"
    "/root/.config/perplexity/mcp_config.json"
    "/root/.config/Perplexity/mcp_config.json"
)

FOUND_CONFIG=""
for loc in "${POSSIBLE_LOCATIONS[@]}"; do
    if [ -f "$loc" ]; then
        echo "   ✅ Found existing config: $loc"
        FOUND_CONFIG="$loc"
        break
    fi
done

if [ -z "$FOUND_CONFIG" ]; then
    echo "   ⚠️  No existing Perplexity config found"
    echo ""
    echo "   Possible locations tried:"
    for loc in "${POSSIBLE_LOCATIONS[@]}"; do
        echo "     - $loc"
    done
    echo ""
    echo "   🎯 MANUAL STEP REQUIRED:"
    echo ""
    echo "   1. Find where Perplexity stores MCP configs on your system"
    echo "   2. Copy the config manually:"
    echo ""
    echo "      cp /tmp/apex_mcp_config.json <perplexity-config-path>"
    echo ""
    echo "   OR add this to your existing Perplexity MCP config:"
    echo ""
    cat /tmp/apex_mcp_config.json
    echo ""
else
    echo ""
    echo "[3/3] Merging config into $FOUND_CONFIG..."
    cp "$FOUND_CONFIG" "${FOUND_CONFIG}.backup.$(date +%s)"
    
    python3 -c "
import json
with open('$FOUND_CONFIG') as f:
    target = json.load(f)
with open('/tmp/apex_mcp_config.json') as f:
    source = json.load(f)
if 'mcpServers' not in target:
    target['mcpServers'] = {}
for key, val in source['mcpServers'].items():
    target['mcpServers'][key] = val
with open('$FOUND_CONFIG', 'w') as f:
    json.dump(target, f, indent=2)
print('✅ Config merged successfully')
"
    echo ""
    echo "✅ DONE! Restart Perplexity now."
fi

echo ""
echo "📋 Your config is ready at: /tmp/apex_mcp_config.json"
echo ""
