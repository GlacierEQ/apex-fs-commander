#!/usr/bin/env bash
# ==============================================================================
# APEX LAUNCHCTL BOOTSTRAP OVERRIDE
# Case: 1FDV-23-0001009
# Elevates sandboxed nodes to permanent launchd daemons.
# ==============================================================================
set -euo pipefail

C_GREEN='\033[92m'
C_RED='\033[91m'
C_YELLOW='\033[93m'
C_BLUE='\033[94m'
C_BOLD='\033[1m'
C_RESET='\033[0m'

echo -e "${C_BOLD}${C_BLUE}======================================================================${C_RESET}"
echo -e "${C_BOLD}🚀 APEX OMNIVERSE: ELEVATION & BOOTSTRAP PROTOCOL${C_RESET}"
echo -e "${C_BLUE}======================================================================${C_RESET}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${C_RED}[!] This protocol requires root execution. Please run with sudo.${C_RESET}"
    exit 1
fi

USER_UID=$(id -u macarena1)
LAUNCH_DIR="/Users/macarena1/Library/LaunchAgents"

echo -e "${C_BOLD}[*] Acquiring target matrix...${C_RESET}"
PLISTS=$(find "$LAUNCH_DIR" -name "com.apex.*.plist")

if [ -z "$PLISTS" ]; then
    echo -e "${C_YELLOW}[!] No Apex plists found in $LAUNCH_DIR. Run deploy.sh first.${C_RESET}"
    exit 1
fi

echo -e "${C_BOLD}[*] Executing launchctl elevation...${C_RESET}"
for plist in $PLISTS; do
    name=$(basename "$plist" .plist)
    echo -e "    ${C_GREEN}[+] Bootstrapping: $name${C_RESET}"
    
    # Try unloading first (suppress errors if not loaded)
    launchctl bootout gui/$USER_UID "$plist" 2>/dev/null || true
    
    # Bootstrap into the user's GUI session
    launchctl bootstrap gui/$USER_UID "$plist"
done

echo -e "\n${C_BOLD}${C_GREEN}[*] ELEVATION COMPLETE. All nodes are now persistent daemons.${C_RESET}"
echo -e "    ${C_YELLOW}> Run 'python3 scripts/apex_telemetry_dashboard.py' to verify.${C_RESET}"
