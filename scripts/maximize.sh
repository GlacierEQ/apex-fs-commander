#!/usr/bin/env bash
# ==============================================================================
# APEX SYSTEM MAXIMIZATION PROTOCOL
# Case: 1FDV-23-0001009
# Deep cleaning, memory neutralization, and service elevation.
# ==============================================================================
set -euo pipefail

C_GREEN='\033[92m'
C_BOLD='\033[1m'
C_RESET='\033[0m'

echo -e "${C_BOLD}🚀 INITIATING FULL SYSTEM MAXIMIZATION...${C_RESET}\n"

# 1. OPTIMIZE RESOURCES
python3 scripts/apex_optimizer.py --maximize

# 2. ELEVATE SERVICES & UNIFY (requires sudo for launchctl)
echo -e "\n${C_BOLD}[*] Running Unified Activation Protocol...${C_RESET}"
if [ "$EUID" -ne 0 ]; then
    echo "    [i] Sudo may be required for launchctl elevation."
    sudo ./scripts/unified_bootstrap.sh
else
    ./scripts/unified_bootstrap.sh
fi

# 3. VERIFY STATUS
echo -e "\n${C_BOLD}[*] Finalizing System Readiness...${C_RESET}"
python3 apex_nexus_coordinator.py status

echo -e "\n${C_BOLD}${C_GREEN}[✅] SYSTEM MAXIMIZED. ALL NODES OPERATIONAL.${C_RESET}"
