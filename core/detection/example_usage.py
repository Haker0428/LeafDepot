"""
新架构使用示例

展示如何使用可扩展的满层判断和处理模块
"""

from core.detection.detection import (
    # 原有接口（向后兼容）
    prepare_logic,
    cluster_layers_with_box_roi,
    remove_fake_top_layer,
    verify_full_stack,  # 仍然可用，内部使用新架构
    
    # 新接口（可扩展）
    StackProcessorFactory,
    process_stack,
    CoverageBasedDetector,
    TemplateBasedFullProcessor,
    TemplateBasedPartialProcessor,
)


def example_1_use_factory():
    """示例1：使用工厂模式（推荐）"""
    print("="*60)
    print("示例1：使用工厂模式（自动选择处理模块）")
    print("="*60)
    
    # 假设已有分层结果
    layers = [...]  # 分层结果
    template_layers = [10, 10, 10]  # 模板配置
    pile_roi = {"x1": 0, "y1": 0, "x2": 100, "y2": 200}  # ROI区域
    
    # 使用默认工厂（自动判断满层并选择处理模块）
    factory = StackProcessorFactory(enable_debug=True)
    result = factory.process(layers, template_layers, pile_roi)
    
    print(f"是否满层: {result['full']}")
    print(f"总箱数: {result['total']}")
    print(f"判断依据: {result['reason']}")


def example_2_custom_detector():
    """示例2：自定义满层判断器"""
    print("="*60)
    print("示例2：自定义满层判断器（调整阈值）")
    print("="*60)
    
    # 创建自定义判断器（调整阈值）
    custom_detector = CoverageBasedDetector(
        coverage_threshold=0.85,  # 降低覆盖率阈值
        cv_gap_threshold=0.5,      # 提高间距变异系数阈值
        enable_debug=True
    )
    
    # 使用自定义判断器创建工厂
    factory = StackProcessorFactory(
        detector=custom_detector,
        enable_debug=True
    )
    
    layers = [...]
    template_layers = [10, 10, 10]
    pile_roi = {"x1": 0, "y1": 0, "x2": 100, "y2": 200}
    
    result = factory.process(layers, template_layers, pile_roi)


def example_3_custom_processors():
    """示例3：自定义处理模块"""
    print("="*60)
    print("示例3：自定义满层和非满层处理模块")
    print("="*60)
    
    # 可以继承并实现自定义处理器
    class MyFullProcessor(TemplateBasedFullProcessor):
        """自定义满层处理器"""
        def process(self, layers, template_layers, detection_result):
            # 自定义处理逻辑
            result = super().process(layers, template_layers, detection_result)
            # 可以添加额外的处理
            return result
    
    class MyPartialProcessor(TemplateBasedPartialProcessor):
        """自定义非满层处理器"""
        def process(self, layers, template_layers, detection_result):
            # 自定义处理逻辑
            result = super().process(layers, template_layers, detection_result)
            # 可以添加额外的处理
            return result
    
    # 使用自定义处理器
    factory = StackProcessorFactory(
        full_processor=MyFullProcessor(),
        partial_processor=MyPartialProcessor(),
        enable_debug=True
    )
    
    layers = [...]
    template_layers = [10, 10, 10]
    pile_roi = {"x1": 0, "y1": 0, "x2": 100, "y2": 200}
    
    result = factory.process(layers, template_layers, pile_roi)


def example_4_step_by_step():
    """示例4：分步骤使用（更细粒度控制）"""
    print("="*60)
    print("示例4：分步骤使用（独立调试）")
    print("="*60)
    
    from detection import detect_full_layer, process_full_stack, process_partial_stack
    
    layers = [...]
    template_layers = [10, 10, 10]
    pile_roi = {"x1": 0, "y1": 0, "x2": 100, "y2": 200}
    
    # Step 1: 独立判断满层（可调试）
    detector = CoverageBasedDetector(enable_debug=True)
    detection_result = detector.detect(layers, template_layers, pile_roi)
    
    # Step 2: 根据判断结果选择处理模块
    if detection_result["full"]:
        # 满层处理
        processor = TemplateBasedFullProcessor(enable_debug=True)
        result = processor.process(layers, template_layers, detection_result)
    else:
        # 非满层处理
        processor = TemplateBasedPartialProcessor(enable_debug=True)
        result = processor.process(layers, template_layers, detection_result)
    
    print(f"总箱数: {result['total']}")


def example_5_backward_compatible():
    """示例5：向后兼容（原有代码无需修改）"""
    print("="*60)
    print("示例5：向后兼容（原有接口仍然可用）")
    print("="*60)
    
    layers = [...]
    template_layers = [10, 10, 10]
    pile_roi = {"x1": 0, "y1": 0, "x2": 100, "y2": 200}
    
    # 原有接口仍然可用，内部使用新架构
    result = verify_full_stack(layers, template_layers, pile_roi)
    
    print(f"是否满层: {result['full']}")
    print(f"总箱数: {result['total']}")


if __name__ == "__main__":
    print("新架构使用示例\n")
    print("注意：这些示例需要实际的 layers 数据才能运行")
    print("请参考 predict.py 中的实际使用方式\n")

