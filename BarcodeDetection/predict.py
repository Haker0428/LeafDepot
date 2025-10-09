'''
Author: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
Date: 2025-09-17 20:38:39
LastEditors: big box big box@qq.com
LastEditTime: 2025-10-09 23:48:36
FilePath: /LeafDepot/BarcodeDetection/predict.py
Description: 

Copyright (c) 2025 by lizh, All Rights Reserved. 
'''
from ultralytics import YOLO

model = YOLO(
    "BarcodeDetection/runs/detect/barcode+box+piles-yolov8s/weights/best.pt")
results = model.predict(
    source="BarcodeDetection/datasets/test/img0001"".jpg", save=True)
# 获取所有检测框
boxes = results[0].boxes
print(f"检测条形码数量（可能即为烟箱数量）：{len(boxes)}")

# 显示推理结果
results[0].show()
