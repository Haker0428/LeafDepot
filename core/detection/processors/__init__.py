"""
堆垛处理模块
- full_layer_detector: 满层判断器
- stack_processor: 堆垛处理器（满层/非满层）
- factory: 处理器工厂（统一入口）
"""
from .full_layer_detector import (
    FullLayerDetector,
    CoverageBasedDetector,
)
from .stack_processor import (
    FullStackProcessor,
    TemplateBasedFullProcessor,
    PartialStackProcessor,
    TemplateBasedPartialProcessor,
)
from .factory import StackProcessorFactory, count_boxes
# 向后兼容：导出旧接口
from .full_layer_verification import (
    calc_coverage,
    calc_cv_gap,
    calc_cv_width,
    verify_full_stack,
)

__all__ = [
    # 向后兼容接口
    "calc_coverage",
    "calc_cv_gap",
    "calc_cv_width",
    "verify_full_stack",
    # 核心接口（类）
    "FullLayerDetector",
    "CoverageBasedDetector",
    "FullStackProcessor",
    "TemplateBasedFullProcessor",
    "PartialStackProcessor",
    "TemplateBasedPartialProcessor",
    "StackProcessorFactory",
    "count_boxes",  # 算法统一入口
]
