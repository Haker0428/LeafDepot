#!/bin/bash
#
# Redis 7.4.0 离线安装脚本
# 用法: ./install_redis.sh
#
# 前置依赖（需要联网安装）:
#   sudo apt install build-essential libevent-dev tcl
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$SCRIPT_DIR/redis_pkg"
TARBALL="$PKG_DIR/redis-7.4.0.tar.gz"
INSTALL_PREFIX="/opt/redis-7.4.0"
RUN_USER=$(whoami)

echo ""
echo "========================================"
echo "  Redis 7.4.0 离线安装脚本"
echo "========================================"
echo ""
echo "安装路径: $INSTALL_PREFIX"
echo "运行用户: $RUN_USER"
echo ""

# ===== 检查离线包 =====
if [ ! -f "$TARBALL" ]; then
    echo "[错误] 找不到离线包: $TARBALL"
    echo "        请确保 redis_pkg/redis-7.4.0.tar.gz 存在"
    exit 1
fi
echo "[INFO] 找到离线包: $TARBALL"

# ===== 编译并安装 =====
build_redis() {
    echo "[INFO] 解压 Redis 源码..."
    mkdir -p /tmp/redis-build
    tar xzf "$TARBALL" -C /tmp/redis-build

    cd /tmp/redis-build/redis-7.4.0

    echo "[INFO] 编译 Redis（需要 build-essential）..."
    make -j$(nproc)

    echo "[INFO] 安装到 $INSTALL_PREFIX..."
    sudo mkdir -p "$INSTALL_PREFIX"
    sudo make PREFIX="$INSTALL_PREFIX" install

    echo "[INFO] 清理编译临时文件..."
    cd /
    rm -rf /tmp/redis-build

    echo "[OK] Redis 安装完成"
}

# ===== 配置 =====
configure_redis() {
    echo "[INFO] 生成配置文件..."

    sudo mkdir -p "$INSTALL_PREFIX/etc"
    sudo mkdir -p "$INSTALL_PREFIX/data"
    sudo mkdir -p "$INSTALL_PREFIX/logs"
    sudo chown -R $RUN_USER:$RUN_USER "$INSTALL_PREFIX"

    cat > /tmp/redis.conf << EOF
# Redis 7.4.0 配置
bind 0.0.0.0
port 6379
protected-mode no
daemonize yes
pidfile $INSTALL_PREFIX/redis.pid
loglevel notice
logfile $INSTALL_PREFIX/logs/redis.log
databases 16
dir $INSTALL_PREFIX/data
maxmemory 512mb
maxmemory-policy allkeys-lru
save ""
appendonly no
EOF
    sudo cp /tmp/redis.conf "$INSTALL_PREFIX/etc/redis.conf"
    sudo chown $RUN_USER:$RUN_USER "$INSTALL_PREFIX/etc/redis.conf"

    echo "[INFO] 配置文件: $INSTALL_PREFIX/etc/redis.conf"
}

# ===== systemd 服务 =====
install_systemd() {
    echo "[INFO] 注册 systemd 服务..."

    local REDIS_SERVER="$INSTALL_PREFIX/bin/redis-server"

    cat > /tmp/redis-server.service << EOF
[Unit]
Description=Redis 7.4.0 Service
After=network.target

[Service]
Type=simple
User=$RUN_USER
Group=$(id -gn $RUN_USER)
WorkingDirectory=$INSTALL_PREFIX
ExecStart=$REDIS_SERVER $INSTALL_PREFIX/etc/redis.conf
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_PREFIX/logs/redis_stdout.log
StandardError=append:$INSTALL_PREFIX/logs/redis_stderr.log

[Install]
WantedBy=multi-user.target
EOF

    sudo cp /tmp/redis-server.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now redis-server
    echo "[OK] Redis 服务已启动"
}

# ===== 验证 =====
verify() {
    echo ""
    echo "[INFO] 验证安装..."
    sleep 1
    if $INSTALL_PREFIX/bin/redis-cli ping 2>/dev/null | grep -q PONG; then
        echo "[OK] Redis 运行正常 (PONG)"
    else
        echo "[WARN] Redis 未响应，请检查日志:"
        echo "  cat $INSTALL_PREFIX/logs/redis.log"
    fi

    echo ""
    echo "[INFO] Redis 版本:"
    $INSTALL_PREFIX/bin/redis-cli INFO server 2>/dev/null | grep redis_version
}

# ===== 主流程 =====
echo "[INFO] 前置检查..."
MISSING=""
for cmd in make gcc; do
    if ! command -v $cmd &>/dev/null; then
        MISSING="$MISSING $cmd"
    fi
done
if [ -n "$MISSING" ]; then
    echo "[错误] 缺少编译工具:$MISSING"
    echo "       请先联网安装:"
    echo "       sudo apt install build-essential"
    exit 1
fi

build_redis
configure_redis
install_systemd
verify

echo ""
echo "========================================"
echo "  Redis 7.4.0 安装完成!"
echo "========================================"
echo ""
echo "服务管理:"
echo "  sudo systemctl start   redis-server   # 启动"
echo "  sudo systemctl stop    redis-server   # 停止"
echo "  sudo systemctl restart redis-server   # 重启"
echo "  sudo systemctl status  redis-server   # 状态"
echo ""
echo "命令行:"
echo "  $INSTALL_PREFIX/bin/redis-cli"
echo ""
echo "配置: $INSTALL_PREFIX/etc/redis.conf"
echo "日志: $INSTALL_PREFIX/logs/"
echo ""
