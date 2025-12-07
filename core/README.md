# 核心算法模块

此目录包含项目的核心算法和检测功能。

## 目录结构

- `detection/` - 堆垛检测算法核心
  - `detection/` - 检测核心逻辑（分层、聚类、满层判断等）
  - `utils/` - 工具函数（异常处理、数据库、YOLO工具等）
  - `visualization/` - 可视化功能

- `vision/` - 视觉处理模块
  - `yolo_detector.py` - YOLO 目标检测
  - `barcode_recognizer.py` - 条形码识别

- `config/` - 配置文件
  - `pile_config.json` - 堆垛配置数据库

## 使用示例

```python
from core.detection import prepare_logic, cluster_layers, verify_full_stack
from core.vision import YoloDetection, BarcodeRecognizer

# 使用检测功能
prepared = prepare_logic(yolo_output)

# 使用视觉处理
detector = YoloDetection(model_path="shared/models/yolo/best.pt")
recognizer = BarcodeRecognizer()
```

