'''
Author: big box big box@qq.com
Date: 2025-10-20 23:20:31
LastEditors: big box big box@qq.com
LastEditTime: 2025-10-20 23:31:21
FilePath: /app/sim/cam_sys/sim_cam_sys.py
Description: 

Copyright (c) 2025 by lizh, All Rights Reserved. 
'''
from flask import Flask, request, jsonify
import os
from PIL import Image
import io
import random
import logging
import base64

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cam_sys.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CamSys")

app = Flask(__name__)
IMAGE_DIR = "camera_images"
os.makedirs(IMAGE_DIR, exist_ok=True)


@app.route('/take_photo', methods=['POST'])
def take_photo():
    """模拟相机系统拍照接口 (被RCS调用)"""
    data = request.json
    task_id = data.get("task_id")
    bin_code = data.get("bin_code")

    if not task_id or not bin_code:
        return jsonify({"status": "error", "message": "Missing task_id or bin_code"}), 400

    # 模拟拍照过程 (保存到SD卡)
    img = Image.new('RGB', (800, 600), color=(random.randint(
        0, 255), random.randint(0, 255), random.randint(0, 255)))
    img_io = io.BytesIO()
    img.save(img_io, format='PNG')
    img_data = img_io.getvalue()

    # 保存到SD卡 (使用模拟路径)
    image_path = os.path.join(
        IMAGE_DIR, f"simulated_sd_{task_id}_{bin_code}.png")
    with open(image_path, "wb") as f:
        f.write(img_data)

    logger.info("CamSys: Photo saved to %s", image_path)

    # 返回成功响应
    return jsonify({
        "status": "success",
        "image_path": image_path,
        "message": "Photo taken successfully"
    })


@app.route('/image/<task_id>', methods=['GET'])
def get_image(task_id):
    """模拟相机系统返回照片接口 (被外部网关调用)"""
    # 搜索匹配的图片
    image_files = [f for f in os.listdir(
        IMAGE_DIR) if f.startswith(f"simulated_sd_{task_id}_")]

    if not image_files:
        return jsonify({"status": "error", "message": "Image not found"}), 404

    image_file = image_files[0]
    image_path = os.path.join(IMAGE_DIR, image_file)

    # 读取图片并返回Base64
    with open(image_path, "rb") as f:
        image_data = f.read()

    image_base64 = base64.b64encode(image_data).decode('utf-8')

    return jsonify({
        "task_id": task_id,
        "image": image_base64,
        "format": "png"
    })


if __name__ == "__main__":
    # 创建必要的目录
    os.makedirs(IMAGE_DIR, exist_ok=True)

    # 启动相机系统服务
    print("Starting CamSys server on http://localhost:5010")
    print(f"Image directory: {os.path.abspath(IMAGE_DIR)}")
    app.run(host='0.0.0.0', port=5010, debug=False)
