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

# 启动模拟LMS服务端
uvicorn gateway:app --host 0.0.0.0 --port 8000 --reload
