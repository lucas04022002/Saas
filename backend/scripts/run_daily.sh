#!/bin/zsh
set -euo pipefail

BACKEND_DIR="/Users/lucasguilhot/Documents/Playground/Algorithme_Paris copie/backend"
LOG_DIR="$BACKEND_DIR/logs"
LOG_FILE="$LOG_DIR/daily_run.log"

mkdir -p "$LOG_DIR"

cd "$BACKEND_DIR"
source .venv/bin/activate
python scripts/daily_run.py --limit 50 >> "$LOG_FILE" 2>&1
