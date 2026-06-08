#!/bin/bash
#
# LeafDepot 部署脚本（相对路径版）
# 在任意目录下运行：./install.sh
#
set -e

# ===== 自动检测项目根目录（脚本所在目录） =====
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo ""
echo "========================================"
echo "  LeafDepot 部署脚本"
echo "========================================"
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo ""

# ===== 检测 conda =====
CONDA_BIN=""
for p in \
    "$HOME/miniconda3/bin/conda" \
    "$HOME/miniconda3/condabin/conda" \
    "$HOME/anaconda3/bin/conda" \
    "$HOME/anaconda3/condabin/conda" \
    "/opt/conda/bin/conda" \
    "/opt/conda/condabin/conda" \
    "/usr/local/conda/bin/conda" \
    "/usr/local/conda/condabin/conda"; do
    if [ -x "$p" ]; then
        CONDA_BIN="$p"
        break
    fi
done

if [ -z "$CONDA_BIN" ]; then
    echo "[错误] 未找到 conda，请确保 miniconda 或 anaconda 已安装"
    echo "       或设置 CONDA_PREFIX 环境变量后重试："
    echo "       CONDA_PREFIX=/path/to/miniconda3 $0"
    exit 1
fi

CONDA_PREFIX="$(dirname "$(dirname "$CONDA_BIN")")"
echo "[INFO] Conda 路径: $CONDA_BIN"
echo "[INFO] Conda 前缀: $CONDA_PREFIX"

# ===== 检测 Redis CLI（用于状态检查） =====
REDIS_CLI=""
for p in \
    "$CONDA_PREFIX/envs/tobacco_env/bin/redis-cli" \
    "/opt/redis-7.4.0/bin/redis-cli" \
    "/opt/redis-7.0/bin/redis-cli" \
    "/usr/bin/redis-cli"; do
    if [ -x "$p" ]; then
        REDIS_CLI="$p"
        break
    fi
done
if [ -n "$REDIS_CLI" ]; then
    echo "[INFO] Redis CLI: $REDIS_CLI"
else
    echo "[WARN] 未找到 redis-cli，Redis 可能未安装"
fi

# ===== 检测 pnpm =====
PNPM_BIN=""
for p in \
    "pnpm" \
    "$HOME/.local/share/pnpm/pnpm" \
    "/usr/bin/pnpm" \
    "/usr/local/bin/pnpm" \
    "$(npm root -g 2>/dev/null)/pnpm"; do
    if [ -x "$p" ] 2>/dev/null; then
        PNPM_BIN="$p"
        break
    fi
done

if [ -z "$PNPM_BIN" ]; then
    echo "[错误] 未找到 pnpm，请先安装: npm install -g pnpm"
    exit 1
fi
echo "[INFO] pnpm 路径: $PNPM_BIN"

# 获取运行用户
RUN_USER=$(whoami)
RUN_GROUP=$(id -gn $RUN_USER)
echo "[INFO] 运行用户: $RUN_USER"

# ===== 路径变量 =====
CONDA_ENV_BIN="$CONDA_PREFIX/envs/tobacco_env/bin"
PYTHON_BIN="$CONDA_ENV_BIN/python"
UVICORN_BIN="$CONDA_ENV_BIN/uvicorn"
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

SYSTEMD_DIR="$PROJECT_ROOT/systemd"
mkdir -p "$SYSTEMD_DIR"

echo "[INFO] 日志目录: $LOG_DIR"
echo ""

# ===== 生成 systemd unit 文件 =====
echo "[INFO] 生成 systemd unit 文件..."

# ===== Redis 依赖 =====
# Python 代码中 Redis 连接是懒加载自动重连，不需要 systemd 强依赖
REDIS_UNIT_DEPS="After=network.target"

LOG_WRAPPER="$PROJECT_ROOT/log_wrapper.sh"

# ========== gateway ==========
cat > "$SYSTEMD_DIR/leafdepot-gateway.service" << EOF
[Unit]
Description=LeafDepot Gateway API Service
$REDIS_UNIT_DEPS

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$PROJECT_ROOT/services/api
Environment="PYTHONPATH=$PROJECT_ROOT"
ExecStart=$LOG_WRAPPER gateway $PYTHON_BIN -m uvicorn gateway:app --host 0.0.0.0 --port 8000 --no-access-log
Restart=always
RestartSec=10
EOF

cat > "$SYSTEMD_DIR/leafdepot-gateway.timer" << EOF
[Unit]
Description=LeafDepot Gateway 每日凌晨 4 点重启定时器

[Timer]
OnCalendar=*-*-* 04:00:00
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
EOF

# ========== worker ==========
cat > "$SYSTEMD_DIR/leafdepot-worker.service" << EOF
[Unit]
Description=LeafDepot Inventory Worker Service
$REDIS_UNIT_DEPS

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

cat > "$SYSTEMD_DIR/leafdepot-worker.timer" << EOF
[Unit]
Description=LeafDepot Worker 每日凌晨 4 点重启定时器

[Timer]
OnCalendar=*-*-* 04:00:00
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
EOF

# ========== lms ==========
cat > "$SYSTEMD_DIR/leafdepot-lms.service" << EOF
[Unit]
Description=LeafDepot LMS Simulator Service
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

cat > "$SYSTEMD_DIR/leafdepot-lms.timer" << EOF
[Unit]
Description=LeafDepot LMS 每日凌晨 4 点重启定时器

[Timer]
OnCalendar=*-*-* 04:00:00
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
EOF

# ========== rcs ==========
cat > "$SYSTEMD_DIR/leafdepot-rcs.service" << EOF
[Unit]
Description=LeafDepot RCS Simulator Service
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

cat > "$SYSTEMD_DIR/leafdepot-rcs.timer" << EOF
[Unit]
Description=LeafDepot RCS 每日凌晨 4 点重启定时器

[Timer]
OnCalendar=*-*-* 04:00:00
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
EOF

# ========== web ==========
# 自动检测 node 路径
NODE_BIN=""
for p in \
    "/root/LDUI/thirdparty/node-v24.11.1-linux-x64/bin" \
    "$HOME/LDUI/thirdparty/node-v24.11.1-linux-x64/bin" \
    "$HOME/thirdparty/node-v24.11.1-linux-x64/bin" \
    "$(dirname "$(dirname "$(which node 2>/dev/null)")")/bin"; do
    if [ -x "$p/node" ]; then
        NODE_BIN="$p"
        break
    fi
done
if [ -z "$NODE_BIN" ]; then
    echo "[错误] 未找到 node，请确保 Node.js 已安装"
    exit 1
fi
echo "[INFO] Node 路径: $NODE_BIN"
NODE_PATH="${NODE_BIN}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
cat > "$SYSTEMD_DIR/leafdepot-web.service" << EOF
[Unit]
Description=LeafDepot Web Frontend Service
After=network.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$PROJECT_ROOT/web
Environment="PATH=$NODE_PATH"
ExecStart=$LOG_WRAPPER web $PNPM_BIN dev
Restart=always
RestartSec=10
EOF

cat > "$SYSTEMD_DIR/leafdepot-web.timer" << EOF
[Unit]
Description=LeafDepot Web 每日凌晨 4 点重启定时器

[Timer]
OnCalendar=*-*-* 04:00:00
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
EOF

echo "[INFO] Unit 文件生成完成"

# ===== 安装（需要 sudo） =====
echo ""
echo "[INFO] 开始安装 systemd 服务（需要 sudo 权限）..."

if [ -n "$REDIS_CLI" ] && $REDIS_CLI ping > /dev/null 2>&1; then
    echo "[INFO] Redis 已在运行"
else
    echo "[WARN] Redis 未运行，请确保 redis-server 已启动"
fi

sudo cp "$SYSTEMD_DIR"/*.service /etc/systemd/system/
sudo cp "$SYSTEMD_DIR"/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
echo "[INFO] systemd 重载完成"

echo ""
echo "[INFO] 启用并启动服务..."

sudo systemctl enable --now leafdepot-gateway leafdepot-gateway.timer
echo "[OK]   gateway + timer"

sudo systemctl enable --now leafdepot-worker leafdepot-worker.timer
echo "[OK]   worker + timer"

sudo systemctl enable --now leafdepot-lms leafdepot-lms.timer
echo "[OK]   lms + timer"

sudo systemctl enable --now leafdepot-rcs leafdepot-rcs.timer
echo "[OK]   rcs + timer"

sudo systemctl enable --now leafdepot-web leafdepot-web.timer
echo "[OK]   web + timer"

echo ""
echo "========================================"
echo "  部署完成！"
echo "========================================"
echo ""
echo "查看服务状态:"
echo "  sudo systemctl status leafdepot-gateway"
echo "  sudo systemctl status leafdepot-worker"
echo "  sudo systemctl status leafdepot-lms"
echo "  sudo systemctl status leafdepot-rcs"
echo "  sudo systemctl status leafdepot-web"
echo ""
echo "查看定时器:"
echo "  sudo systemctl list-timers | grep leafdepot"
echo ""
echo "日志文件: $LOG_DIR/"
echo ""
