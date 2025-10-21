    from ultralytics import YOLO

# 载入预训练模型（yolov8n.pt 是 nano 版，速度快）
model = YOLO('yolov8n.pt')


# class-agnostic 推理，只输出框，不管类别
results = model("/Users/hepeng/Project/LeafDepot/LeafDepot/demo_test/raw_img/img0.png", conf=0.3, iou=0.4, agnostic_nms=True)

# 获取所有检测框
boxes = results[0].boxes
print(f"检测框数量（可能即为烟箱数量）：{len(boxes)}")

# 显示推理结果
results[0].show()