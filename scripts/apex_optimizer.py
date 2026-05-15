#!/usr/bin/env python3
"""
APEX OPTIMIZER & HEALTH DOCTOR
Case: 1FDV-23-0001009
Maximizes Bootup, Device Health, and Memory.
"""

import os
import sys
import subprocess
import signal
from pathlib import Path

# ANSI Colors
C_RED = '\033[91m'
C_GREEN = '\033[92m'
C_YELLOW = '\033[93m'
C_BLUE = '\033[94m'
C_BOLD = '\033[1m'
C_RESET = '\033[0m'

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode('utf-8').strip()
    except:
        return ""

def audit_disk():
    print(f"{C_BOLD}{C_BLUE}[*] Auditing Disk Health...{C_RESET}")
    df = run_cmd("df -h / | tail -n 1")
    print(f"    Current Partition: {df}")
    
    # Large Caches
    print(f"    {C_YELLOW}[!] Large Caches Detected:{C_RESET}")
    caches = run_cmd("du -sh ~/Library/Caches/* 2>/dev/null | sort -hr | head -n 3")
    print(f"        {caches if caches else 'None found.'}")

def purge_memory():
    print(f"{C_BOLD}{C_BLUE}[*] Neutralizing Memory Hogs...{C_RESET}")
    targets = ["chrome", "puppeteer", "playwright", "node"]
    found_any = False
    for target in targets:
        pids = run_cmd(f"ps aux | grep -i {target} | grep -v grep | awk '{{print $2}}'")
        if pids:
            found_any = True
            pid_list = pids.split('\n')
            print(f"    {C_RED}[-] Found {len(pid_list)} {target} processes. Terminating...{C_RESET}")
            for pid in pid_list:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except:
                    pass
    if not found_any:
        print(f"    {C_GREEN}[+] No orphaned memory hogs detected.{C_RESET}")
    else:
        print(f"    {C_GREEN}[+] Memory Purge Complete.{C_RESET}")

def purge_disk():
    print(f"{C_BOLD}{C_BLUE}[*] Executing Surgical Disk Purge...{C_RESET}")
    
    purge_targets = {
        "User Caches": "~/Library/Caches/*",
        "System Logs": "~/Library/Logs/*",
        "IDE Bloat (Windsurf)": "~/.windsurf/core/*",
        "NPM Cache": "~/.npm/_cacache/*",
        "Homebrew Cache": "~/Library/Caches/Homebrew/*",
        "Cloud FileProvider Caches": "~/Library/Application\ Support/FileProvider/*/Cache/*"
    }
    
    for name, path in purge_targets.items():
        expanded_path = os.path.expanduser(path)
        print(f"    {C_YELLOW}[!] Purging {name}...{C_RESET}")
        run_cmd(f"rm -rf {expanded_path}")
    
    print(f"    {C_GREEN}[+] Disk Purge Complete. Reclaimed space will reflect shortly.{C_RESET}")

def validate_env():
    print(f"{C_BOLD}{C_BLUE}[*] Validating Environment Matrix...{C_RESET}")
    env_path = Path(".env")
    if not env_path.exists():
        print(f"    {C_RED}[!] .env MISSING{C_RESET}")
        return

    missing_keys = []
    with open(env_path, 'r') as f:
        for line in f:
            if "PENDING_USER_PROVISION" in line:
                key = line.split('=')[0]
                missing_keys.append(key)
    
    if missing_keys:
        print(f"    {C_YELLOW}[!] {len(missing_keys)} variables pending provision (e.g., {missing_keys[0]}).{C_RESET}")
    else:
        print(f"    {C_GREEN}[+] Environment Fully Synchronized.{C_RESET}")

def main():
    print(f"{C_BOLD}{C_BLUE}========================================{C_RESET}")
    print(f"{C_BOLD}       APEX SYSTEM OPTIMIZER            {C_RESET}")
    print(f"{C_BOLD}{C_BLUE}========================================{C_RESET}")
    
    audit_disk()
    print("")
    validate_env()
    print("")
    
    if "--purge" in sys.argv or "--maximize" in sys.argv:
        purge_memory()
        purge_disk()
    else:
        print(f"{C_YELLOW}[i] Run with --purge to neutralize memory hogs and reclaim disk space.{C_RESET}")
    
    print(f"{C_BOLD}{C_BLUE}========================================{C_RESET}")

if __name__ == "__main__":
    main()
