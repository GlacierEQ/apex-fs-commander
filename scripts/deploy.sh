#!/usr/bin/env bash
# ============================================================
# APEX MCP SERVER — ONE-COMMAND DEPLOYMENT
# Supports: Linux (systemd), macOS (launchd), POSIX (nohup)
# Usage: bash deploy.sh [--worker-only] [--server-only] [--restart]
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER="$REPO_ROOT/servers/apex_shell_mcp.py"
WORKER="$REPO_ROOT/workers/notion_queue_worker.py"
SERVICE_NAME="apex-shell-mcp"
WORKER_SERVICE="apex-notion-worker"
PYTHON="${PYTHON:-$REPO_ROOT/.venv/bin/python3}"
LOG_DIR="$REPO_ROOT/logs"
SERVER_LOG="$LOG_DIR/apex_shell_mcp.log"
WORKER_LOG="$LOG_DIR/notion_queue_worker.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${BLUE}[APEX]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERR]${NC}  $*"; exit 1; }
banner(){ echo -e "\n${BOLD}${BLUE}$*${NC}\n"; }

DEPLOY_SERVER=true
DEPLOY_WORKER=true
RUN_PIP=true
for arg in "${@:-}"; do
    case $arg in
        --worker-only) DEPLOY_SERVER=false ;;
        --server-only) DEPLOY_WORKER=false ;;
        --restart) info "Restarting services..."; DEPLOY_SERVER=true; DEPLOY_WORKER=true ;;
        --no-pip) RUN_PIP=false ;;
    esac
done

banner "⚡ APEX MCP SERVER — DEPLOYMENT SEQUENCE"
info "Repo root : $REPO_ROOT"
info "Server    : $SERVER"
info "Worker    : $WORKER"
info "OS        : $(uname -s)"

# ─── Python version check ─────────────────────────────────────────────────────
PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo $PY_VER | cut -d. -f1)
PY_MINOR=$(echo $PY_VER | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
    err "Python 3.10+ required, found $PY_VER"
fi
ok "Python $PY_VER"

# ─── Install dependencies ─────────────────────────────────────────────────────
if [ "$RUN_PIP" = true ]; then
    banner "Installing dependencies..."
    $PYTHON -m pip install --quiet --upgrade pip
    $PYTHON -m pip install --quiet \
        "mcp==1.9.0" \
        "notion-client>=2.2.1" \
        "httpx>=0.27.0" \
        "python-dotenv>=1.0.0"
    ok "Dependencies ready"
else
    banner "Bypassing dependency installation (--no-pip)"
fi

# ─── Setup directories ────────────────────────────────────────────────────────
mkdir -p "$LOG_DIR" "$REPO_ROOT/workers"
ok "Directories ready"

# ─── Load .env ────────────────────────────────────────────────────────────────
if [ -f "$REPO_ROOT/.env" ]; then
    set -o allexport
    source "$REPO_ROOT/.env"
    set +o allexport
    ok ".env loaded"
else
    warn "No .env found. Create $REPO_ROOT/.env with NOTION_API_KEY and REPO_ROOT."
fi

if [ -z "${NOTION_API_KEY:-}" ]; then
    warn "NOTION_API_KEY not set — Notion queue worker will be disabled"
else
    ok "NOTION_API_KEY set"
fi

# ─── Detect OS and deploy ─────────────────────────────────────────────────────
OS="$(uname -s)"

deploy_systemd() {
    local name=$1; local script=$2; local log=$3
    cat > /tmp/${name}.service << EOF
[Unit]
Description=APEX ${name}
After=network.target
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
WorkingDirectory=${REPO_ROOT}
ExecStart=${PYTHON} ${script}
Restart=always
RestartSec=5
StandardOutput=append:${log}
StandardError=append:${log}
EnvironmentFile=-${REPO_ROOT}/.env
Environment=REPO_ROOT=${REPO_ROOT}

[Install]
WantedBy=multi-user.target
EOF
    if [ "$EUID" -eq 0 ]; then
        cp /tmp/${name}.service /etc/systemd/system/
        systemctl daemon-reload
        systemctl enable --now "$name"
    else
        mkdir -p ~/.config/systemd/user
        cp /tmp/${name}.service ~/.config/systemd/user/
        systemctl --user daemon-reload
        systemctl --user enable --now "$name"
    fi
    ok "$name deployed via systemd"
}

deploy_launchd() {
    local label=$1; local script=$2; local log=$3
    local plist="$HOME/Library/LaunchAgents/${label}.plist"
    mkdir -p "$HOME/Library/LaunchAgents"
    cat > "$plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>${label}</string>
    <key>ProgramArguments</key>
    <array><string>${PYTHON}</string><string>${script}</string></array>
    <key>WorkingDirectory</key><string>${REPO_ROOT}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>REPO_ROOT</key><string>${REPO_ROOT}</string>
        <key>NOTION_API_KEY</key><string>${NOTION_API_KEY:-}</string>
        <key>NOTION_QUEUE_DB</key><string>66a2012916064ff5b0f54c252569a4b7</string>
        <key>NOTION_LOG_DB</key><string>94a5c74bdd9f43268bffd19ded518d43</string>
    </dict>
    <key>StandardOutPath</key><string>${log}</string>
    <key>StandardErrorPath</key><string>${log}</string>
    <key>KeepAlive</key><true/>
    <key>RunAtLoad</key><true/>
</dict>
</plist>
EOF
    launchctl unload "$plist" 2>/dev/null || true
    launchctl load -w "$plist"
    ok "$label deployed via launchd"
}

deploy_nohup() {
    local name=$1; local script=$2; local log=$3
    local pidfile="/tmp/${name}.pid"
    if [ -f "$pidfile" ] && kill -0 "$(cat $pidfile)" 2>/dev/null; then
        info "Stopping existing $name (PID $(cat $pidfile))..."
        kill "$(cat $pidfile)" 2>/dev/null || true
        sleep 2
    fi
    export REPO_ROOT NOTION_API_KEY NOTION_QUEUE_DB NOTION_LOG_DB
    nohup $PYTHON "$script" >> "$log" 2>&1 &
    echo $! > "$pidfile"
    ok "$name started via nohup (PID: $(cat $pidfile)) — log: $log"
}

banner "Deploying processes..."

if [ "$OS" = "Linux" ] && command -v systemctl &>/dev/null; then
    info "Strategy: Linux systemd"
    $DEPLOY_SERVER && deploy_systemd "$SERVICE_NAME" "$SERVER" "$SERVER_LOG"
    $DEPLOY_WORKER && [ -n "${NOTION_API_KEY:-}" ] && deploy_systemd "$WORKER_SERVICE" "$WORKER" "$WORKER_LOG" || true
elif [ "$OS" = "Darwin" ]; then
    info "Strategy: macOS launchd"
    $DEPLOY_SERVER && deploy_launchd "com.apex.shell-mcp" "$SERVER" "$SERVER_LOG"
    $DEPLOY_WORKER && [ -n "${NOTION_API_KEY:-}" ] && deploy_launchd "com.apex.notion-worker" "$WORKER" "$WORKER_LOG" || true
else
    info "Strategy: POSIX nohup"
    $DEPLOY_SERVER && deploy_nohup "$SERVICE_NAME" "$SERVER" "$SERVER_LOG"
    $DEPLOY_WORKER && [ -n "${NOTION_API_KEY:-}" ] && deploy_nohup "$WORKER_SERVICE" "$WORKER" "$WORKER_LOG" || true
fi

# ─── Health check ─────────────────────────────────────────────────────────────
sleep 3
banner "Startup verification"
for log in "$SERVER_LOG" "$WORKER_LOG"; do
    if [ -f "$log" ]; then
        echo -e "\n${BOLD}$(basename $log):${NC}"
        tail -8 "$log" 2>/dev/null || true
    fi
done

banner "DEPLOYMENT COMPLETE"
ok "Server logs : tail -f $SERVER_LOG"
ok "Worker logs : tail -f $WORKER_LOG"
ok "Notion Hub  : https://www.notion.so/317b1e4f32238144a757e7cdd9da7b1e"
ok "Queue DB    : https://www.notion.so/66a2012916064ff5b0f54c252569a4b7"
ok "Exec Log    : https://www.notion.so/94a5c74bdd9f43268bffd19ded518d43"
echo ""
