'''
Author: error: error: git config user.name & please set dead value or install git && error: git config user.email & please set dead value or install git & please set dead value or install git
Date: 2025-09-17 20:38:39
LastEditors: big box big box@qq.com
LastEditTime: 2025-10-09 23:48:36
FilePath: /LeafDepot/BarcodeDetection/predict.py
Description: 

Copyright (c) 2025 by lizh, All Rights Reserved. 
'''
from pathlib import Path
import cv2
from ultralytics import YOLO

# 使用新的模块导入路径
from core.detection.core import (
    prepare_logic,
    cluster_layers_with_box_roi,
    remove_fake_top_layer,
    draw_layers_with_box_roi,
    visualize_layers,
    visualize_layers_with_roi,
    visualize_layers_with_box_roi,
)
# verify_full_stack 从向后兼容模块导入
from core.detection import verify_full_stack
from core.detection.utils import extract_yolo_detections, PileTypeDatabase
from core.detection.utils.path_utils import ensure_output_dir
from core.detection.visualization import prepare_scene

# 从项目根目录计算路径
_project_root = Path(__file__).resolve().parent.parent.parent.parent
img_path = str(_project_root / "tests" / "test_images" / "full" / "sample1.jpg")
model_path = str(_project_root / "shared" / "models" / "yolo" / "pile+box.pt")
model = YOLO(model_path)
results = model.predict(source=img_path, save=False)  # 不保存YOLO默认输出

# 获取所有检测框
detections = extract_yolo_detections(results)
print(f"检测烟箱数量：{len(detections)}")
print(f"result is {detections}")

pile_config_path = _project_root / "core" / "config" / "pile_config.json"
pile_db = PileTypeDatabase(pile_config_path)
pile_id = 1
count = pile_db.get_total_count(pile_id)
# print(f"堆{pile_id}的总箱数：{count}")

# 确保输出目录存在
output_dir = ensure_output_dir()

prepared = prepare_scene(
    image_path=img_path,
    yolo_output=detections,  # YOLO 输出
    conf_thr=0.65,
    save_path="annotated_test.jpg",
    show=False,               # 改成 True 可直接弹窗显示
    output_dir=output_dir
)

# Step 2️⃣: 分层聚类 + 可视化
layer_result = visualize_layers(
    image_path=img_path,
    boxes=prepared["boxes"],
    pile_roi=prepared["pile_roi"],
    save_path="annotated_layers.jpg",
    gap_ratio=0.6,
    show=False,
    output_dir=output_dir
)

# Step 2️⃣: 分层聚类 + 层ROI + 可视化
result = visualize_layers_with_roi(
    image_path=img_path,
    boxes=prepared["boxes"],
    pile_roi=prepared["pile_roi"],
    gap_ratio=0.6,
    padding_ratio=0.1,
    save_path="annotated_layers_roi.jpg",
    show=False,
    output_dir=output_dir
)

layers_result = visualize_layers_with_box_roi(
    image_path=img_path,
    boxes=prepared["boxes"],
    pile_roi=prepared["pile_roi"],
    save_path="annotated_layers_boxes.jpg",
    show=False,
    target_layers=1,
    alpha=0.3,
    box_thickness=5,
    output_dir=output_dir
)
def reindex_layers(layers):
    """
    重新为层编号：最上层为1，依次递增
    """
    if not layers:
        return layers
    layers_sorted = sorted(layers, key=lambda l: l["avg_y"])
    for i, layer in enumerate(layers_sorted, 1):
        layer["index"] = i
    return layers_sorted

# 3️⃣ 满层判定
# template_layers = [5, 5, 5, 5, 5]  # 假设满垛 5 层，每层 2 箱
template_layers = [10, 10, 10]
# template_layers = [8, 8, 8, 8, 8]
# 2️⃣ 分层聚类
layers_result = cluster_layers_with_box_roi(prepared["boxes"], prepared["pile_roi"])

# layers_filtered = filter_rear_boxes_if_multilayer(layers_result["layers"], prepared["pile_roi"])
print(layers_result)

# 🆕 去除俯视误层
layers_result["layers"] = remove_fake_top_layer(layers_result["layers"])

layers_result["layers"] = reindex_layers(layers_result["layers"])

total_count = verify_full_stack(layers_result["layers"] , template_layers, prepared["pile_roi"])
print(f"总箱数: {total_count}")

draw_layers_with_box_roi(
    img_path=img_path,
    pile_roi=prepared["pile_roi"],
    layer_result=layers_result,
    save_path="annotated_top_complete.jpg",
    target_layers=1,
    layer_color=(0, 0, 255),  # 红色阴影
    alpha=0.35,
    show=False,
    output_dir=output_dir
)