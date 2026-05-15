#!/usr/bin/env bash
# ============================================================
# APEX MASTER DEPLOY v2.1 — GlacierEQ/apex-fs-commander
# Case: 1FDV-23-0001009 | Operator: Casey Barton
# Fixed: alias persistence, env key names, missing packages
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}[APEX]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERR]${NC} $1"; }

echo -e "${BOLD}${CYAN}"
echo "  ⚡ APEX-FS-COMMANDER MASTER DEPLOY v2.1"
echo "  Case: 1FDV-23-0001009 | Operator: Casey Barton"
echo "  $(date '+%Y-%m-%d %H:%M %Z')"
echo -e "${NC}"

# ── 1. DETECT ENVIRONMENT
if command -v pkg &>/dev/null; then
  ENV="termux"
  PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
elif [[ "$(uname)" == "Darwin" ]]; then
  ENV="mac"
  PREFIX="/usr/local"
else
  ENV="linux"
  PREFIX="/usr/local"
fi
log "Environment: $ENV"

# ── 2. INSTALL SYSTEM DEPS
log "Installing system dependencies..."
if [ "$ENV" = "termux" ]; then
  pkg install -y python ffmpeg cloudflared openssh git 2>/dev/null || warn "Some pkg installs may need retry"
elif [ "$ENV" = "mac" ]; then
  if command -v brew &>/dev/null; then
    brew install ffmpeg git cloudflared 2>/dev/null || warn "brew partial"
  else
    warn "Homebrew not found — skipping system deps"
  fi
else
  sudo apt-get update -qq 2>/dev/null
  sudo apt-get install -y ffmpeg git curl 2>/dev/null || warn "apt partial"
  if ! command -v cloudflared &>/dev/null; then
    curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
      -o "$PREFIX/bin/cloudflared" && chmod +x "$PREFIX/bin/cloudflared" || warn "cloudflared manual install failed"
  fi
fi

# ── 3. INSTALL PYTHON PACKAGES (all of them)
log "Installing Python packages..."
pip install --quiet --upgrade \
  faster-whisper \
  whisperx \
  requests \
  notion-client \
  python-dotenv \
  msal \
  supabase \
  PyGithub \
  aiohttp \
  flask \
  pyngrok \
  anthropic \
  openai \
  rich \
  httpx \
  pydantic || warn "Some pip packages failed — retry individually"
log "Python packages done"

# ── 4. SETUP ENV FILE
if [ ! -f .env.apex ]; then
  warn ".env.apex not found — copying from .env.example"
  [ -f .env.example ] && cp .env.example .env.apex
else
  log ".env.apex found ✔"
fi

# ── 5. MAKE apexgo EXECUTABLE SCRIPT (no alias needed)
log "Installing apexgo binary..."
chmod +x apexgo

# Create ~/bin if it doesn't exist
mkdir -p "$HOME/bin"

# Symlink into ~/bin (always on PATH in Termux)
ln -sf "$(pwd)/apexgo" "$HOME/bin/apexgo"
log "apexgo symlinked to ~/bin/apexgo ✔"

# Ensure ~/bin is in PATH permanently
for RC in ~/.bashrc ~/.zshrc ~/.bash_profile ~/.profile; do
  if [ -f "$RC" ]; then
    grep -q 'HOME/bin' "$RC" 2>/dev/null || echo 'export PATH="$HOME/bin:$PATH"' >> "$RC"
  fi
done
export PATH="$HOME/bin:$PATH"
log "PATH updated ✔"

# ── 6. WRITE CONSOLIDATED .env LOADER
# The health check was missing keys because it looks for GITHUB_TOKEN
# but .env.apex has GITHUB_TOKEN. Also loads from github.env etc.
cat > "$HOME/.apex_env_loader" << 'ENVEOF'
# APEX env loader — source this or add to .bashrc
APEX_DIR="$(pwd)"
for f in "$APEX_DIR/.env.apex" \
         "$APEX_DIR/ai-services.env" \
         "$APEX_DIR/apex.env" \
         "$APEX_DIR/github.env" \
         "$APEX_DIR/infrastructure.env" \
         "$APEX_DIR/memory.env"; do
  if [ -f "$f" ]; then
    perms="$(stat -c %a "$f" 2>/dev/null || stat -f %Lp "$f" 2>/dev/null || echo 600)"
    case "$perms" in
      *[2367][0-7]|*[0-7][2367]) echo "Skipping insecure env file: $f" >&2 ;;
      *) set -a && source "$f" && set +a ;;
    esac
  fi
done
# Key aliases — bridge env file names to what apex_terminal_commander.py expects
export GITHUB_TOKEN="${GITHUB_TOKEN:-$GITHUB_PAT}"
export NOTION_API_KEY="${NOTION_API_KEY:-$NOTION_TOKEN}"
export SUPABASE_SERVICE_ROLE_KEY="${SUPABASE_SERVICE_ROLE_KEY:-$SUPABASE_KEY}"
ENVEOF

# Add loader to .bashrc if not already there
for RC in ~/.bashrc ~/.zshrc; do
  if [ -f "$RC" ]; then
    grep -q 'apex_env_loader' "$RC" 2>/dev/null || \
      echo 'source "$HOME/.apex_env_loader" 2>/dev/null' >> "$RC"
  fi
done
source "$HOME/.apex_env_loader" 2>/dev/null || true
log "Env loader installed ✔"

# ── 7. HEALTH CHECK
log "Running health check..."
apexgo health || warn "Health check complete — fix any red items above"

# ── 8. SUMMARY
echo ""
echo -e "${BOLD}${GREEN}═════════════════════════════════════════${NC}"
echo -e "${BOLD}  ✅ APEX v2.1 DEPLOY COMPLETE${NC}"
echo -e "${GREEN}═════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}apexgo is now a permanent command — open any new terminal and run:${NC}"
echo ""
echo "  apexgo health"
echo "  apexgo onedrive download-audio"
echo "  apexgo whisper transcribe-all"
echo "  apexgo tunnel start"
echo "  apexgo vector track-trigger"
echo ""
echo -e "  ${BOLD}The Glacier is Unstoppable.${NC}"
echo ""
