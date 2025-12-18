#!/bin/bash

# Gateway服务启动脚本 - 用于测试
# 启动Gateway服务并打开测试页面

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
GATEWAY_PORT="${GATEWAY_PORT:-8000}"
TEST_SERVER_PORT="${TEST_SERVER_PORT:-8080}"

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GATEWAY_SCRIPT="${PROJECT_ROOT}/services/api/gateway.py"
TEST_HTML="${PROJECT_ROOT}/demo/static/test_detect.html"
PID_FILE="${PROJECT_ROOT}/.gateway_test.pid"

# 检查Python是否可用
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ 未找到python3，请先安装Python${NC}"
    exit 1
fi

# 检测Python环境
PYTHON_CMD="python3"
CONDA_ENV=""

# 检测并尝试使用conda环境
if command -v conda &> /dev/null; then
    if conda env list | grep -q "tobacco_env"; then
        echo -e "${BLUE}检测到conda环境 tobacco_env，使用conda环境运行${NC}"
        CONDA_ENV="tobacco_env"
        # 使用conda run来运行命令
        PYTHON_CMD="conda run -n tobacco_env python"
    fi
fi

# 设置PYTHONPATH
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

# 验证fastapi是否可用
if $PYTHON_CMD -c "import fastapi" 2>/dev/null; then
    echo -e "${GREEN}✓ fastapi模块可用${NC}"
else
    echo -e "${RED}✗ fastapi模块未找到${NC}"
    echo -e "${YELLOW}请检查Python环境或安装依赖:${NC}"
    if [ -n "$CONDA_ENV" ]; then
        echo -e "  当前使用conda环境: $CONDA_ENV"
        echo -e "  如果仍然失败，请手动执行: conda activate $CONDA_ENV"
    else
        echo -e "  1. 激活conda环境: conda activate tobacco_env"
        echo -e "  2. 或安装依赖: pip install fastapi uvicorn"
    fi
    exit 1
fi

# 函数：检查服务是否运行
check_service() {
    if curl -s "${GATEWAY_URL}/docs" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 函数：停止服务
stop_service() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${YELLOW}正在停止Gateway服务 (PID: $PID)...${NC}"
            kill "$PID" 2>/dev/null
            sleep 2
            # 强制杀死如果还在运行
            if ps -p "$PID" > /dev/null 2>&1; then
                kill -9 "$PID" 2>/dev/null
            fi
        fi
        rm -f "$PID_FILE"
    fi
}

# 函数：清理退出
cleanup() {
    echo -e "\n${YELLOW}正在清理...${NC}"
    stop_service
    exit 0
}

# 捕获退出信号
trap cleanup SIGINT SIGTERM

# 检查是否已有服务运行
if check_service; then
    echo -e "${GREEN}✓ Gateway服务已在运行${NC}"
else
    # 启动服务
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  启动Gateway服务${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "Gateway地址: ${YELLOW}${GATEWAY_URL}${NC}"
    echo -e "服务脚本: ${YELLOW}${GATEWAY_SCRIPT}${NC}"
    echo ""

    # 检查服务脚本是否存在
    if [ ! -f "$GATEWAY_SCRIPT" ]; then
        echo -e "${RED}✗ 服务脚本不存在: ${GATEWAY_SCRIPT}${NC}"
        exit 1
    fi

    echo -e "${BLUE}正在启动Gateway服务...${NC}"

    # 在后台启动服务（使用uvicorn，更可靠）
    cd "$PROJECT_ROOT"
    # 尝试使用uvicorn启动（推荐方式）
    if $PYTHON_CMD -c "import uvicorn" 2>/dev/null; then
        $PYTHON_CMD -m uvicorn services.api.gateway:app --host 0.0.0.0 --port "$GATEWAY_PORT" > /tmp/gateway_test.log 2>&1 &
        GATEWAY_PID=$!
    else
        # 回退到直接运行脚本
        $PYTHON_CMD "$GATEWAY_SCRIPT" > /tmp/gateway_test.log 2>&1 &
        GATEWAY_PID=$!
    fi

    # 保存PID
    echo "$GATEWAY_PID" > "$PID_FILE"

    # 等待服务启动
    echo -e "${YELLOW}等待服务启动...${NC}"
    MAX_WAIT=30
    WAIT_COUNT=0
    while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
        if check_service; then
            echo -e "${GREEN}✓ Gateway服务启动成功！${NC}"
            break
        fi
        sleep 1
        WAIT_COUNT=$((WAIT_COUNT + 1))
        echo -n "."
    done

    if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
        echo -e "\n${RED}✗ Gateway服务启动超时${NC}"
        echo -e "${YELLOW}请查看日志: tail -f /tmp/gateway_test.log${NC}"
        stop_service
        exit 1
    fi

    echo ""
fi

# 启动简单的HTTP服务器提供测试页面
echo -e "${BLUE}正在启动测试页面服务器...${NC}"
cd "$(dirname "$TEST_HTML")"

# 使用Python启动简单的HTTP服务器（不需要特殊环境，用系统python3即可）
python3 -m http.server "$TEST_SERVER_PORT" > /tmp/test_page_server.log 2>&1 &
TEST_SERVER_PID=$!
sleep 1

TEST_PAGE_URL="http://localhost:${TEST_SERVER_PORT}/test_detect.html"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}服务运行中...${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Gateway API: ${GREEN}${GATEWAY_URL}${NC}"
echo -e "测试页面: ${GREEN}${TEST_PAGE_URL}${NC}"
echo -e "API文档: ${GREEN}${GATEWAY_URL}/docs${NC}"
echo ""
if [ -f "$PID_FILE" ]; then
    echo -e "Gateway PID: ${YELLOW}$(cat "$PID_FILE")${NC}"
fi
echo -e "测试服务器 PID: ${YELLOW}${TEST_SERVER_PID}${NC}"
echo ""

echo ""
echo -e "${YELLOW}注意: 测试页面会调用Gateway的正式接口${NC}"
echo -e "${YELLOW}请手动在浏览器中访问测试页面: ${GREEN}${TEST_PAGE_URL}${NC}"
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo ""

# 等待用户中断
wait

