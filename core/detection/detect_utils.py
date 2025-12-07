"""
检测工具模块 - 向后兼容接口
该文件已重构为多个小模块，此文件用于保持向后兼容性。
建议新代码直接导入具体模块：from detection import cluster_layers
"""

# 从新模块导入所有内容，保持向后兼容
from core.detection.utils import PileNotFoundError, PileTypeDatabase, extract_yolo_detections
from core.detection.detection import (
    prepare_logic,
    filter_rear_boxes_if_multilayer,
    remove_fake_top_layer,
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
)
from core.detection.visualization import prepare_scene, visualize_pile_scene

__all__ = [
    "PileNotFoundError",
    "PileTypeDatabase",
    "extract_yolo_detections",
    "prepare_logic",
    "prepare_scene",
    "visualize_pile_scene",
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
]
