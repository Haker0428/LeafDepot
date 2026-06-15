#!/bin/bash
#
# LeafDepot 一键部署脚本
# 用法:
#   ./deploy.sh            # 完整部署
#   ./deploy.sh restart    # 仅重启所有服务
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

    info "重启 5 个服务..."
    sudo systemctl restart \
        leafdepot-gateway \
        leafdepot-worker \
        leafdepot-lms \
        leafdepot-rcs \
        leafdepot-web

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

# 根据参数决定执行哪个命令
CMD="${1:-deploy}"
if [ "$CMD" = "restart" ]; then
    restart_all
    exit 0
fi
# 默认执行完整部署
PROJECT_ROOT="$SCRIPT_DIR"
cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; }

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

# ===== 4. 确保 log_wrapper.sh 有执行权限 =====
chmod +x "$PROJECT_ROOT/log_wrapper.sh"

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

info "unit 文件生成完成"

# ===== 7. 安装并重启服务 =====
info "安装 systemd 服务（需要 sudo）..."
sudo cp "$SYSTEMD_DIR"/leafdepot-*.service /etc/systemd/system/
sudo systemctl daemon-reload

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
