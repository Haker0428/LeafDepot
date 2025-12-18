#!/bin/bash

# 盘点任务API测试脚本
# 用于测试盘点任务相关API接口

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
TASK_NO="${TASK_NO:-demo}"
BIN_LOCATION="${BIN_LOCATION:-test01}"
PILE_ID="${PILE_ID:-1}"
CODE_TYPE="${CODE_TYPE:-ucc128}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  盘点任务API测试脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Gateway地址: ${YELLOW}${GATEWAY_URL}${NC}"
echo -e "任务号: ${YELLOW}${TASK_NO}${NC}"
echo -e "库位号: ${YELLOW}${BIN_LOCATION}${NC}"
echo -e "堆垛ID: ${YELLOW}${PILE_ID}${NC}"
echo -e "条码类型: ${YELLOW}${CODE_TYPE}${NC}"
echo ""

# 检查服务是否运行
echo -e "${BLUE}[1/4] 检查服务状态...${NC}"
if curl -s "${GATEWAY_URL}/docs" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Gateway服务运行正常${NC}"
else
    echo -e "${RED}✗ Gateway服务未运行或无法访问${NC}"
    echo -e "${YELLOW}请确保服务已启动: python services/api/gateway.py${NC}"
    exit 1
fi
echo ""

# 测试扫码+识别接口
echo -e "${BLUE}[2/4] 测试扫码+识别接口...${NC}"
SCAN_RESPONSE=$(curl -s -X POST "${GATEWAY_URL}/api/inventory/scan-and-recognize" \
    -H "Content-Type: application/json" \
    -d "{
        \"taskNo\": \"${TASK_NO}\",
        \"binLocation\": \"${BIN_LOCATION}\",
        \"pile_id\": ${PILE_ID},
        \"code_type\": \"${CODE_TYPE}\"
    }")

SCAN_CODE=$(echo "${SCAN_RESPONSE}" | grep -o '"code":[0-9]*' | grep -o '[0-9]*')
if [ "${SCAN_CODE}" = "200" ]; then
    echo -e "${GREEN}✓ 扫码+识别测试成功${NC}"
    echo "${SCAN_RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${SCAN_RESPONSE}"
else
    echo -e "${RED}✗ 扫码+识别测试失败${NC}"
    echo "${SCAN_RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${SCAN_RESPONSE}"
fi
echo ""

# 等待一下，确保结果已保存
sleep 1

# 测试读取识别结果接口
echo -e "${BLUE}[3/4] 测试读取识别结果接口...${NC}"
RESULT_RESPONSE=$(curl -s -X GET "${GATEWAY_URL}/api/inventory/recognition-result?taskNo=${TASK_NO}&binLocation=${BIN_LOCATION}")

RESULT_CODE=$(echo "${RESULT_RESPONSE}" | grep -o '"code":[0-9]*' | grep -o '[0-9]*')
if [ "${RESULT_CODE}" = "200" ]; then
    echo -e "${GREEN}✓ 读取识别结果测试成功${NC}"
    echo "${RESULT_RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${RESULT_RESPONSE}"
else
    echo -e "${RED}✗ 读取识别结果测试失败${NC}"
    echo "${RESULT_RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${RESULT_RESPONSE}"
fi
echo ""

# 测试读取检测状态接口（可选）
echo -e "${BLUE}[4/4] 测试读取检测状态接口...${NC}"
PROGRESS_RESPONSE=$(curl -s -X GET "${GATEWAY_URL}/api/inventory/progress?taskNo=${TASK_NO}")

PROGRESS_CODE=$(echo "${PROGRESS_RESPONSE}" | grep -o '"code":[0-9]*' | grep -o '[0-9]*')
if [ "${PROGRESS_CODE}" = "200" ]; then
    echo -e "${GREEN}✓ 读取检测状态测试成功${NC}"
    echo "${PROGRESS_RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${PROGRESS_RESPONSE}"
else
    echo -e "${YELLOW}⚠ 读取检测状态失败（可能是任务不存在，这是正常的）${NC}"
    echo "${PROGRESS_RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${PROGRESS_RESPONSE}"
fi
echo ""

# 总结
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  测试完成${NC}"
echo -e "${BLUE}========================================${NC}"

# 使用示例
echo ""
echo -e "${YELLOW}使用示例:${NC}"
echo "  默认参数: ./test_detect_api.sh"
echo "  自定义参数:"
echo "    TASK_NO=task001 BIN_LOCATION=bin001 ./test_detect_api.sh"
echo "    GATEWAY_URL=http://localhost:8000 TASK_NO=demo BIN_LOCATION=test01 PILE_ID=2 CODE_TYPE=code128 ./test_detect_api.sh"
echo ""
echo -e "${YELLOW}API接口说明:${NC}"
echo "  1. POST /api/inventory/scan-and-recognize - 扫码+识别（整合Detect和Barcode）"
echo "  2. GET  /api/inventory/recognition-result - 读取识别结果"
echo "  3. GET  /api/inventory/progress - 读取检测状态"
echo "  4. POST /api/inventory/start-inventory - 开始盘点任务"

