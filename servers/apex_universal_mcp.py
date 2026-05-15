#!/usr/bin/env python3
"""
APEX UNIVERSAL MCP SERVER (Meta-Router)
The unified gateway for raw system primitives and cross-MCP orchestration.
Provides universal shell, filesystem, and dynamic routing to domain-specific servers.
"""

import os
import sys
import json
import asyncio
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add parent directory to sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    from mcp.server.fastmcp import FastMCP
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    print("Error: Missing dependencies. Run: python -m pip install -r servers/requirements.txt")
    sys.exit(1)

# Initialize FastMCP Server
mcp = FastMCP(
    "APEX-Universal-MCP",
    dependencies=["mcp", "requests", "python-dotenv"]
)

# ==============================================================================
# 🛠️ PILLAR 1: RAW SYSTEM PRIMITIVES
# ==============================================================================

@mcp.tool()
def universal_shell(command: str, timeout: int = 60) -> Dict[str, Any]:
    """
    Execute a shell command with universal system access.
    
    Args:
        command: The shell command to execute.
        timeout: Execution timeout in seconds (default: 60).
    """
    try:
        process = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT)
        )
        return {
            "stdout": process.stdout,
            "stderr": process.stderr,
            "returncode": process.returncode,
            "success": process.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout} seconds", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}

@mcp.tool()
def universal_fs(action: str, path: str, content: Optional[str] = None) -> Dict[str, Any]:
    """
    Universal File System interface.
    
    Args:
        action: read, write, append, list, delete, exists.
        path: Path relative to repository root.
        content: Data to write or append.
    """
    target_path = REPO_ROOT / path
    
    try:
        if action == "read":
            return {"content": target_path.read_text(), "success": True}
        elif action == "write":
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content or "")
            return {"message": f"Wrote to {path}", "success": True}
        elif action == "append":
            with target_path.open("a") as f:
                f.write(content or "")
            return {"message": f"Appended to {path}", "success": True}
        elif action == "list":
            items = [str(p.relative_to(REPO_ROOT)) for p in target_path.iterdir()]
            return {"items": items, "success": True}
        elif action == "delete":
            if target_path.is_dir():
                import shutil
                shutil.rmtree(target_path)
            else:
                target_path.unlink()
            return {"message": f"Deleted {path}", "success": True}
        elif action == "exists":
            return {"exists": target_path.exists(), "success": True}
        else:
            return {"error": f"Unknown action: {action}", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}

# ==============================================================================
# 🕸️ PILLAR 2: META-ROUTING (Dynamic Discovery)
# ==============================================================================

@mcp.tool()
def list_mcp_servers() -> Dict[str, Any]:
    """
    List all specialized MCP servers available in the ecosystem.
    """
    servers_dir = REPO_ROOT / "servers"
    mcp_files = list(servers_dir.glob("apex_*_mcp.py"))
    
    server_info = {}
    for f in mcp_files:
        name = f.stem
        if name == "apex_universal_mcp":
            continue
        
        # Simple regex to find tool names
        content = f.read_text()
        tools = re.findall(r'def\s+(\w+)\s*\(', content)
        server_info[name] = {"path": str(f.relative_to(REPO_ROOT)), "tools": tools}
        
    return {"servers": server_info, "success": True}

@mcp.tool()
def execute_mcp_tool(server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dynamically execute a tool on a specialized MCP server and return the results.
    
    Args:
        server_name: The name of the server (e.g., 'apex_master_mcp').
        tool_name: The tool to invoke.
        arguments: Arguments for the tool as a dictionary.
    """
    servers = list_mcp_servers().get("servers", {})
    if server_name not in servers:
        return {"error": f"Server '{server_name}' not found.", "success": False}
    
    if tool_name not in servers[server_name]["tools"]:
        return {"error": f"Tool '{tool_name}' not found on server '{server_name}'.", "success": False}

    server_path = REPO_ROOT / servers[server_name]["path"]
    
    # We use a 'one-shot' execution pattern. 
    # Since these are FastMCP servers, we can try to import them and call the function 
    # or run a bridge script. For now, we'll use a Python bridge to execute the tool function.
    
    bridge_code = f"""
import sys
import json
import asyncio
from pathlib import Path

# Setup path
repo_root = Path('{REPO_ROOT}')
sys.path.insert(0, str(repo_root))

# Import the server module
import importlib.util
spec = importlib.util.spec_from_file_location('{server_name}', '{server_path}')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Find and call the tool
async def run():
    found = False
    if hasattr(module, 'mcp'):
        # Use the internal tool manager
        try:
            tool = module.mcp._tool_manager.get_tool('{tool_name}')
            if tool:
                # Check if the function is a coroutine
                if asyncio.iscoroutinefunction(tool.fn):
                     result = await tool.fn(**arguments)
                 else:
                     result = tool.fn(**arguments)
                print(json.dumps(result))
                return True
        except Exception as e:
            print(json.dumps({{"error": str(e)}}))
            return True

    if not found:
        print(json.dumps({{"error": "Tool {tool_name} not found in {server_name}"}}))
        return False

if __name__ == "__main__":
    asyncio.run(run())
"""

    try:
        # Use the project's venv python if available
        python_bin = REPO_ROOT / ".venv" / "bin" / "python3"
        if not python_bin.exists():
            python_bin = "python3"
            
        process = subprocess.run(
            [str(python_bin), "-c", bridge_code],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if process.returncode != 0:
            return {"error": process.stderr, "stdout": process.stdout, "success": False}
            
        try:
            return {"result": json.loads(process.stdout.strip()), "success": True}
        except json.JSONDecodeError:
            return {"error": "Failed to parse tool output", "raw_output": process.stdout, "success": False}
            
    except Exception as e:
        return {"error": str(e), "success": False}

# ==============================================================================
# 🧬 PILLAR 3: SELF-EVOLUTION & PROACTIVE PREPARATION
# ==============================================================================

@mcp.tool()
def proactive_resource_check(task_requirements: List[str]) -> Dict[str, Any]:
    """
    Check if the current ecosystem has the tools required for a task.
    
    Args:
        task_requirements: List of capabilities needed (e.g., ['audio_transcription', 'vector_search']).
    """
    servers = list_mcp_servers().get("servers", {})
    all_tools = []
    for s in servers.values():
        all_tools.extend(s["tools"])
        
    missing = [req for req in task_requirements if not any(req in t for t in all_tools)]
    
    return {
        "missing_capabilities": missing,
        "status": "READY" if not missing else "DEFICIENT",
        "recommendation": "Use install_mcp_capability for missing tools." if missing else "Proceed with execution."
    }

@mcp.tool()
def install_mcp_capability(query: str) -> Dict[str, Any]:
    """
    Search for and suggest the installation of a new MCP capability from the global registry.
    """
    # This acts as a bridge to the platform's mcp-manager-router
    return {
        "action_required": "USE_PLATFORM_TOOL",
        "tool_to_call": "mcp_mcp-manager-router_search_mcp_servers",
        "query": query,
        "note": "I will now search the global registry for the requested capability."
    }

@mcp.tool()
def scaffold_specialized_server(name: str, purpose: str, tools: List[str]) -> Dict[str, Any]:
    """
    Scaffold a new specialized FastMCP server in the servers/ directory.
    
    Args:
        name: Name of the server (e.g., 'audio_processor').
        purpose: Description of what the server does.
        tools: List of tool names to scaffold.
    """
    filename = f"apex_{name}_mcp.py"
    target_path = REPO_ROOT / "servers" / filename
    
    if target_path.exists():
        return {"error": f"Server {filename} already exists.", "success": False}
        
    tool_defs = ""
    for t in tools:
        tool_defs += f"""
@mcp.tool()
async def {t}(**kwargs) -> Dict[str, Any]:
    \"\"\"
    Auto-scaffolded tool for {t}.
    \"\"\"
    return {{"status": "not_implemented", "tool": "{t}"}}
"""

    content = f"""#!/usr/bin/env python3
\"\"\"
APEX {name.upper()} MCP SERVER
Purpose: {purpose}
\"\"\"

import os
import sys
from pathlib import Path
from typing import Dict, Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("APEX-{name.capitalize()}-MCP")

{tool_defs}

if __name__ == "__main__":
    mcp.run()
"""
    target_path.write_text(content)
    return {"message": f"Scaffolded {filename} with {len(tools)} tools.", "success": True}

if __name__ == "__main__":
    mcp.run()
