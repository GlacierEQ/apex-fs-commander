#!/usr/bin/env python3
import subprocess
import os
import sys
from pathlib import Path

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode('utf-8').strip()
    except:
        return ""

def audit_disk():
    print("--- 💾 DISK AUDIT ---")
    df = run_cmd("df -h . | tail -n 1")
    print(f"Current Partition: {df}")
    
    # print("\nTop 5 Home Directory Hogs:")
    # hogs = run_cmd("du -sh ~/* 2>/dev/null | sort -hr | head -n 5")
    # print(hogs if hogs else "Scanning...")
    
    print("\nTop 5 Cache Hogs:")
    caches = run_cmd("du -sh ~/Library/Caches/* 2>/dev/null | sort -hr | head -n 5")
    print(caches if caches else "None found.")
    
    print("\nFiles > 200MB:")
    large_files = run_cmd("find ~ -type f -size +200M -exec ls -lh {} + 2>/dev/null | sort -hr -k 5 | head -n 5")
    print(large_files if large_files else "None found in immediate scan.")

def audit_memory():
    print("\n--- 🧠 MEMORY AUDIT ---")
    print("Top 5 Memory Hogs (RSS):")
    # %CPU %MEM RSS COMMAND
    m_hogs = run_cmd("ps aux | sort -rn -k 4 | head -n 5 | awk '{print $3\"% CPU | \"$4\"% MEM | \"$6/1024\" MB | \"$11}'")
    print(m_hogs)

    print("\nPotential Orphaned Processes (Chrome/Puppeteer):")
    orphans = run_cmd("ps aux | grep -iE 'chrome|puppeteer' | grep -v grep | awk '{print $2\" | \"$11}'")
    print(orphans if orphans else "None detected.")

def main():
    print("========================================")
    print("      APEX SYSTEM RESOURCE AUDIT        ")
    print("========================================")
    audit_disk()
    audit_memory()
    print("========================================")

if __name__ == "__main__":
    main()
