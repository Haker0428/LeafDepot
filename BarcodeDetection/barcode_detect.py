from ultralytics import YOLO

# 初始化 nano 模型（最轻量）
model = YOLO('yolov8s.yaml')

# 开始训练
if __name__ == '__main__':
    model.train(
        data='datasets/barcode/data.yaml',
        epochs=100,
        imgsz=1080,
        batch=16,
        name='barcode+box+piles+QR-yolov8s'
    )