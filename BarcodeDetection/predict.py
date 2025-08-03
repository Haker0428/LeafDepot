from ultralytics import YOLO

model = YOLO("runs/detect/barcode-yolov8n6/weights/best.pt")
results = model.predict(source="datasets/barcode/images/train/img0006.jpg", save=True)

# 获取所有检测框
boxes = results[0].boxes
print(f"检测条形码数量（可能即为烟箱数量）：{len(boxes)}")

# 显示推理结果
results[0].show()