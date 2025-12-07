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
uvicorn sim_rcs_server:app --host 0.0.0.0 --port 4001 --reload