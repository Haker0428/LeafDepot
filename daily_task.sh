#!/bin/bash
#
# LeafDepot 每日维护：拉取 WMS 库存 -> 重启全部服务
# 由 leafdepot-daily.timer 每天 04:00 触发；测试期可手动 sudo ./daily_task.sh 执行
#
# 设计约束：
#   1. 必须以 root 运行（systemctl restart 需要权限）；python 步骤用 runuser 降权执行，
#      保证 bins_data.xlsx / lms_*.log 属主仍是普通用户（否则 LMS 服务会 crash-loop）
#   2. 不硬编码用户名/路径：运行用户从项目根属主推导，conda python 从该用户家目录推导，
#      可直接部署到任意机器
#   3. 打印详尽自解释（远程排障只能靠日志）：写入 logs/daily_task_YYYYMMDD.log
#
set -u

# ---------- 0. root 检查 ----------
if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] 本脚本必须以 root 运行（sudo ./daily_task.sh 或由 systemd timer 触发）"
    exit 1
fi

# ---------- 1. 定位项目根（本脚本位于项目根目录） ----------
SCRIPT_SRC="$(readlink -f "$0")"
PROJECT_ROOT="$(dirname "$SCRIPT_SRC")"
LOG_DIR="$PROJECT_ROOT/logs"
FETCH_SCRIPT="$PROJECT_ROOT/services/sim/lms/fetch_wms_stock.py"
BINS_FILE="$PROJECT_ROOT/services/sim/lms/bins_data.xlsx"
mkdir -p "$LOG_DIR"

# ---------- 2. 推导运行用户与 conda python（root 的 $HOME 是 /root，禁用 $HOME 写法） ----------
RUN_USER="$(stat -c '%U' "$PROJECT_ROOT")"
RUN_HOME="$(getent passwd "$RUN_USER" 2>/dev/null | cut -d: -f6)"
PYTHON_BIN=""
if [ -n "$RUN_HOME" ]; then
    for _p in \
        "$RUN_HOME/miniconda3/envs/tobacco_env/bin/python" \
        "$RUN_HOME/anaconda3/envs/tobacco_env/bin/python" \
        "/opt/conda/envs/tobacco_env/bin/python"; do
        [ -x "$_p" ] && PYTHON_BIN="$_p" && break
    done
fi
if [ -z "$PYTHON_BIN" ] || [ ! -f "$FETCH_SCRIPT" ]; then
    echo "[ERROR] 环境推导失败: user=$RUN_USER home=$RUN_HOME python=$PYTHON_BIN"
    echo "[ERROR] 拉取脚本: $FETCH_SCRIPT"
    echo "[ERROR] 请确认 conda env tobacco_env 位置及项目目录属主"
    exit 1
fi

# ---------- 3. 自身日志（root 创建，0644，仅自用）+ 清理 30 天前旧日志 ----------
LOG_FILE="$LOG_DIR/daily_task_$(date +%Y%m%d).log"
find "$LOG_DIR" -name "daily_task_*.log" -mtime +30 -delete 2>/dev/null || true
touch "$LOG_FILE" && chmod 0644 "$LOG_FILE"
exec >> "$LOG_FILE" 2>&1

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
ok()   { log "[OK]   $*"; }
warn() { log "[WARN] $*"; }
fail() { log "[FAIL] $*"; }

# ---------- 4. 服务清单 ----------
SERVICES=(gateway worker lms rcs web)
declare -A PORTS=(
    [gateway]=8000
    [lms]=6000
    [rcs]=4001
    [web]=5173
)   # worker 是 Redis 消费者，无端口

port_up()   { ss -tln 2>/dev/null | grep -q ":$1 "; }
http_code() { curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:$1/" 2>/dev/null; }
svc_pid()   { systemctl show -p MainPID --value "leafdepot-$1" 2>/dev/null; }

# ================================================================
log "========================================================="
log "LeafDepot 每日维护开始"
log "========================================================="
log "主机:     $(hostname)  IP: $(hostname -I 2>/dev/null | tr -s ' ')"
log "项目:     $PROJECT_ROOT"
log "用户:     $RUN_USER (home: $RUN_HOME)"
log "Python:   $PYTHON_BIN"
log "is_sim:   $(python3 -c "import json;print(json.load(open('$PROJECT_ROOT/config.json')).get('is_sim','?'))" 2>/dev/null || echo '读取失败')"
if [ -f "$BINS_FILE" ]; then
    log "拉取前 bins_data.xlsx: $(stat -c '属主=%U 大小=%s字节' "$BINS_FILE"), 修改于 $(date -r "$BINS_FILE" '+%Y-%m-%d %H:%M:%S')"
else
    warn "bins_data.xlsx 不存在: $BINS_FILE"
fi

# ---------- 步骤一：拉取 WMS 库存（降权执行，重试2次，失败不阻断重启） ----------
FETCH_MAX=2
FETCH_RETRY_SLEEP=60
FETCH_RC=1
FETCH_DESC="失败(保留旧数据)"
log "----- 步骤 1/2: 拉取 WMS 库存 (最多尝试 $FETCH_MAX 次) -----"
for i in $(seq 1 "$FETCH_MAX"); do
    _t0=$(date +%s)
    log "WMS 同步第 $i/$FETCH_MAX 次尝试开始..."
    if runuser -u "$RUN_USER" -- "$PYTHON_BIN" "$FETCH_SCRIPT" --once; then
        FETCH_RC=0
        FETCH_DESC="成功"
        ok "WMS 同步成功 (耗时 $(( $(date +%s) - _t0 ))s)"
        break
    fi
    warn "WMS 同步第 $i/$FETCH_MAX 次尝试失败 (耗时 $(( $(date +%s) - _t0 ))s), 详情见 logs/lms_$(date +%Y%m%d).log"
    [ "$i" -lt "$FETCH_MAX" ] && { log "等待 ${FETCH_RETRY_SLEEP}s 后重试..."; sleep "$FETCH_RETRY_SLEEP"; }
done
[ "$FETCH_RC" -ne 0 ] && warn "WMS 拉取最终失败，bins_data.xlsx 保留旧数据，服务将带旧数据重启"
if [ -f "$BINS_FILE" ]; then
    _rows=$(runuser -u "$RUN_USER" -- "$PYTHON_BIN" -c "
from openpyxl import load_workbook
wb = load_workbook('$BINS_FILE', read_only=True)
print(wb.active.max_row - 1)" 2>/dev/null || echo "?")
    log "拉取后 bins_data.xlsx: $(stat -c '属主=%U 大小=%s字节' "$BINS_FILE"), 数据 $_rows 行, 修改于 $(date -r "$BINS_FILE" '+%Y-%m-%d %H:%M:%S')"
fi

# ---------- 步骤二：重启全部服务（root 直接 systemctl，无需 sudo） ----------
log "----- 步骤 2/2: 重启全部服务 -----"
for s in "${SERVICES[@]}"; do
    if systemctl restart "leafdepot-$s"; then
        log "restart leafdepot-$s: 已下发 (MainPID=$(svc_pid "$s"))"
    else
        fail "restart leafdepot-$s: 命令失败"
    fi
done

# ---------- 等待就绪（同时轮询全部服务，2s 一次，最长 60s） ----------
WAIT_MAX=60
log "等待服务就绪 (最长 ${WAIT_MAX}s)..."
elapsed=0
while [ "$elapsed" -lt "$WAIT_MAX" ]; do
    pending=""
    for s in "${SERVICES[@]}"; do
        st="$(systemctl is-active "leafdepot-$s" 2>/dev/null || true)"
        if [ "$st" != "active" ]; then
            pending="$pending $s(状态:$st)"
            continue
        fi
        p="${PORTS[$s]:-}"
        if [ -n "$p" ] && ! port_up "$p"; then
            pending="$pending $s(:$p)"
        fi
    done
    if [ -z "$pending" ]; then
        ok "全部服务就绪 (耗时 ${elapsed}s)"
        break
    fi
    log "[+${elapsed}s] 等待中:$pending"
    sleep 2
    elapsed=$((elapsed + 2))
done

# ---------- 逐服务详细核对 ----------
TODAY=$(date +%Y%m%d)
FAILED=0
log "----- 服务核对汇总 -----"
log "$(printf '%-10s %-10s %-9s %-9s %-8s %-10s %s' 服务 状态 PID 端口 HTTP 今日日志)"
for s in "${SERVICES[@]}"; do
    st="$(systemctl is-active "leafdepot-$s" 2>/dev/null || true)"
    pid="$(svc_pid "$s")"; [ "$pid" = "0" ] && pid="-"
    p="${PORTS[$s]:-}"
    if [ -n "$p" ]; then
        if port_up "$p"; then port_str=":$p 监听"; else port_str=":$p 未监听"; fi
        code="$(http_code "$p")"
        if [ -n "$code" ] && [ "$code" != "000" ]; then http_str="HTTP $code"; else http_str="无响应"; fi
    else
        port_str="-"; http_str="-"
    fi
    lf="$LOG_DIR/${s}_${TODAY}.log"
    if [ -f "$lf" ]; then log_str="$(du -h "$lf" | cut -f1)"; else log_str="不存在"; fi
    log "$(printf '%-10s %-10s %-9s %-9s %-8s %-10s %s' "$s" "$st" "$pid" "$port_str" "$http_str" "$log_str")"
    if [ "$st" != "active" ]; then
        FAILED=$((FAILED+1)); fail "$s 未运行 (状态: $st)"; continue
    fi
    if [ -n "$p" ] && ! port_up "$p"; then
        FAILED=$((FAILED+1)); fail "$s 状态 active 但端口 :$p 未监听"
    fi
done

# ---------- 收尾 ----------
log "========================================================="
if [ "$FETCH_RC" -ne 0 ]; then
    warn "WMS 拉取失败（不影响本次重启，详情见 logs/lms_${TODAY}.log）"
fi
if [ "$FAILED" -gt 0 ]; then
    fail "每日维护结束: ${FAILED} 个服务异常，详情见上方 [FAIL] 行"
    log "========================================================="
    exit 1
fi
log "每日维护结束: WMS 拉取${FETCH_DESC}，${#SERVICES[@]} 个服务全部正常"
log "========================================================="
exit 0
