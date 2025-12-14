# Detection 脚本说明

## predict.py - 预测测试脚本

### 运行方式

**方式1：从项目根目录运行（推荐）**
```bash
cd /Users/hepeng/Project/lead_depot/LeafDepot
python -m core.detection.scripts.predict
```

**方式2：直接运行（需要确保在正确的目录）**
```bash
cd /Users/hepeng/Project/lead_depot/LeafDepot/core/detection/scripts
python predict.py
```

### 功能说明

该脚本用于测试检测算法的完整流程：
1. YOLO检测
2. 场景准备
3. 分层聚类
4. 满层判断
5. 结果可视化

### 输出

结果会保存到 `core/detection/output/` 目录下：
- `annotated_test.jpg` - 场景准备结果
- `annotated_layers.jpg` - 分层聚类结果
- `annotated_layers_roi.jpg` - 带ROI的分层结果
- `annotated_layers_boxes.jpg` - 带box ROI的分层结果
- `annotated_top_complete.jpg` - 最终结果
