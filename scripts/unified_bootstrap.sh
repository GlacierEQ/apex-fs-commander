#!/usr/bin/env bash
# ==============================================================================
# APEX UNIFIED BOOTSTRAP PROTOCOL
# Case: 1FDV-23-0001009
# Status: MAXIMIZING | Aspen Grove Federated
# ==============================================================================
set -euo pipefail

C_GREEN='\033[92m'
C_RED='\033[91m'
C_YELLOW='\033[93m'
C_BLUE='\033[94m'
C_BOLD='\033[1m'
C_RESET='\033[0m'

echo -e "${C_BOLD}${C_BLUE}██████╗ ██╗      ██████╗  ██████╗██╗███████╗██████╗ ${C_RESET}"
echo -e "${C_BOLD}${C_BLUE}██╔════╝ ██║     ██╔══██╗██╔════╝██║██╔════╝██╔══██╗${C_RESET}"
echo -e "${C_BOLD}${C_BLUE}██║  ███╗██║     ███████║██║     ██║█████╗  ██████╔╝${C_RESET}"
echo -e "${C_BOLD}${C_BLUE}██║   ██║██║     ██╔══██║██║     ██║██╔══╝  ██╔══██╗${C_RESET}"
echo -e "${C_BOLD}${C_BLUE}╚██████╔╝███████╗██║  ██║╚██████╗██║███████╗██║  ██║${C_RESET}"
echo -e "${C_BOLD}${C_BLUE} ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝╚══════╝╚═╝  ╚═╝${C_RESET}"
echo -e "${C_BLUE}----------------------------------------------------${C_RESET}"
echo -e "${C_BOLD}🚀 INITIATING UNIFIED APEX ACTIVATION...${C_RESET}"

# 1. OPTIMIZE RESOURCES
echo -e "\n${C_BOLD}[1/5] Optimizing System Resources...${C_RESET}"
if [ -f "scripts/apex_optimizer.py" ]; then
    python3 scripts/apex_optimizer.py --maximize
else
    echo -e "    ${C_YELLOW}[!] Optimizer script not found. Skipping.${C_RESET}"
fi

# 2. VERIFY LEGAL WEAPONS
echo -e "\n${C_BOLD}[2/5] Verifying Legal Weapons...${C_RESET}"
FILES=(
    "legal_documents/federal/RICO_COMPLAINT_ALL_ISLAND.md"
    "legal_documents/federal/CATACLYSM_EXECUTION_KIT.md"
    "legal_documents/intel/TARGET_DOSSIER.md"
    "legal_documents/fusion/MASTER_FUSION_INDEX.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "    ${C_GREEN}[+] $file: ARMED${C_RESET}"
    else
        echo -e "    ${C_RED}[!] $file: MISSING${C_RESET}"
    fi
done

# 3. ASPEN GROVE FEDERATION
echo -e "\n${C_BOLD}[3/5] Federating Aspen Grove Constellation...${C_RESET}"
if [ -f "orchestration/aspen_grove_federator.py" ]; then
    python3 orchestration/aspen_grove_federator.py
else
    echo -e "    ${C_RED}[!] Aspen Grove Federator not found.${C_RESET}"
fi

# 4. SERVICE ELEVATION (macOS launchctl)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "\n${C_BOLD}[4/5] Elevating Background Services (macOS)...${C_RESET}"
    USER_UID=$(id -u)
    LAUNCH_DIR="$HOME/Library/LaunchAgents"
    PLISTS=$(find "$LAUNCH_DIR" -name "com.apex.*.plist")

    if [ -n "$PLISTS" ]; then
        for plist in $PLISTS; do
            name=$(basename "$plist" .plist)
            echo -e "    ${C_GREEN}[+] Bootstrapping: $name${C_RESET}"
            launchctl bootout gui/"$USER_UID" "$plist" 2>/dev/null || true
            launchctl bootstrap gui/"$USER_UID" "$plist"
        done
    else
        echo -e "    ${C_YELLOW}[!] No Apex plists found in $LAUNCH_DIR.${C_RESET}"
    fi
else
    echo -e "\n${C_BOLD}[4/5] Service Elevation: SKIPPED (Non-macOS)${C_RESET}"
fi

# 5. FINAL NEXUS STATUS
echo -e "\n${C_BOLD}[5/5] Finalizing Nexus Coordination...${C_RESET}"
python3 apex_nexus_coordinator.py status

echo -e "\n${C_BOLD}${C_GREEN}====================================================${C_RESET}"
echo -e "${C_BOLD}${C_GREEN} ✅ UNIFIED BOOTSTRAP COMPLETE. SYSTEM MAXIMIZED.${C_RESET}"
echo -e "${C_BOLD}${C_GREEN}====================================================${C_RESET}"
