from ultralytics import YOLO

# 初始化 nano 模型（最轻量）
model = YOLO('yolov8n.yaml')

# 开始训练
model.train(
    data='datasets/barcode/data.yaml',
    epochs=50,
    imgsz=640,
    batch=8,
    name='barcode-yolov8n'
)