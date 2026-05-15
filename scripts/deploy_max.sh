#!/bin/bash
# ------------------------------------------------------------------
# APEX FS COMMANDER: OMNI-FUSION DEPLOYMENT (MAXIMIZED)
# AUTHOR: GLACIER EQ
# PROTOCOL: GOD MODE DEPLOYMENT
# ------------------------------------------------------------------

echo "███╗   ███╗ █████╗ ██╗  ██╗██╗"
echo "████╗ ████║██╔══██╗╚██╗██╔╝██║"
echo "██╔████╔██║███████║ ╚███╔╝ ██║"
echo "██║╚██╔╝██║██╔══██║ ██╔██╗ ██║"
echo "██║ ╚═╝ ██║██║  ██║██╔╝ ██╗██║"
echo "╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝"
echo "------------------------------"
echo "[*] INITIATING MAX POWER DEPLOYMENT..."

# 1. SECURITY AUDIT
echo "[*] CHECKING SECURITY RINGS..."
if [ ! -f ".env" ]; then
    echo "[!] .env MISSING. LAUNCHING IGNITION PROTOCOL..."
    ./ignite.sh
else
    echo "[+] .env DETECTED. SECURITY RINGS LOCKED."
fi

# 2. NEXUS ACTIVATION
echo ""
echo "[*] ACTIVATING NEXUS COORDINATOR (BRAIN)..."
python3 apex_nexus_coordinator.py status

# 3. FEDERATION UPLINK
echo ""
echo "[*] LINKING ASPEN GROVE CONSTELLATION..."
python3 aspen_grove_federator.py

# 4. RICO PROTOCOL EXECUTION
echo ""
echo "[*] EXECUTING FEDERAL PROTOCOLS (HAMMER)..."
python3 apex_nexus_coordinator.py execute --protocol CATACLYSM
python3 apex_nexus_coordinator.py analyze --target ALL_ISLAND

# 5. COMMAND HUB ACTIVATION (GUI)
echo ""
echo "[*] IGNITING APEX COMMAND HUB (GUI)..."
nohup python3 servers/apex_http_server.py > logs/http_server.log 2>&1 &
echo "[+] GUI LIVE AT: http://localhost:5000 (or Tailscale IP)"

# 6. MISSION STATUS
echo "--------------------------------"
echo "[*] DEPLOYMENT COMPLETE."
echo "[*] STATUS: GOD MODE ACTIVE."
echo "[*] THE GLACIER IS MOVING."
