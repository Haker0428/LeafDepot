# Detection 检测算法模块

## 📁 目录结构

```
core/detection/
├── README.md                    # 本文件（使用说明）
├── __init__.py                  # 统一导出接口
│
├── core/                        # 🔵 核心算法模块
│   ├── __init__.py
│   ├── scene_prepare.py         # 场景准备：YOLO输出过滤、ROI确定
│   ├── layer_clustering.py      # 分层聚类：根据位置对box进行分层
│   └── layer_filter.py          # 层过滤：去除误层、过滤背面box
│
├── processors/                  # 🟢 堆垛处理模块（满层判断 + 计数）
│   ├── __init__.py
│   ├── full_layer_detector.py   # 满层判断器（抽象接口 + 覆盖率实现）
│   ├── stack_processor.py       # 堆垛处理器（满层/非满层统一处理）
│   └── factory.py               # 处理器工厂（统一入口）⭐推荐使用
│
├── utils/                       # 🟡 工具模块
│   ├── __init__.py
│   ├── exceptions.py            # 异常定义
│   ├── pile_db.py               # 堆垛配置数据库
│   ├── yolo_utils.py            # YOLO工具函数
│   └── path_utils.py            # 路径工具函数
│
└── visualization/               # 🟣 可视化模块
    ├── __init__.py
    └── scene_visualize.py       # 场景可视化

# 辅助文件
├── examples/                    # 示例代码
│   └── usage_example.py         # 使用示例
└── scripts/                     # 测试脚本
    └── predict.py               # 预测测试脚本

# 向后兼容（已废弃，但保留）
└── detection/                   # ⚠️ 旧目录（向后兼容层，请勿在新代码中使用）
```

## 🎯 模块说明

### 1. core/ - 核心算法模块

#### scene_prepare.py
- **功能**: 场景准备，处理YOLO原始输出
- **主要函数**:
  - `prepare_logic()`: 过滤YOLO输出，找到pile并确定ROI

#### layer_clustering.py
- **功能**: 分层聚类算法
- **主要函数**:
  - `cluster_layers()`: 基础分层聚类
  - `cluster_layers_with_roi()`: 带ROI的分层聚类
  - `cluster_layers_with_box_roi()`: 带box ROI的分层聚类
  - 可视化函数: `draw_layers_*`, `visualize_layers_*`

#### layer_filter.py
- **功能**: 层过滤和清理
- **主要函数**:
  - `filter_rear_boxes_if_multilayer()`: 多层时过滤背面box
  - `remove_fake_top_layer()`: 去除误层

### 2. processors/ - 堆垛处理模块 ⭐核心

#### full_layer_detector.py
- **功能**: 满层判断
- **主要类**:
  - `FullLayerDetector`: 抽象基类
  - `CoverageBasedDetector`: 基于覆盖率的实现（默认）

#### stack_processor.py
- **功能**: 堆垛处理（满层/非满层计数）
- **主要类**:
  - `FullStackProcessor`: 满层处理器抽象基类
  - `TemplateBasedFullProcessor`: 模板基础满层处理器
  - `PartialStackProcessor`: 非满层处理器抽象基类
  - `TemplateBasedPartialProcessor`: 模板基础非满层处理器

#### factory.py ⭐统一入口
- **功能**: 统一入口，自动选择处理模块
- **主要类**:
  - `StackProcessorFactory`: 处理器工厂
  - `process_stack()`: 便捷函数

### 3. utils/ - 工具模块

- `exceptions.py`: 自定义异常
- `pile_db.py`: 堆垛配置数据库（读取pile_config.json）
- `yolo_utils.py`: YOLO检测结果提取
- `path_utils.py`: 路径和输出目录管理

### 4. visualization/ - 可视化模块

- `scene_visualize.py`: 场景可视化函数

## 🚀 使用流程

### 标准流程（推荐）

```python
from core.detection.processors import StackProcessorFactory
from core.detection.utils import extract_yolo_detections, PileTypeDatabase
from core.detection.core import (
    prepare_logic,
    cluster_layers_with_box_roi,
    remove_fake_top_layer
)

# 1. YOLO检测
from ultralytics import YOLO
model = YOLO("path/to/model.pt")
results = model.predict(source="image.jpg")
detections = extract_yolo_detections(results)

# 2. 场景准备
prepared = prepare_logic(detections, conf_thr=0.65)

# 3. 分层聚类
layer_result = cluster_layers_with_box_roi(prepared["boxes"], prepared["pile_roi"])
layers = layer_result["layers"]

# 4. 层过滤
layers = remove_fake_top_layer(layers)

# 5. 获取模板配置
pile_db = PileTypeDatabase("path/to/pile_config.json")
template_layers = pile_db.get_template_layers(pile_id=1)

# 6. 处理堆垛（统一入口）⭐
factory = StackProcessorFactory()
result = factory.process(layers, template_layers, prepared["pile_roi"])
total_count = result["total"]  # 总箱数
is_full = result["full"]       # 是否满层
```

### 简化流程（使用顶层导入）

```python
from core.detection import (
    StackProcessorFactory,
    prepare_logic,
    cluster_layers_with_box_roi,
    remove_fake_top_layer,
    PileTypeDatabase,
    extract_yolo_detections
)

# ... YOLO检测和场景准备 ...

# 统一入口
factory = StackProcessorFactory(enable_debug=False)
result = factory.process(layers, template_layers, pile_roi)
```

## 📖 主要接口

### 统一入口（推荐使用）⭐

```python
from core.detection.processors import StackProcessorFactory

factory = StackProcessorFactory()
result = factory.process(
    layers: List[Dict],           # 分层结果
    template_layers: List[int],    # 模板层配置
    pile_roi: Dict[str, float]    # 堆垛ROI
)
# 返回: {
#     "full": bool,        # 是否满层
#     "total": int,        # 总箱数
#     "detection": dict,   # 满层判断结果
#     "processing": dict,  # 处理结果
#     "top_layer": dict,   # 顶层信息
#     "reason": str        # 判断依据
# }
```

### 分步骤接口

```python
# 场景准备
from core.detection.core.scene_prepare import prepare_logic

# 分层聚类
from core.detection.core.layer_clustering import cluster_layers_with_box_roi

# 层过滤
from core.detection.core.layer_filter import remove_fake_top_layer

# 满层判断（独立使用）
from core.detection.processors.full_layer_detector import CoverageBasedDetector
detector = CoverageBasedDetector()
result = detector.detect(layers, template_layers, pile_roi)
```

## 📝 设计原则

1. **单一职责**: 每个模块只负责一个明确的功能
2. **分层清晰**: core → processors → factory，层层递进
3. **统一入口**: 通过factory自动选择处理策略
4. **向后兼容**: 保留旧接口，新代码使用新结构

## 🔄 迁移指南

查看 [MIGRATION.md](./MIGRATION.md) 了解如何从旧结构迁移到新结构。

## 📚 调用链路

```
服务层 (services/vision/box_count_service.py)
  └─ count_boxes()
     └─ StackProcessorFactory.process()  ← 统一入口
        ├─ CoverageBasedDetector.detect()  ← 满层判断
        └─ 根据结果选择：
           ├─ TemplateBasedFullProcessor.process()  ← 满层处理
           └─ TemplateBasedPartialProcessor.process()  ← 非满层处理
```
