#!/bin/bash
#
# LeafDepot 一键部署脚本
# 用法:
#   ./deploy.sh            # 完整部署
#   ./deploy.sh restart    # 仅重启所有服务
#   ./deploy.sh cron       # 设置每日维护timer（每天凌晨4点：拉取WMS数据+重启全部服务）
#   ./deploy.sh cron-del   # 删除每日维护timer
#
# 完整部署包含：
#   1. 清理 __pycache__ 和 .pyc（强制加载新代码）
#   2. 杀掉旧的 gateway 进程（释放端口）
#   3. 重启所有 systemd 服务
#   4. 清理 Redis 测试数据（可选）
#   5. 查看服务状态
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ===== 一键重启所有服务 =====
restart_all() {
    echo ""
    echo "========================================"
    echo "  LeafDepot 重启所有服务"
    echo "========================================"
    echo ""

    info "清理 __pycache__..."
    find "$PROJECT_ROOT/services" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT/services" -name "*.pyc" -delete 2>/dev/null || true

    info "重启服务..."
    sudo systemctl restart \
        leafdepot-gateway \
        leafdepot-worker \
        leafdepot-lms \
        leafdepot-rcs \
        leafdepot-web || true

    sleep 4

    echo ""
    info "========================================"
    info "  服务状态"
    info "========================================"

    local logdate
    logdate=$(date +%Y%m%d)

    for svc in gateway worker lms rcs web; do
        local unit="leafdepot-${svc}.service"
        local status
        status=$(sudo systemctl is-active "$unit" 2>/dev/null || echo "unknown")
        if [ "$status" = "active" ]; then
            info "${svc}: ✅ 运行中"
        else
            error "${svc}: ❌ $status"
        fi
    done

    if [ -f "$PROJECT_ROOT/logs/gateway_${logdate}.log" ]; then
        echo ""
        info "最新日志 (gateway_${logdate}.log):"
        tail -5 "$PROJECT_ROOT/logs/gateway_${logdate}.log" | sed 's/^/    /'
    fi

    echo ""
}

# PROJECT_ROOT 和颜色函数必须在最前面定义，cron/restart 命令会直接调用
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# 读取 is_sim 配置（全局变量，所有函数共享）
IS_SIM=true
if [ -f "$PROJECT_ROOT/config.json" ]; then
    IS_SIM=$(python3 -c "import json; print(json.load(open('$PROJECT_ROOT/config.json')).get('is_sim', True))" 2>/dev/null || echo "true")
fi

# ===== 每日维护 timer（拉WMS数据 + 重启全部服务） =====

# 清理遗留的定时机制（幂等，可重复调用）：
#   1. crontab 里两条旧重启条目（manage.sh 死条目 + deploy.sh restart 条目；保留 NVIDIA 条目）
#   2. 5 个旧的已安装但从未正常工作的 timer（/etc 和 repo systemd/ 两处）
#   3. wms-sync 常驻服务残留（由 daily task 每日拉取取代）
cleanup_legacy_scheduling() {
    info "清理遗留定时机制..."

    # crontab：精确删除旧条目（模式不匹配 NVIDIA updater 行）
    crontab -l 2>/dev/null \
        | grep -vE 'bash manage\.sh restart all|LeafDepot/deploy\.sh restart' \
        | crontab - 2>/dev/null || true

    # 5 个旧 timer：停用 + 删除（显式列出，避免 glob 误伤 daily.timer）
    local old_timers="leafdepot-gateway.timer leafdepot-worker.timer leafdepot-lms.timer leafdepot-rcs.timer leafdepot-web.timer"
    sudo systemctl disable --now $old_timers 2>/dev/null || true
    sudo rm -f /etc/systemd/system/leafdepot-gateway.timer /etc/systemd/system/leafdepot-worker.timer \
        /etc/systemd/system/leafdepot-lms.timer /etc/systemd/system/leafdepot-rcs.timer /etc/systemd/system/leafdepot-web.timer
    rm -f "$PROJECT_ROOT/systemd/leafdepot-gateway.timer" "$PROJECT_ROOT/systemd/leafdepot-worker.timer" \
        "$PROJECT_ROOT/systemd/leafdepot-lms.timer" "$PROJECT_ROOT/systemd/leafdepot-rcs.timer" \
        "$PROJECT_ROOT/systemd/leafdepot-web.timer"

    # wms-sync 残留（防御性：跑过旧版 deploy 的机器）
    sudo systemctl disable --now leafdepot-wms-sync 2>/dev/null || true
    sudo rm -f /etc/systemd/system/leafdepot-wms-sync.service

    sudo systemctl daemon-reload
    info "遗留清理完成"
}

# 设置每日维护 timer（生成 daily.service/.timer 并启用）
setup_daily_timer() {
    echo ""
    echo "========================================"
    echo "  设置 LeafDepot 每日维护 timer"
    echo "  每天 04:00: 拉取 WMS 库存 + 重启全部服务"
    echo "========================================"
    echo ""

    cleanup_legacy_scheduling

    local systemd_dir="$PROJECT_ROOT/systemd"
    mkdir -p "$systemd_dir"
    chmod +x "$PROJECT_ROOT/daily_task.sh" "$PROJECT_ROOT/check_services.sh" 2>/dev/null || true

    # 每日维护 oneshot 服务（root 运行；python 步骤在 daily_task.sh 内部 runuser 降权）
    cat > "$systemd_dir/leafdepot-daily.service" << EOF
[Unit]
Description=LeafDepot Daily Maintenance (WMS fetch + services restart)
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
ExecStart=$PROJECT_ROOT/daily_task.sh
TimeoutStartSec=600
EOF

    # 每天 04:00 触发；Persistent=true 关机错过则开机补跑（补跑时随机延迟不生效）
    cat > "$systemd_dir/leafdepot-daily.timer" << EOF
[Unit]
Description=LeafDepot Daily Maintenance Timer (04:00)

[Timer]
OnCalendar=*-*-*  04:00:00
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
EOF

    info "安装 timer（需要 sudo）..."
    sudo cp "$systemd_dir/leafdepot-daily.service" "$systemd_dir/leafdepot-daily.timer" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now leafdepot-daily.timer

    echo ""
    info "每日维护 timer 已启用："
    systemctl list-timers leafdepot-daily.timer --no-pager 2>/dev/null | sed 's/^/    /' || true
    # NEXT 必须有值（旧 timer 就僵死在 NEXT 为空）；为空则重排程一次
    local next
    next=$(systemctl show -p NextElapseUSecRealtime --value leafdepot-daily.timer 2>/dev/null || true)
    if [ -z "$next" ] || [ "$next" = "n/a" ]; then
        warn "timer NEXT 为空（疑似僵死），尝试重新排程..."
        sudo systemctl restart leafdepot-daily.timer || true
        next=$(systemctl show -p NextElapseUSecRealtime --value leafdepot-daily.timer 2>/dev/null || true)
        if [ -z "$next" ] || [ "$next" = "n/a" ]; then
            warn "仍未排程，请手动检查: systemctl list-timers leafdepot-daily.timer"
        else
            info "重新排程成功，NEXT: $next"
        fi
    fi
    local cron_out
    cron_out=$(crontab -l 2>/dev/null || true)
    if [ -n "$cron_out" ]; then
        info "当前 crontab（应只剩非 LeafDepot 条目，如 NVIDIA updater）:"
        echo "$cron_out" | sed 's/^/    /'
    else
        info "当前 crontab 为空"
    fi
}

# 删除每日维护 timer
remove_daily_timer() {
    info "删除每日维护 timer..."
    sudo systemctl disable --now leafdepot-daily.timer 2>/dev/null || true
    sudo rm -f /etc/systemd/system/leafdepot-daily.timer /etc/systemd/system/leafdepot-daily.service
    rm -f "$PROJECT_ROOT/systemd/leafdepot-daily.timer" "$PROJECT_ROOT/systemd/leafdepot-daily.service"
    sudo systemctl daemon-reload
    sudo systemctl reset-failed leafdepot-daily.service 2>/dev/null || true
    info "每日维护 timer 已删除"
}

# 根据参数决定执行哪个命令
CMD="${1:-deploy}"
if [ "$CMD" = "restart" ]; then
    restart_all
    exit 0
fi
if [ "$CMD" = "cron" ]; then
    setup_daily_timer
    exit 0
fi
if [ "$CMD" = "cron-del" ]; then
    remove_daily_timer
    exit 0
fi
# 默认执行完整部署

echo ""
echo "========================================"
echo "  LeafDepot 一键部署"
echo "========================================"
echo ""

# ===== 1. 清理 Python 缓存 =====
info "清理 __pycache__ 和 .pyc..."
find "$PROJECT_ROOT/services" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT/services" -name "*.pyc" -delete 2>/dev/null || true
info "缓存清理完成"

# ===== 2. 检测 conda =====
CONDA_BIN=""
for p in \
    "$HOME/miniconda3/bin/conda" \
    "$HOME/miniconda3/condabin/conda" \
    "$HOME/anaconda3/bin/conda" \
    "/opt/conda/bin/conda" \
    "/opt/conda/condabin/conda"; do
    [ -x "$p" ] && CONDA_BIN="$p" && break
done
if [ -z "$CONDA_BIN" ]; then
    error "未找到 conda，退出"
    exit 1
fi
CONDA_ENV_BIN="$HOME/miniconda3/envs/tobacco_env/bin"
PYTHON_BIN="$CONDA_ENV_BIN/python"
UVICORN_BIN="$CONDA_ENV_BIN/uvicorn"

# ===== 3. 检测端口占用，杀掉旧 gateway =====
info "检查 8000 端口占用..."
GATEWAY_PID=$(lsof -ti :8000 2>/dev/null || true)
if [ -n "$GATEWAY_PID" ]; then
    warn "8000 端口被 PID $GATEWAY_PID 占用，强制杀掉..."
    kill -9 $GATEWAY_PID 2>/dev/null || true
    sleep 2
    REMAIN=$(lsof -ti :8000 2>/dev/null || true)
    if [ -n "$REMAIN" ]; then
        error "无法释放 8000 端口，当前占用: $REMAIN"
        exit 1
    fi
    info "端口已释放"
else
    info "8000 端口空闲"
fi

# ===== 4. 确保运维脚本有执行权限 =====
chmod +x "$PROJECT_ROOT/log_wrapper.sh" "$PROJECT_ROOT/daily_task.sh" "$PROJECT_ROOT/check_services.sh"

# ===== 5. 检测 Redis =====
REDIS_CLI="$CONDA_ENV_BIN/redis-cli"
REDIS_OK=false
if [ -x "$REDIS_CLI" ] && $REDIS_CLI ping > /dev/null 2>&1; then
    info "Redis 运行正常"
    REDIS_OK=true
else
    warn "Redis 未运行，请手动启动: redis-server &"
fi

# ===== 6. 生成 systemd unit 文件 =====
info "生成 systemd unit 文件..."
SYSTEMD_DIR="$PROJECT_ROOT/systemd"
mkdir -p "$SYSTEMD_DIR"
LOG_WRAPPER="$PROJECT_ROOT/log_wrapper.sh"
RUN_USER=$(whoami)
RUN_GROUP=$(id -gn $RUN_USER)

# gateway
cat > "$SYSTEMD_DIR/leafdepot-gateway.service" << EOF
[Unit]
Description=LeafDepot Gateway API Service
After=network.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$PROJECT_ROOT
Environment="PYTHONPATH=$PROJECT_ROOT"
ExecStart=$LOG_WRAPPER gateway $PYTHON_BIN -m uvicorn services.api.gateway:app --host 0.0.0.0 --port 8000 --no-access-log
Restart=always
RestartSec=10
EOF

# worker
cat > "$SYSTEMD_DIR/leafdepot-worker.service" << EOF
[Unit]
Description=LeafDepot Inventory Worker Service
After=network.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$PROJECT_ROOT
Environment="PYTHONPATH=$PROJECT_ROOT"
ExecStart=$LOG_WRAPPER worker $PYTHON_BIN $PROJECT_ROOT/services/worker/inventory_worker.py
Restart=always
RestartSec=10
EOF

# lms sim
cat > "$SYSTEMD_DIR/leafdepot-lms.service" << EOF
[Unit]
Description=LeafDepot LMS Simulator
After=network.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$PROJECT_ROOT/services/sim/lms
Environment="PYTHONPATH=$PROJECT_ROOT"
ExecStart=$LOG_WRAPPER lms $PYTHON_BIN -m uvicorn sim_lms_server:app --host 0.0.0.0 --port 6000 --no-access-log
Restart=always
RestartSec=10
EOF

# rcs sim
cat > "$SYSTEMD_DIR/leafdepot-rcs.service" << EOF
[Unit]
Description=LeafDepot RCS Simulator
After=network.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$PROJECT_ROOT/services/sim/rcs
Environment="PYTHONPATH=$PROJECT_ROOT"
ExecStart=$LOG_WRAPPER rcs $PYTHON_BIN -m uvicorn sim_rcs_server:app --host 0.0.0.0 --port 4001 --no-access-log
Restart=always
RestartSec=10
EOF

# daily 每日维护 oneshot（root 运行；python 步骤在 daily_task.sh 内部 runuser 降权）
cat > "$SYSTEMD_DIR/leafdepot-daily.service" << EOF
[Unit]
Description=LeafDepot Daily Maintenance (WMS fetch + services restart)
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
ExecStart=$PROJECT_ROOT/daily_task.sh
TimeoutStartSec=600
EOF

# daily 每日维护 timer（04:00；Persistent 关机错过则开机补跑）
cat > "$SYSTEMD_DIR/leafdepot-daily.timer" << EOF
[Unit]
Description=LeafDepot Daily Maintenance Timer (04:00)

[Timer]
OnCalendar=*-*-*  04:00:00
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
EOF

info "unit 文件生成完成"

# ===== 6.5 部署时立即同步一次 WMS 数据 =====
info "部署时立即同步一次 WMS 数据 (is_sim=$IS_SIM)..."
$PYTHON_BIN "$PROJECT_ROOT/services/sim/lms/fetch_wms_stock.py" --once || warn "WMS 首次同步失败，请检查日志 logs/lms_YYYYMMDD.log"
info "WMS 首次同步完成"

# ===== 7. 安装并重启服务 =====
info "安装 systemd 服务（需要 sudo）..."
sudo cp "$SYSTEMD_DIR"/leafdepot-*.service "$SYSTEMD_DIR"/leafdepot-*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# 清理遗留定时机制 + 启用每日维护 timer
cleanup_legacy_scheduling
info "启用每日维护 timer（每天 04:00 拉取 WMS 数据 + 重启全部服务）..."
sudo systemctl enable --now leafdepot-daily.timer 2>/dev/null || warn "daily timer 启用失败，可用 ./deploy.sh cron 单独设置"

# 只启动 gateway 和 worker（lms/rcs/web 按需手动启）
info "重启 gateway..."
sudo systemctl restart leafdepot-gateway

info "重启 worker..."
sudo systemctl restart leafdepot-worker

# ===== 8. 等待启动完成 =====
sleep 4

# ===== 9. 验证 =====
info ""
info "========================================"
info "  部署结果"
info "========================================"

# gateway
if lsof -ti :8000 > /dev/null 2>&1; then
    G_PID=$(lsof -ti :8000)
    info "gateway: ✅ 运行中 (PID=$G_PID)"
else
    error "gateway: ❌ 启动失败！查看日志: tail -50 logs/gateway_$(date +%Y%m%d).log"
fi

# worker
W_STATUS=$(sudo systemctl is-active leafdepot-worker 2>/dev/null || echo "unknown")
if [ "$W_STATUS" = "active" ]; then
    W_PID=$(ps aux | grep "inventory_worker" | grep -v grep | awk '{print $2}' | head -1)
    info "worker:    ✅ 运行中 (PID=$W_PID)"
else
    warn "worker:    ⚠️  $W_STATUS（可能正常，Redis 未连接时 worker 会空转）"
fi

# redis
if $REDIS_OK; then
    info "redis:     ✅ 运行中"
else
    warn "redis:     ⚠️  未运行"
fi

# 日志文件
LOGDATE=$(date +%Y%m%d)
if [ -f "$PROJECT_ROOT/logs/gateway_${LOGDATE}.log" ]; then
    info "日志文件:  ✅ logs/gateway_${LOGDATE}.log"
    tail -3 "$PROJECT_ROOT/logs/gateway_${LOGDATE}.log" | sed 's/^/          /'
else
    warn "日志文件:  ⚠️  未找到 logs/gateway_${LOGDATE}.log"
fi

echo ""
info "常用命令："
echo "  查看 gateway 日志: tail -f logs/gateway_${LOGDATE}.log"
echo "  查看服务状态:      sudo systemctl status leafdepot-gateway"
echo "  重启 gateway:      sudo systemctl restart leafdepot-gateway"
echo "  查看 journal:       sudo journalctl -u leafdepot-gateway -f"
echo ""
