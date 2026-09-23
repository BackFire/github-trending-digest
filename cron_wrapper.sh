#!/usr/bin/env bash
# cron wrapper：加载 .env，从部署目录执行 main.py，并记录日志。
set -u

APP_DIR="/opt/github-trending-digest"
ENV_FILE="$APP_DIR/.env"
LOG_DIR="$APP_DIR/logs"

MODE="${1:-daily}"
LOG_FILE="$LOG_DIR/${MODE}.log"

mkdir -p "$LOG_DIR"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
  cd "$APP_DIR" || exit 1
  python3 "$APP_DIR/main.py" --mode "$MODE" --config "$APP_DIR/config.yaml" 2>&1
  RC=$?
  echo "EXIT_CODE=$RC"
} >> "$LOG_FILE"

tail -2000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
exit "$RC"
