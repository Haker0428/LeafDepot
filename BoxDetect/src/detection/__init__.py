"""检测模块：场景准备、分层聚类、满层判断"""

from detection.scene_prepare import prepare_logic
from detection.layer_clustering import (
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
from detection.full_layer_verification import (
    calc_coverage,
    calc_cv_gap,
    calc_cv_width,
    verify_full_stack,
)

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
    "calc_coverage",
    "calc_cv_gap",
    "calc_cv_width",
    "verify_full_stack",
]

