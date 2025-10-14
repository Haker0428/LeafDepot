#!/bin/bash
###
 # @Author: big box big box@qq.com
 # @Date: 2025-10-14 22:32:04
 # @LastEditors: big box big box@qq.com
 # @LastEditTime: 2025-10-14 23:21:29
 # @FilePath: /Intergration/start_app.sh
 # @Description: 
 # 
 # Copyright (c) 2025 by lizh, All Rights Reserved. 
### 

conda activate tobacco_env

# 启动FastAPI
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
