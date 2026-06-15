#!/bin/bash
#
# LeafDepot 日志包装脚本
# 功能：按日期分文件 + 进程崩溃/正常退出才会返回（让 systemd 感知退出码）
# 用法: ./log_wrapper.sh <服务名> <命令...>
#
set -e

SERVICE_NAME="$1"
shift
[ -z "$SERVICE_NAME" ] && echo "[ERROR] 用法: $0 <服务名> <命令...>" && exit 1

# 自身路径通过 readlink 解析，不依赖 cd 或外部变量
_wrapper_src="$(readlink -f "$0")"
# log_wrapper.sh 位于项目根目录，父目录即 LeafDepot 根目录
_project_root="$(dirname "$_wrapper_src")"
LOG_DIR="$_project_root/logs"
mkdir -p "$LOG_DIR"

export PYTHONIOENCODING=utf-8

# 30 天前清理
find "$LOG_DIR" -name "${SERVICE_NAME}_*.log" -mtime +30 -delete 2>/dev/null

# 入口：单次 exec 写入当日日志文件
# 进程退出后 shell 脚本也跟着退出，systemd 收到 SIGCHLD 才触发重启
exec >> "$LOG_DIR/${SERVICE_NAME}_$(date +%Y%m%d).log" 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] [LOG] === 服务启动: $SERVICE_NAME ==="

exec "$@"
