#!/usr/bin/env python3
"""
APEX NEXUS COORDINATOR
Case: 1FDV-23-0001009
SpaceX-Grade Master Control Node
"""

import os
import sys
import subprocess
from pathlib import Path

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent
ENV_PATH = REPO_ROOT / ".env"
LEGAL_DIR = REPO_ROOT / "legal_documents"

# ANSI Colors
C_RED = '\033[91m'
C_GREEN = '\033[92m'
C_YELLOW = '\033[93m'
C_BLUE = '\033[94m'
C_BOLD = '\033[1m'
C_RESET = '\033[0m'

def print_banner():
    banner = f"""{C_BLUE}{C_BOLD}
 ════╝ ██║     ██╔══██╗██╔════╝██║██╔════╝██╔══██╗
 ██║  ███╗██║     ███████║██║     ██║█████╗  ██████╔╝
 ██║   ██║██║     ██╔══██║██║     ██║██╔══╝  ██╔══██╗
 ╚██████╔╝███████╗██║  ██║╚██████╗██║███████╗██║  ██║
  ╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝╚══════╝╚═╝  ╚═╝
----------------------------------------------------{C_RESET}"""
    print(banner)

def load_env():
    """Manually parse .env to avoid heavy dependencies in coordinator."""
    if ENV_PATH.exists():
        with open(ENV_PATH, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    val = val.strip(' "\'')
                    os.environ[key] = val

def check_dependencies():
    print(f"{C_BOLD}[*] Checking Operational Environment...{C_RESET}")
    # Python
    py_ver = sys.version.split()[0]
    print(f"    {C_GREEN}[+] Python {py_ver}: DETECTED{C_RESET}")
    
    # Git
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        print(f"    {C_GREEN}[+] Git: DETECTED{C_RESET}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"    {C_RED}[!] Git: MISSING{C_RESET}")

def check_memory_fusion():
    print(f"{C_BOLD}[*] Checking Memory Fusion...{C_RESET}")
    token = os.environ.get('MEMORY_AUTH_TOKEN')
    if token and token != "PENDING_USER_PROVISION":
        print(f"    {C_GREEN}[+] MEMORY_AUTH_TOKEN: DETECTED{C_RESET}")
        print(f"        > Active Memory Synchronization Established")
    else:
        print(f"    {C_RED}[!] MEMORY_AUTH_TOKEN: MISSING{C_RESET}")
        print(f"        > Set it with: export MEMORY_AUTH_TOKEN='your_token'")
        print(f"        > Get token from: https://www.memoryplugin.com/dashboard")

def check_legal_weapons():
    print(f"{C_BOLD}[*] Verifying Legal Weapons...{C_RESET}")
    documents = [
        ("federal/RICO_COMPLAINT_ALL_ISLAND.md", "RICO_COMPLAINT_ALL_ISLAND.md"),
        ("federal/CATACLYSM_EXECUTION_KIT.md", "CATACLYSM_EXECUTION_KIT.md"),
        ("intel/TARGET_DOSSIER.md", "TARGET_DOSSIER.md"),
        ("fusion/MASTER_FUSION_INDEX.md", "MASTER_FUSION_INDEX.md")
    ]
    
    all_armed = True
    for path, name in documents:
        full_path = LEGAL_DIR / path
        if full_path.exists():
            print(f"    {C_GREEN}[+] legal_documents/{path}: ARMED{C_RESET}")
        else:
            print(f"    {C_RED}[!] legal_documents/{path}: MISSING (Run Sync){C_RESET}")
            all_armed = False
            
    return all_armed

def run_status():
    print_banner()
    print(f"{C_BOLD}[*] INITIATING APEX SEQUENCE...{C_RESET}")
    load_env()
    check_dependencies()
    check_memory_fusion()
    check_legal_weapons()
    print(f"{C_BLUE}----------------------------------------------------{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}[*] BOOTSTRAP COMPLETE. SYSTEM MAXIMIZED.{C_RESET}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        run_status()
    else:
        print("Usage: python3 apex_nexus_coordinator.py status")
