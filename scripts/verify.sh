#!/bin/bash
# 快速验证脚本 - 检查所有服务状态

echo "🔍 检查服务状态..."
echo ""

# 检查端口
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "✅ 端口 $1 正在监听 - $2"
        return 0
    else
        echo "❌ 端口 $1 未监听 - $2"
        return 1
    fi
}

# 检查文件
check_file() {
    if [ -f "$1" ]; then
        echo "✅ 文件存在: $2"
        return 0
    else
        echo "❌ 文件缺失: $2"
        return 1
    fi
}

# 检查目录
check_dir() {
    if [ -d "$1" ]; then
        echo "✅ 目录存在: $2"
        return 0
    else
        echo "❌ 目录缺失: $2"
        return 1
    fi
}

# 检查 Python 模块
check_python_module() {
    if python3 -c "import sys; sys.path.insert(0, '.'); $1" >/dev/null 2>&1; then
        echo "✅ Python 模块导入成功: $2"
        return 0
    else
        echo "❌ Python 模块导入失败: $2"
        return 1
    fi
}

echo "📋 检查端口状态:"
check_port 6000 "LMS 模拟服务"
check_port 8000 "网关服务"
check_port 3000 "前端服务"

echo ""
echo "📁 检查关键文件:"
check_file "shared/models/yolo/best.pt" "YOLO 模型"
check_file "shared/tools/BarcodeReaderCLI/bin/BarcodeReaderCLI" "条形码识别工具"
check_file "core/config/pile_config.json" "堆垛配置"
check_file "services/api/gateway.py" "网关服务"

echo ""
echo "📂 检查目录结构:"
check_dir "core/detection" "核心检测模块"
check_dir "core/vision" "视觉处理模块"
check_dir "services/api" "API 服务"
check_dir "services/sim" "模拟服务"
check_dir "web/src" "前端源码"

echo ""
echo "🐍 检查 Python 模块:"
check_python_module "from core.detection import prepare_logic" "核心检测模块"
check_python_module "from core.vision import YoloDetection" "视觉处理模块"
check_python_module "from services.utils.compression import compress_and_encode" "服务工具"

echo ""
echo "📡 测试 API 可访问性:"
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "✅ 网关 API 文档可访问 (http://localhost:8000/docs)"
else
    echo "❌ 网关 API 文档不可访问 (服务可能未启动)"
fi

if curl -s http://localhost:6000/docs > /dev/null 2>&1; then
    echo "✅ LMS API 文档可访问 (http://localhost:6000/docs)"
else
    echo "❌ LMS API 文档不可访问 (服务可能未启动)"
fi

echo ""
echo "✅ 验证完成！"
echo ""
echo "💡 提示："
echo "   - 如果端口未监听，请启动相应的服务"
echo "   - 如果文件缺失，请检查迁移是否完整"
echo "   - 如果模块导入失败，请检查 Python 路径和环境"


