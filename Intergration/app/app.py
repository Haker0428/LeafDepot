'''
Author: big box big box@qq.com
Date: 2025-10-14 21:06:05
LastEditors: big box big box@qq.com
LastEditTime: 2025-10-14 22:30:46
FilePath: /Intergration/app/app.py
Description: 

Copyright (c) 2025 by lizh, All Rights Reserved. 
'''
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import os
from pathlib import Path

app = FastAPI()

# 图片存储目录（相对于项目根目录）
IMAGES_DIR = Path("../images")


@app.get("/")
async def index():
    """返回前端页面"""
    return HTMLResponse(content=open("../ui/index.html").read(), status_code=200)


@app.get("/api/images")
async def get_images():
    """获取所有可用图片的路径（修正后的路径格式）"""
    images = []
    for img in IMAGES_DIR.iterdir():
        if img.is_file() and img.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
            # 修正：返回相对路径 /images/1.jpg
            images.append({
                "filename": img.name,
                "url": f"/images/{img.name}"  # 关键修正：使用相对路径
            })
    return {"images": images}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
