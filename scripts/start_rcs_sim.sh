#!/bin/bash
###
 # @Author: big box big box@qq.com
 # @Date: 2025-10-14 22:32:04
 # @LastEditors: big box big box@qq.com
 # @LastEditTime: 2025-10-24 00:59:31
 # @FilePath: /Intergration/app/sim/rcs/start_sim_rcs_server.sh
 # @Description: 
 # 
 # Copyright (c) 2025 by lizh, All Rights Reserved. 
### 

# 启动模拟RCS服务端
# 从项目根目录执行此脚本

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 设置 PYTHONPATH 为项目根目录
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 切换到服务目录
cd "$PROJECT_ROOT/services/sim/rcs"

# 启动服务
uvicorn sim_rcs_server:app --host 0.0.0.0 --port 4001 --reload