#!/usr/bin/env bash
# ==============================================================================
# APEX FORENSIC ORCHESTRATOR LOOP
# Periodically organizes, syncs, transcribes, and links all case evidence.
# ==============================================================================

# Paths
PROJECT_DIR="/Users/macarena1/dev/projects/apex-fs-commander"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
LOG_FILE="$PROJECT_DIR/logs/orchestrator_loop.log"

# Setup Logs
mkdir -p "$(dirname "$LOG_FILE")"

echo "----------------------------------------------------------------" | tee -a "$LOG_FILE"
echo "🚀 APEX ORCHESTRATOR INITIATED: $(date)" | tee -a "$LOG_FILE"
echo "----------------------------------------------------------------" | tee -a "$LOG_FILE"

# 1. ORGANIZE DROPBOX
echo "📂 Running Dropbox Organization..." | tee -a "$LOG_FILE"
python3 "$SCRIPTS_DIR/apex_dropbox_organizer.py" >> "$LOG_FILE" 2>&1

# 2. CROSS-SYNC TO CLOUD (OneDrive/iCloud)
echo "☁️ Running Cloud Sync & Manifest Generation..." | tee -a "$LOG_FILE"
python3 "$SCRIPTS_DIR/apex_forensic_cloud_organizer.py" >> "$LOG_FILE" 2>&1

# 3. AUTO-TRANSCRIBE NEW MEDIA
echo "📝 Running Auto-Transcription..." | tee -a "$LOG_FILE"
python3 "$SCRIPTS_DIR/apex_auto_transcribe.py" >> "$LOG_FILE" 2>&1

# 4. LINK TO DOSSIER
echo "🔗 Running Dossier Linker..." | tee -a "$LOG_FILE"
python3 "$SCRIPTS_DIR/apex_dossier_linker.py" >> "$LOG_FILE" 2>&1

echo "----------------------------------------------------------------" | tee -a "$LOG_FILE"
echo "✅ ORCHESTRATION CYCLE COMPLETE: $(date)" | tee -a "$LOG_FILE"
echo "----------------------------------------------------------------" | tee -a "$LOG_FILE"
