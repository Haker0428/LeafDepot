#!/bin/bash
#
# LeafDepot systemd 安装脚本
# 用法: ./setup_systemd.sh [项目根目录] [conda前缀路径]
#
# 示例:
#   ./setup_systemd.sh /home/ubuntu/code/LeafDepot /home/ubuntu/miniconda3
#   ./setup_systemd.sh                           # 交互式输入
#

set -e

# ===== 自动检测或使用参数 =====
PROJECT_ROOT="${1:-}"
CONDA_PREFIX="${2:-}"

if [ -z "$PROJECT_ROOT" ] || [ -z "$CONDA_PREFIX" ]; then
    echo ""
    echo "========================================"
    echo "  LeafDepot systemd 安装向导"
    echo "========================================"
    echo ""

    if [ -z "$PROJECT_ROOT" ]; then
        read -p "请输入项目根目录（如 /home/ubuntu/code/LeafDepot）: " PROJECT_ROOT
    fi
    if [ -z "$CONDA_PREFIX" ]; then
        read -p "请输入 conda 前缀（如 /home/ubuntu/miniconda3）: " CONDA_PREFIX
    fi
fi

# 去掉末尾斜杠
PROJECT_ROOT="${PROJECT_ROOT%/}"
CONDA_PREFIX="${CONDA_PREFIX%/}"

echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "Conda 前缀: $CONDA_PREFIX"
echo ""

# 校验
if [ ! -d "$PROJECT_ROOT" ]; then
    echo "[错误] 项目根目录不存在: $PROJECT_ROOT"
    exit 1
fi
if [ ! -d "$CONDA_PREFIX" ]; then
    echo "[错误] Conda 前缀目录不存在: $CONDA_PREFIX"
    exit 1
fi

CONDA_BIN="$CONDA_PREFIX/bin/conda"
if [ ! -x "$CONDA_BIN" ]; then
    echo "[错误] Conda 不可执行: $CONDA_BIN"
    exit 1
fi

# 获取运行本脚本的用户
RUN_USER=$(whoami)
echo "[INFO] 当前用户: $RUN_USER"
echo "[INFO] 当前用户组: $(id -gn $RUN_USER)"

# ===== 检测 pnpm =====
PNPM_BIN=""
for p in pnpm "/usr/bin/pnpm" "/usr/local/bin/pnpm" "$HOME/.local/share/pnpm/pnpm"; do
    if [ -x "$p" ]; then
        PNPM_BIN="$p"
        break
    fi
done

if [ -z "$PNPM_BIN" ]; then
    echo "[错误] 未找到 pnpm，请先安装: npm install -g pnpm"
    exit 1
fi
echo "[INFO] pnpm 路径: $PNPM_BIN"

# ===== 生成 systemd unit 文件 =====
SYSTEMD_DIR="$PROJECT_ROOT/systemd"
mkdir -p "$SYSTEMD_DIR"

CONDA_ENV_BIN="$CONDA_PREFIX/envs/tobacco_env/bin"
PYTHON_BIN="$CONDA_ENV_BIN/python"
UVICORN_BIN="$CONDA_ENV_BIN/uvicorn"
REDIS_CLI="$CONDA_ENV_BIN/redis-cli"

LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

echo "[INFO] 生成 systemd unit 文件..."

# ========== gateway ==========
cat > "$SYSTEMD_DIR/leafdepot-gateway.service" << EOF
[Unit]
Description=LeafDepot Gateway API Service
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=$RUN_USER
Group=$(id -gn $RUN_USER)
WorkingDirectory=$PROJECT_ROOT
Environment="PYTHONPATH=$PROJECT_ROOT"
ExecStart=$UVICORN_BIN gateway:app --host 0.0.0.0 --port 8000
StandardOutput=append:$LOG_DIR/gateway_systemd.log
StandardError=append:$LOG_DIR/gateway_systemd.log
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
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=$RUN_USER
Group=$(id -gn $RUN_USER)
WorkingDirectory=$PROJECT_ROOT
Environment="PYTHONPATH=$PROJECT_ROOT"
ExecStart=$PYTHON_BIN $PROJECT_ROOT/services/worker/inventory_worker.py
StandardOutput=append:$LOG_DIR/worker_systemd.log
StandardError=append:$LOG_DIR/worker_systemd.log
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
Group=$(id -gn $RUN_USER)
WorkingDirectory=$PROJECT_ROOT/services/sim/lms
Environment="PYTHONPATH=$PROJECT_ROOT"
ExecStart=$UVICORN_BIN sim_lms_server:app --host 0.0.0.0 --port 6000
StandardOutput=append:$LOG_DIR/lms_systemd.log
StandardError=append:$LOG_DIR/lms_systemd.log
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
Group=$(id -gn $RUN_USER)
WorkingDirectory=$PROJECT_ROOT/services/sim/rcs
Environment="PYTHONPATH=$PROJECT_ROOT"
ExecStart=$UVICORN_BIN sim_rcs_server:app --host 0.0.0.0 --port 4001
StandardOutput=append:$LOG_DIR/rcs_systemd.log
StandardError=append:$LOG_DIR/rcs_systemd.log
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
cat > "$SYSTEMD_DIR/leafdepot-web.service" << EOF
[Unit]
Description=LeafDepot Web Frontend Service
After=network.target

[Service]
Type=simple
User=$RUN_USER
Group=$(id -gn $RUN_USER)
WorkingDirectory=$PROJECT_ROOT/web
ExecStart=$PNPM_BIN dev
StandardOutput=append:$LOG_DIR/web_systemd.log
StandardError=append:$LOG_DIR/web_systemd.log
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

echo "[INFO] Unit 文件生成完成: $SYSTEMD_DIR"

# ===== 安装（需要 sudo） =====
echo ""
echo "[INFO] 开始安装 systemd 服务（需要 sudo 权限）..."

# 检查 redis 是否运行
if $REDIS_CLI ping > /dev/null 2>&1; then
    echo "[INFO] Redis 已在运行"
else
    echo "[WARN] Redis 未运行，请确保 redis-server 已启动（systemd 或手动）"
fi

# 复制 unit 文件
sudo cp "$SYSTEMD_DIR"/*.service /etc/systemd/system/
sudo cp "$SYSTEMD_DIR"/*.timer /etc/systemd/system/

# 重载 systemd
sudo systemctl daemon-reload
echo "[INFO] systemd 重载完成"

# 启用并启动（按依赖顺序）
echo ""
echo "[INFO] 启用并启动服务..."

sudo systemctl enable --now leafdepot-gateway leafdepot-gateway.timer
echo "[OK]   gateway + timer 已启用"

sudo systemctl enable --now leafdepot-worker leafdepot-worker.timer
echo "[OK]   worker + timer 已启用"

sudo systemctl enable --now leafdepot-lms leafdepot-lms.timer
echo "[OK]   lms + timer 已启用"

sudo systemctl enable --now leafdepot-rcs leafdepot-rcs.timer
echo "[OK]   rcs + timer 已启用"

sudo systemctl enable --now leafdepot-web leafdepot-web.timer
echo "[OK]   web + timer 已启用"

echo ""
echo "========================================"
echo "  安装完成！查看服务状态："
echo "========================================"
echo ""
echo "  sudo systemctl status leafdepot-gateway"
echo "  sudo systemctl status leafdepot-worker"
echo "  sudo systemctl status leafdepot-lms"
echo "  sudo systemctl status leafdepot-rcs"
echo "  sudo systemctl status leafdepot-web"
echo ""
echo "  查看定时器下次触发时间："
echo "  sudo systemctl list-timers | grep leafdepot"
echo ""
echo "  日志文件：$LOG_DIR/"
echo ""
