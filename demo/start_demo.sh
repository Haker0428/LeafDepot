#!/bin/bash

# 图片API Demo 启动脚本

echo "=========================================="
echo "🚀 启动图片API Demo服务"
echo "=========================================="

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# 进入项目根目录
cd "$PROJECT_ROOT"

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "❌ 错误: 未找到Python，请先安装Python"
    exit 1
fi

# 运行demo服务
echo "📡 服务地址: http://localhost:8001"
echo "🌐 前端页面: http://localhost:8001"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

python "$SCRIPT_DIR/image_api_demo.py"

