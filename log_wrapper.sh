#!/bin/bash
#
# 日志包装脚本 — 按日期分文件记录服务输出
# 用法: ./log_wrapper.sh <服务名> <命令...>
# 例:   ./log_wrapper.sh gateway /path/to/python -m uvicorn gateway:app ...
#
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="$1"
shift
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

DATE=$(date +%Y%m%d)
LOG_FILE="$LOG_DIR/${SERVICE_NAME}_${DATE}.log"

# 清理 7 天前的旧日志
find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null

exec "$@" >> "$LOG_FILE" 2>&1
