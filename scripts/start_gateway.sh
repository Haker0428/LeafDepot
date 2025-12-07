#!/bin/bash
###
 # @Author: big box big box@qq.com
 # @Date: 2025-10-14 22:32:04
 # @LastEditors: big box big box@qq.com
 # @LastEditTime: 2025-10-21 23:39:41
 # @FilePath: /app/start_gateway.sh
 # @Description: 
 # 
 # Copyright (c) 2025 by lizh, All Rights Reserved. 
### 

# 启动网关服务
# 从项目根目录执行此脚本

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 设置 PYTHONPATH 为项目根目录
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 切换到服务目录
cd "$PROJECT_ROOT/services/api"

# 启动服务
uvicorn gateway:app --host 0.0.0.0 --port 8000 --reload
