"""
核心算法模块
- scene_prepare: 场景准备
- layer_clustering: 分层聚类
- layer_filter: 层过滤
"""
from .scene_prepare import prepare_logic
from .layer_clustering import (
    cluster_layers,
    cluster_layers_with_roi,
    cluster_layers_with_box_roi,
    draw_layers_on_image,
    draw_layers_with_roi,
    draw_layers_with_box_roi,
    visualize_layers,
    visualize_layers_with_roi,
    visualize_layers_with_box_roi,
)
from .layer_filter import filter_rear_boxes_if_multilayer, remove_fake_top_layer

__all__ = [
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
    "filter_rear_boxes_if_multilayer",
    "remove_fake_top_layer",
]
