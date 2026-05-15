#!/usr/bin/env bash
# APEX — SHOW SERVER STATUS
REPO_DIR="${REPO_ROOT:-$HOME/apex-fs-commander}"
echo ""
echo "====  APEX SERVER STATUS  ===="
echo ""
for svc in apex_shell_mcp apex_terminal_mcp apex_master_mcp apex_universal_mcp apex_spiral_mcp apex_stealth_diamond_mcp apex_audio_processor_mcp apex_evidence_mcp apex_github_mcp apex_jefs_scraper_mcp apex_notion_mcp apex_case_intelligence_mcp primordial_terminal_mcp notion_queue_worker; do
  pid=""
  # 1. On macOS, query launchd directly
  if [ "$(uname -s)" = "Darwin" ]; then
    case "$svc" in
      apex_shell_mcp) label="com.apex.shell-mcp" ;;
      apex_terminal_mcp) label="com.apex.terminal-mcp" ;;
      apex_master_mcp) label="com.apex.master-mcp" ;;
      apex_universal_mcp) label="com.apex.universal-mcp" ;;
      apex_spiral_mcp) label="com.apex.spiral-mcp" ;;
      apex_stealth_diamond_mcp) label="com.apex.stealth-diamond-mcp" ;;
      apex_audio_processor_mcp) label="com.apex.audio-processor-mcp" ;;
      apex_evidence_mcp) label="com.apex.evidence-mcp" ;;
      apex_github_mcp) label="com.apex.github-mcp" ;;
      apex_jefs_scraper_mcp) label="com.apex.jefs-scraper-mcp" ;;
      apex_notion_mcp) label="com.apex.notion-mcp" ;;
      apex_case_intelligence_mcp) label="com.apex.case-intelligence-mcp" ;;
      primordial_terminal_mcp) label="com.apex.primordial-terminal-mcp" ;;
      notion_queue_worker) label="com.apex.notion-worker" ;;
      *) label="" ;;
    esac
    if [ -n "$label" ]; then
      pid=$(launchctl list 2>/dev/null | grep "$label" | awk '{print $1}')
      # If pid is "-", it is loaded but not running
      if [ "$pid" = "-" ]; then
        pid=""
      fi
    fi
  fi

  # 2. Fallback to raw /tmp pidfiles
  if [ -z "$pid" ]; then
    case "$svc" in
      apex_shell_mcp) pidfile="/tmp/apex-shell-mcp.pid" ;;
      apex_terminal_mcp) pidfile="/tmp/apex-terminal-mcp.pid" ;;
      apex_master_mcp) pidfile="/tmp/apex-master-mcp.pid" ;;
      apex_universal_mcp) pidfile="/tmp/apex-universal-mcp.pid" ;;
      apex_spiral_mcp) pidfile="/tmp/apex-spiral-mcp.pid" ;;
      apex_stealth_diamond_mcp) pidfile="/tmp/apex-stealth-diamond-mcp.pid" ;;
      apex_audio_processor_mcp) pidfile="/tmp/apex-audio-processor-mcp.pid" ;;
      apex_evidence_mcp) pidfile="/tmp/apex-evidence-mcp.pid" ;;
      apex_github_mcp) pidfile="/tmp/apex-github-mcp.pid" ;;
      apex_jefs_scraper_mcp) pidfile="/tmp/apex-jefs-scraper-mcp.pid" ;;
      apex_notion_mcp) pidfile="/tmp/apex-notion-mcp.pid" ;;
      apex_case_intelligence_mcp) pidfile="/tmp/apex-case-intelligence-mcp.pid" ;;
      primordial_terminal_mcp) pidfile="/tmp/primordial-terminal-mcp.pid" ;;
      notion_queue_worker) pidfile="/tmp/apex-notion-worker.pid" ;;
      *) pidfile="" ;;
    esac
    if [ -n "$pidfile" ] && [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
      pid="$(cat "$pidfile")"
    fi
  fi

  if [ -n "$pid" ]; then
    echo "  ✅ $svc  (PID $pid)"
  else
    echo "  ❌ $svc  NOT RUNNING"
  fi
done
echo ""
echo "Logs:"
ls -lh "$REPO_DIR/logs/"*.log 2>/dev/null | awk '{print "  "$5" "$NF}' || echo "  No logs found"
echo ""
