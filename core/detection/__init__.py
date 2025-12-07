"""
检测工具模块 - 统一导出接口
模块化结构：
- utils: 工具模块（异常、配置数据库、YOLO工具）
- detection: 检测模块（场景准备、分层聚类、满层判断）
- visualization: 可视化模块（场景可视化）
"""

# 工具模块
from core.detection.utils import PileNotFoundError, PileTypeDatabase, extract_yolo_detections

# 检测模块
from core.detection.detection import (
    prepare_logic,
    filter_rear_boxes_if_multilayer,
    cluster_layers,
    cluster_layers_with_roi,
    cluster_layers_with_box_roi,
    draw_layers_on_image,
    draw_layers_with_roi,
    draw_layers_with_box_roi,
    visualize_layers,
    visualize_layers_with_roi,
    visualize_layers_with_box_roi,
    calc_coverage,
    calc_cv_gap,
    calc_cv_width,
    verify_full_stack,
    remove_fake_top_layer,
)

# 可视化模块
from core.detection.visualization import prepare_scene, visualize_pile_scene

__all__ = [
    # 工具模块
    "PileNotFoundError",
    "PileTypeDatabase",
    "extract_yolo_detections",
    # 检测模块
    "prepare_logic",
    "cluster_layers",
    "cluster_layers_with_roi",
    "cluster_layers_with_box_roi",
    "draw_layers_on_image",
    "draw_layers_with_roi",
    "draw_layers_with_box_roi",
    "visualize_layers",
    "visualize_layers_with_roi",
    "visualize_layers_with_box_roi",
    "calc_coverage",
    "calc_cv_gap",
    "calc_cv_width",
    "verify_full_stack",
    "filter_rear_boxes_if_multilayer",
    "remove_fake_top_layer",
    # 可视化模块
    "prepare_scene",
    "visualize_pile_scene",
]


