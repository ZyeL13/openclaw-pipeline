#!/bin/bash
set -e

# ── COLOR OUTPUT ──────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ── LOAD .ENV ─────────────────────────────────────────────────────────────────
ENV_FILE="$HOME/konten-pipeline/.env"

if [ -f "$ENV_FILE" ]; then
    echo -e "${BLUE}[INFO] Loading .env from $ENV_FILE${NC}"
    set -a
    source "$ENV_FILE"
    set +a
    echo -e "${GREEN}[OK] .env loaded successfully${NC}"
else
    echo -e "${RED}[ERROR] .env not found at $ENV_FILE${NC}"
    exit 1
fi

# ── VALIDATE REQUIRED VARS ────────────────────────────────────────────────────
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo -e "${RED}[ERROR] TELEGRAM_BOT_TOKEN not set in .env${NC}"
    exit 1
fi

if [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo -e "${RED}[ERROR] TELEGRAM_CHAT_ID not set in .env${NC}"
    exit 1
fi

echo -e "${GREEN}[OK] Telegram config loaded (BOT_TOKEN: ${#TELEGRAM_BOT_TOKEN} chars, CHAT_ID: $TELEGRAM_CHAT_ID)${NC}"

# ── CHECK ARGUMENTS ───────────────────────────────────────────────────────────
RUN_DIR="${1:-}"

if [ -z "$RUN_DIR" ]; then
    echo -e "${RED}[ERROR] Usage: ./kirim.sh <run_dir_path>${NC}"
    echo -e "${YELLOW}Example: ./kirim.sh /path/to/konten-pipeline/output/2024-01-01_12-00-00${NC}"
    exit 1
fi

if [ ! -d "$RUN_DIR" ]; then
    echo -e "${RED}[ERROR] Directory not found: $RUN_DIR${NC}"
    exit 1
fi

# ── CHECK FILES ───────────────────────────────────────────────────────────────
VIDEO_PATH="$RUN_DIR/final_video.mp4"
QC_FILE="$RUN_DIR/qc_report.json"

if [ ! -f "$VIDEO_PATH" ]; then
    echo -e "${RED}[ERROR] final_video.mp4 not found in $RUN_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}[OK] Video found: $VIDEO_PATH${NC}"

# ── EXTRACT QC SCORE ──────────────────────────────────────────────────────────
QC_SCORE="N/A"
if [ -f "$QC_FILE" ]; then
    QC_SCORE=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('overall_score','N/A'))" "$QC_FILE" 2>/dev/null || echo "N/A")
    echo -e "${GREEN}[OK] QC Score: $QC_SCORE/10${NC}"
else
    echo -e "${YELLOW}[WARN] QC report not found at $QC_FILE${NC}"
fi

# ── COPY TO STORAGE ───────────────────────────────────────────────────────────
TARGET_BASE="$HOME/storage/shared/termux_scripts/videos"
FOLDER_NAME=$(basename "$RUN_DIR")
TARGET_DIR="$TARGET_BASE/$FOLDER_NAME"

mkdir -p "$TARGET_DIR"
cp "$VIDEO_PATH" "$TARGET_DIR/final_video.mp4"
echo -e "${GREEN}[OK] Video copied to $TARGET_DIR/final_video.mp4${NC}"

# ── TELEGRAM NOTIFICATION ─────────────────────────────────────────────────────
echo -e "${BLUE}[INFO] Sending Telegram notification...${NC}"

# Build message (simplified, without MarkdownV2 escaping)
if [ "$QC_SCORE" != "N/A" ]; then
    MSG="Video Selesai!
Folder: ${FOLDER_NAME}
QC Score: ${QC_SCORE}/10
Path: ${TARGET_DIR}/final_video.mp4"
else
    MSG="Video Selesai!
Folder: ${FOLDER_NAME}
Path: ${TARGET_DIR}/final_video.mp4"
fi

# Send notification (plain text, more reliable)
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
     -d chat_id="$TELEGRAM_CHAT_ID" \
     -d text="$MSG")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}[OK] Telegram notification sent successfully${NC}"
else
    echo -e "${RED}[ERROR] Failed to send Telegram notification (HTTP $HTTP_CODE)${NC}"
    echo -e "${YELLOW}Response: $BODY${NC}"
    exit 1
fi

# ── DONE ──────────────────────────────────────────────────────────────────────
echo -e "${GREEN}✅ Done! Video available at: $TARGET_DIR/final_video.mp4${NC}"
