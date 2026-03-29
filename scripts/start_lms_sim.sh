#!/bin/bash
###
 # @Author: big box big box@qq.com
 # @Date: 2025-10-14 22:32:04
 # @LastEditors: big box big box@qq.com
 # @LastEditTime: 2025-10-21 21:41:56
 # @FilePath: /app/sim/lms/start_sim_lms_server.sh
 # @Description: 
 # 
 # Copyright (c) 2025 by lizh, All Rights Reserved. 
### 

# 启动模拟LMS服务端
# 从项目根目录执行此脚本

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 设置 PYTHONPATH 为项目根目录
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 切换到服务目录
cd "$PROJECT_ROOT/services/sim/lms"

# 启动服务
uvicorn sim_lms_server:app --host 0.0.0.0 --port 6000 --reload