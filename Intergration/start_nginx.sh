#!/bin/bash
###
 # @Author: big box big box@qq.com
 # @Date: 2025-10-14 22:32:04
 # @LastEditors: big box big box@qq.com
 # @LastEditTime: 2025-10-14 22:32:07
 # @FilePath: /Intergration/run.sh
 # @Description: 
 # 
 # Copyright (c) 2025 by lizh, All Rights Reserved. 
### 

# 启动Nginx
echo "启动Nginx..."
nginx -c $(pwd)/nginx.conf

echo "启动成功! 访问 http://localhost"