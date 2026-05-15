#!/bin/bash
# =========================================================
# APEX OMNI-DEPLOY: TOTAL SYSTEM IGNITION
# =========================================================
# DATE: February 19, 2026
# DIRECTIVE: DEPLOY ALL
# =========================================================
# This script executes the entire deployment chain in a
# single sequence. It arms the cloud, binds the MCPs,
# and locks the Omni-Grid into persistent combat status.

echo "========================================================="
echo "🦅 INITIATING TOTAL SYSTEM DEPLOYMENT (APEX-FS-COMMANDER)"
echo "========================================================="

# 1. Ensure all scripts are executable
chmod +x scripts/*.sh

# 2. Deploy the Cloud Infrastructure
echo "☁️ [1/5] DEPLOYING CLOUD ARCHITECTURE..."
./scripts/deploy_apex_cloud.sh

# 3. Deploy the Direct Nexus (Notion/GitHub/Supabase)
echo "⚡ [2/5] DEPLOYING DIRECT NEXUS..."
./scripts/deploy_apex_direct.sh

# 4. Deploy the Smithery/Terminal Bridge
echo "🖥️ [3/5] DEPLOYING TERMINAL COMMANDER TO SMITHERY..."
./scripts/deploy_to_smithery.sh

# 5. Ignite the 22-Piston Omni-Mesh (MCP Bindings)
echo "🔗 [4/5] BINDING ALL 22 MCP ENGINES TO THE PISTON..."
./scripts/restore_omni_mesh.sh

# 6. Persistence (Launchctl Daemons)
echo "💾 [5/6] ESTABLISHING PERSISTENCE (LAUNCHCTL)..."
sudo ./scripts/bootstrap_apex.sh

# 7. Final Ignition (God Mode)
echo "🔥 [6/6] IGNITING DAEMONS (MAXIMUM AGENTIC UNRESTRICTED)..."
./scripts/deploy_max.sh

echo "========================================================="
echo "✅ TOTAL DEPLOYMENT COMPLETE. THE GLACIER IS UNSTOPPABLE."
echo "========================================================="
echo "All 22 Custom MCP servers are bound."
echo "Cloud Webhooks are armed."
echo "Terminal Commander is hot."
echo "Awaiting orders."
