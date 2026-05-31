#!/bin/bash
#
# pnpm 离线安装脚本
# 用法: ./install_pnpm.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$SCRIPT_DIR/pnpm_pkg"
BINARY="$PKG_DIR/pnpm-linux-x64"
INSTALL_PREFIX="/usr/local/bin"

echo ""
echo "========================================"
echo "  pnpm 离线安装脚本"
echo "========================================"
echo ""

if [ ! -f "$BINARY" ]; then
    echo "[错误] 找不到离线包: $BINARY"
    exit 1
fi

echo "[INFO] 安装 pnpm 到 $INSTALL_PREFIX/pnpm ..."
sudo cp "$BINARY" "$INSTALL_PREFIX/pnpm"
sudo chmod +x "$INSTALL_PREFIX/pnpm"

echo "[OK] pnpm 安装成功"
echo ""
echo "[INFO] 版本: $(pnpm --version)"
echo ""
echo "使用示例:"
echo "  pnpm install          # 安装依赖"
echo "  pnpm dev              # 启动开发服务器"
echo ""
