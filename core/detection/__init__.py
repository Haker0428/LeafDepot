"""
检测算法模块 - 统一导出接口

目录结构：
- core/: 核心算法（场景准备、分层聚类、层过滤）
- processors/: 堆垛处理（满层判断、计数处理、工厂）
- utils/: 工具模块（异常、数据库、YOLO工具、路径）
- visualization/: 可视化模块
"""

# 工具模块
from core.detection.utils import (
    PileNotFoundError,
    PileTypeDatabase,
    extract_yolo_detections
)

# 核心算法模块
from core.detection.core import (
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
)

# 堆垛处理模块（推荐使用）
from core.detection.processors import (
    StackProcessorFactory,
    count_boxes,  # 算法统一入口：count_boxes(image_path, pile_id)
)

# 可视化模块
from core.detection.visualization import (
    prepare_scene,
    visualize_pile_scene
)

# 向后兼容：导出旧接口（full_layer_verification）
# 这些函数现在从processors模块导出
from core.detection.processors import (
    calc_coverage,
    calc_cv_gap,
    calc_cv_width,
    verify_full_stack,
)

__all__ = [
    # 工具模块
    "PileNotFoundError",
    "PileTypeDatabase",
    "extract_yolo_detections",
    
    # 核心算法模块
    "prepare_logic",
    "filter_rear_boxes_if_multilayer",
    "remove_fake_top_layer",
    "cluster_layers",
    "cluster_layers_with_roi",
    "cluster_layers_with_box_roi",
    "draw_layers_on_image",
    "draw_layers_with_roi",
    "draw_layers_with_box_roi",
    "visualize_layers",
    "visualize_layers_with_roi",
    "visualize_layers_with_box_roi",
    
    # 堆垛处理模块（推荐使用）
    "StackProcessorFactory",
    "count_boxes",  # 算法统一入口：count_boxes(image_path, pile_id)
    
    # 可视化模块
    "prepare_scene",
    "visualize_pile_scene",
    
    # 向后兼容（旧接口）
    "calc_coverage",
    "calc_cv_gap",
    "calc_cv_width",
    "verify_full_stack",
]
