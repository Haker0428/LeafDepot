"""检测模块：场景准备、分层聚类、满层判断"""

from core.detection.detection.scene_prepare import prepare_logic, filter_rear_boxes_if_multilayer, remove_fake_top_layer
from core.detection.detection.layer_clustering import (
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
from core.detection.detection.full_layer_verification import (
    calc_coverage,
    calc_cv_gap,
    calc_cv_width,
    verify_full_stack,
)

# 新增：可扩展的满层判断和处理模块
from core.detection.detection.full_layer_detector import (
    FullLayerDetector,
    CoverageBasedDetector,
    detect_full_layer,
)
from core.detection.detection.full_stack_processor import (
    FullStackProcessor,
    TemplateBasedFullProcessor,
    process_full_stack,
)
from core.detection.detection.partial_stack_processor import (
    PartialStackProcessor,
    TemplateBasedPartialProcessor,
    process_partial_stack,
)
from core.detection.detection.stack_processor_factory import (
    StackProcessorFactory,
    process_stack,
)

__all__ = [
    # 原有接口（向后兼容）
    "prepare_logic",
    "filter_rear_boxes_if_multilayer",
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
    "remove_fake_top_layer",
    # 新增接口
    "FullLayerDetector",
    "CoverageBasedDetector",
    "detect_full_layer",
    "FullStackProcessor",
    "TemplateBasedFullProcessor",
    "process_full_stack",
    "PartialStackProcessor",
    "TemplateBasedPartialProcessor",
    "process_partial_stack",
    "StackProcessorFactory",
    "process_stack",
]
