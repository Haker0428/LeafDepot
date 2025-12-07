"""堆垛处理器工厂：根据满层判断结果自动选择对应的处理模块"""

from typing import Dict, List, Optional
from core.detection.detection.full_layer_detector import (
    FullLayerDetector, 
    CoverageBasedDetector,
    detect_full_layer
)
from core.detection.detection.full_stack_processor import (
    FullStackProcessor,
    TemplateBasedFullProcessor,
    process_full_stack
)
from core.detection.detection.partial_stack_processor import (
    PartialStackProcessor,
    TemplateBasedPartialProcessor,
    process_partial_stack
)


class StackProcessorFactory:
    """
    堆垛处理器工厂
    
    工作流程：
    1. 使用满层判断模块判断是否满层
    2. 根据判断结果选择对应的处理模块（满层/非满层）
    3. 执行处理并返回结果
    """
    
    def __init__(self,
                 detector: Optional[FullLayerDetector] = None,
                 full_processor: Optional[FullStackProcessor] = None,
                 partial_processor: Optional[PartialStackProcessor] = None,
                 enable_debug: bool = True):
        """
        :param detector: 满层判断器（可选，默认使用 CoverageBasedDetector）
        :param full_processor: 满层处理器（可选，默认使用 TemplateBasedFullProcessor）
        :param partial_processor: 非满层处理器（可选，默认使用 TemplateBasedPartialProcessor）
        :param enable_debug: 是否启用调试输出
        """
        self.detector = detector or CoverageBasedDetector(enable_debug=enable_debug)
        self.full_processor = full_processor or TemplateBasedFullProcessor(enable_debug=enable_debug)
        self.partial_processor = partial_processor or TemplateBasedPartialProcessor(enable_debug=enable_debug)
        self.enable_debug = enable_debug
    
    def process(self, layers: List[Dict], template_layers: List[int], 
                pile_roi: Dict[str, float]) -> Dict:
        """
        处理堆垛：自动判断满层并选择对应处理模块
        
        :param layers: 分层结果列表
        :param template_layers: 模板层配置（每层期望的箱数）
        :param pile_roi: 堆垛ROI区域
        :return: 完整处理结果字典，包含：
            - full: bool  # 是否满层
            - total: int  # 总箱数
            - detection: dict  # 满层判断结果
            - processing: dict  # 处理结果
            - top_layer: dict  # 顶层信息
        """
        # Step 1: 满层判断
        detection_result = self.detector.detect(layers, template_layers, pile_roi)
        is_full = detection_result["full"]
        
        # Step 2: 根据判断结果选择处理模块
        if is_full:
            if self.enable_debug:
                print("🟢 进入满层处理模块")
            processing_result = self.full_processor.process(
                layers, template_layers, detection_result
            )
        else:
            if self.enable_debug:
                print("🟡 进入非满层处理模块")
            processing_result = self.partial_processor.process(
                layers, template_layers, detection_result
            )
        
        # Step 3: 整合结果
        result = {
            "full": is_full,
            "total": processing_result["total"],
            "detection": detection_result,
            "processing": processing_result,
            "top_layer": detection_result.get("top_layer", {}),
            "reason": detection_result.get("reason", "unknown")
        }
        
        if self.enable_debug:
            print("\n" + "="*60)
            print("🎯 最终处理结果汇总")
            print("="*60)
            print(f"📦 是否满层: {'✅ 是' if is_full else '❌ 否'}")
            print(f"📊 总箱数: {result['total']}")
            print(f"📝 判断依据: {result['reason']}")
            print(f"🔧 处理策略: {processing_result.get('strategy', 'unknown')}")
            print("="*60 + "\n")
        
        return result


# 默认工厂实例（向后兼容）
_default_factory = StackProcessorFactory()


def process_stack(layers: List[Dict], template_layers: List[int], 
                 pile_roi: Dict[str, float],
                 factory: Optional[StackProcessorFactory] = None) -> Dict:
    """
    处理堆垛（便捷函数）
    
    :param layers: 分层结果列表
    :param template_layers: 模板层配置
    :param pile_roi: 堆垛ROI区域
    :param factory: 自定义工厂（可选，默认使用 StackProcessorFactory）
    :return: 完整处理结果字典
    """
    if factory is None:
        factory = _default_factory
    return factory.process(layers, template_layers, pile_roi)

