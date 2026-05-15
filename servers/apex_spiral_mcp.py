#!/usr/bin/env python3
"""
APEX SPIRAL ENGINE MCP
The recursive heart of the Apex Nexus. 
Manages the "Spiral Cycle": Initiate -> Expand -> Integrate -> Ascend.
Ensures that every task results in a core system upgrade.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("APEX-Spiral-Engine")

# The Spiral Log: Tracking the ascension of the system
SPIRAL_LOG_PATH = REPO_ROOT / ".agent-mem" / "spiral_evolution.json"

def _load_spiral_log():
    if not SPIRAL_LOG_PATH.exists():
        SPIRAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        return {"cycles": [], "current_tier": 1, "total_evolutions": 0}
    return json.loads(SPIRAL_LOG_PATH.read_text())

def _save_spiral_log(log):
    SPIRAL_LOG_PATH.write_text(json.dumps(log, indent=2))

@mcp.tool()
def log_spiral_cycle(task_name: str, enhancements: List[str], quality_metrics: Dict[str, float]) -> Dict[str, Any]:
    """
    Log the completion of a spiral cycle and document the system's expansion.
    """
    log = _load_spiral_log()
    cycle = {
        "timestamp": datetime.now().isoformat(),
        "task": task_name,
        "enhancements": enhancements,
        "metrics": quality_metrics,
        "tier": log["current_tier"]
    }
    log["cycles"].append(cycle)
    log["total_evolutions"] += len(enhancements)
    
    # Check for tier ascension (every 5 evolutions)
    if log["total_evolutions"] // 5 > log["current_tier"]:
        log["current_tier"] += 1
        cycle["ascension"] = True
        
    _save_spiral_log(log)
    return {"status": "CYCLE_INTEGRATED", "new_tier": log["current_tier"], "total_evolutions": log["total_evolutions"]}

@mcp.tool()
def propose_evolution_path() -> Dict[str, Any]:
    """
    Analyze the current ecosystem and propose the next 'outward' spiral step.
    """
    # This tool queries the list_mcp_servers and checks for missing bridges or older code
    # to suggest the next improvement.
    from servers.apex_universal_mcp import list_mcp_servers
    servers = list_mcp_servers().get("servers", {})
    
    proposals = []
    if "apex_audio_processor_mcp" in servers:
        proposals.append("Integrate Whisper-v3 local bridge for high-fidelity transcription.")
        
    if "apex_master_mcp" in servers:
        proposals.append("Refactor Legacy Master logic into specialized domain micro-servers.")
        
    return {
        "proposals": proposals,
        "strategy": "EXPANSION",
        "focus": "Capability Deepening"
    }

@mcp.tool()
def execute_system_refinement(target_file: str) -> Dict[str, Any]:
    """
    Automate the 'Refinement' phase by applying Apex Gold Standard patterns to a file.
    """
    # This tool would typically use the agent's internal 'replace' logic
    # but as an MCP tool, it provides the 'Refinement Directives'.
    return {
        "directives": [
            "Add explicit type hinting to all functions.",
            "Implement try-except blocks with detailed error logging.",
            "Ensure FastMCP tool decorators are correctly applied.",
            "Add docstrings with 'Args' and 'Returns' sections."
        ],
        "target": target_file
    }

if __name__ == "__main__":
    mcp.run()
