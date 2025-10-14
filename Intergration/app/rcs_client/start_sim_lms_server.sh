#!/bin/bash
###
 # @Author: big box big box@qq.com
 # @Date: 2025-10-14 22:32:04
 # @LastEditors: big box big box@qq.com
 # @LastEditTime: 2025-10-14 23:19:55
 # @FilePath: /Intergration/app/rcs_client/run.sh
 # @Description: 
 # 
 # Copyright (c) 2025 by lizh, All Rights Reserved. 
### 

# 启动模拟LMS服务端
uvicorn sim_lms_server:app --host 0.0.0.0 --port 5000 --reload