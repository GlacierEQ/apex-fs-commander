#!/usr/bin/env python3
"""
APEX ORBITAL TELEMETRY DASHBOARD
SpaceX-Grade Ecosystem Monitoring & Bootstrap Coordinator
Case: 1FDV-23-0001009
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime, timezone

# Ensure we're in the right environment
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from servers.apex_universal_skill import (
    ServerRegistry,
    ActivationStrategy,
    HeartbeatMonitor,
    ServerStatus
)

# Colors for terminal output
C_GREEN = '\033[92m'
C_RED = '\033[91m'
C_YELLOW = '\033[93m'
C_BLUE = '\033[94m'
C_BOLD = '\033[1m'
C_RESET = '\033[0m'

async def run_telemetry():
    print(f"{C_BOLD}{C_BLUE}======================================================================{C_RESET}")
    print(f"{C_BOLD}🚀 APEX OMNIVERSE: ORBITAL TELEMETRY & COMMAND INFRASTRUCTURE{C_RESET}")
    print(f"{C_BLUE}======================================================================{C_RESET}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Runtime: Python {sys.version.split()[0]} | OS: macOS (Apple Silicon)")
    print(f"Sandbox Restriction: {C_YELLOW}ACTIVE{C_RESET} (Pending Bootstrap)\n")
    
    registry = ServerRegistry()
    activator = ActivationStrategy()
    monitor = HeartbeatMonitor(registry, interval=5.0)
    
    print(f"{C_BOLD}--- INITIALIZING SENSOR ARRAY ({len(registry.servers)} NODES) ---{C_RESET}")
    
    # Run a single heartbeat check
    await monitor._check_all()
    report = monitor.get_status_report()
    
    healthy = 0
    degraded = 0
    offline = 0
    
    print("\n{:<30} | {:<15} | {:<12} | {}".format("SERVER NODE", "STATUS", "LATENCY", "STRATEGY"))
    print("-" * 80)
    
    for name, data in report.items():
        status = data['status']
        latency = f"{data['latency_ms']}ms" if data['latency_ms'] > 0 else "---"
        strategy = activator.get_strategy(name)
        
        color = C_RESET
        if status == ServerStatus.HEALTHY.value:
            color = C_GREEN
            healthy += 1
        elif status == ServerStatus.SANDBOX_RESTRICTED.value or status == ServerStatus.DEGRADED.value:
            color = C_YELLOW
            degraded += 1
        else:
            color = C_RED
            offline += 1
            
        print(f"{color}{name:<30} | {status.upper():<15} | {latency:<12} | {strategy}{C_RESET}")

    print("\n" + "="*80)
    print(f"{C_BOLD}SYSTEM HEALTH:{C_RESET} {C_GREEN}{healthy} NOMINAL{C_RESET} | {C_YELLOW}{degraded} RESTRICTED/DEGRADED{C_RESET} | {C_RED}{offline} OFFLINE{C_RESET}")
    
    if degraded > 0 or offline > 0:
        print(f"\n{C_BOLD}{C_YELLOW}ACTION REQUIRED: ONE-TIME BOOTSTRAP OVERRIDE{C_RESET}")
        print("To clear sandbox restrictions and achieve full autonomous launchctl orchestration, execute:")
        print(f"  {C_BOLD}sudo scripts/bootstrap_apex.sh{C_RESET}")
    else:
        print(f"\n{C_BOLD}{C_GREEN}ALL SYSTEMS GO FOR AUTONOMOUS ORCHESTRATION.{C_RESET}")

if __name__ == "__main__":
    asyncio.run(run_telemetry())
