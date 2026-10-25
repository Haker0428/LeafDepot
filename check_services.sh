#!/bin/bash
#
# LeafDepot 服务状态轮询观察脚本（无需 root）
# 用法:
#   ./check_services.sh [间隔秒数，默认10] [--forever]
#
# 默认模式：全部服务连续 3 轮就绪后自动退出（退出前打印各服务今日日志尾部）
# --forever 模式：一直轮询，用于观察重启全过程（Ctrl+C 随时退出）
#
# 测试姿势：终端 A 跑本脚本，终端 B 跑 sudo ./daily_task.sh，
#           肉眼验证服务逐个下线->上线
#
set -u

SCRIPT_SRC="$(readlink -f "$0")"
PROJECT_ROOT="$(dirname "$SCRIPT_SRC")"
LOG_DIR="$PROJECT_ROOT/logs"

# ---------- 参数解析 ----------
INTERVAL=10
FOREVER=false
for a in "$@"; do
    case "$a" in
        --forever) FOREVER=true ;;
        *) INTERVAL="$a" ;;
    esac
done

SERVICES=(gateway worker lms rcs web)
declare -A PORTS=([gateway]=8000 [lms]=6000 [rcs]=4001 [web]=5173)

port_up() { ss -tln 2>/dev/null | grep -q ":$1 "; }

trap 'echo ""; echo "观察结束（手动停止）"; exit 0' INT TERM

NEED_STREAK=3
ready_streak=0

echo "项目目录: $PROJECT_ROOT"
echo "轮询间隔: ${INTERVAL}s  模式: $([ "$FOREVER" = true ] && echo "持续轮询(--forever)" || echo "全部就绪连续${NEED_STREAK}轮后自动退出")"
echo ""

while true; do
    line="$(date '+%H:%M:%S')"
    all_ready=true
    for s in "${SERVICES[@]}"; do
        st="$(systemctl is-active "leafdepot-$s" 2>/dev/null || true)"
        p="${PORTS[$s]:-}"
        if [ "$st" = "active" ]; then mark="✔"; else mark="✘"; all_ready=false; fi
        if [ -n "$p" ]; then
            if port_up "$p"; then mark="$mark(:$p✔)"; else mark="$mark(:$p✘)"; all_ready=false; fi
        fi
        line="$line  $s=$mark"
    done
    echo "$line"

    if [ "$all_ready" = true ]; then
        ready_streak=$((ready_streak + 1))
        if [ "$FOREVER" != true ] && [ "$ready_streak" -ge "$NEED_STREAK" ]; then
            TODAY=$(date +%Y%m%d)
            echo ""
            echo "=== 全部服务就绪（连续 ${NEED_STREAK} 轮验证通过）==="
            echo "--- 各服务今日日志最后 3 行 ---"
            for s in "${SERVICES[@]}"; do
                lf="$LOG_DIR/${s}_${TODAY}.log"
                echo "[$s] $lf"
                if [ -f "$lf" ]; then tail -3 "$lf" | sed 's/^/    /'; else echo "    (日志文件不存在)"; fi
            done
            exit 0
        fi
    else
        ready_streak=0
    fi
    sleep "$INTERVAL"
done
