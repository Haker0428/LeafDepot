"""非满层处理模块：处理非满层堆垛的计数逻辑"""

from typing import Dict, List
from abc import ABC, abstractmethod


class PartialStackProcessor(ABC):
    """非满层堆垛处理器抽象基类"""
    
    @abstractmethod
    def process(self, layers: List[Dict], template_layers: List[int], 
                detection_result: Dict) -> Dict:
        """
        处理非满层堆垛，计算总箱数
        
        :param layers: 分层结果列表
        :param template_layers: 模板层配置（每层期望的箱数）
        :param detection_result: 满层判断结果
        :return: 处理结果字典，包含 total(int), details(dict) 等
        """
        pass


class TemplateBasedPartialProcessor(PartialStackProcessor):
    """
    基于模板的非满层处理器（当前默认实现）
    
    处理逻辑：
    顶层不满 → 总箱数 = 下层模板之和 + 顶层实际检测数
    """
    
    def __init__(self, enable_debug: bool = True):
        """
        :param enable_debug: 是否启用调试输出
        """
        self.enable_debug = enable_debug
    
    def process(self, layers: List[Dict], template_layers: List[int], 
                detection_result: Dict) -> Dict:
        """
        处理非满层堆垛
        
        :return: {
            "total": int,  # 总箱数
            "strategy": str,  # 使用的策略
            "details": {
                "n_detected": int,  # 检测到的层数
                "n_template": int,  # 模板层数
                "top_layer_observed": int,  # 顶层实际检测数
                "lower_layers_sum": int,  # 下层模板总和
                "calculation": str  # 计算说明
            }
        }
        """
        n_detected = len(layers)
        n_template = len(template_layers)
        
        # 顶层实际检测数
        top_layer_observed = detection_result.get("top_layer", {}).get("observed", 0)
        
        # 计算下层模板总和（排除顶层）
        if n_template > 1:
            lower_layers_sum = sum(template_layers[:-1])
        else:
            lower_layers_sum = 0
        
        # 顶层不满 → 总箱数 = 下层模板之和 + 顶层实际检测数
        total = lower_layers_sum + top_layer_observed
        
        strategy = "partial_with_template"
        calculation = (
            f"顶层不满 → 下层模板({lower_layers_sum}) + "
            f"顶层实际检测数({top_layer_observed}) = {total}"
        )
        
        result = {
            "total": int(total),
            "strategy": strategy,
            "details": {
                "n_detected": n_detected,
                "n_template": n_template,
                "top_layer_observed": top_layer_observed,
                "lower_layers_sum": lower_layers_sum,
                "calculation": calculation
            }
        }
        
        if self.enable_debug:
            print("\n" + "="*50)
            print("📦 非满层处理模块 - 处理结果")
            print("="*50)
            print(f"🎯 处理策略: {strategy}")
            print(f"📊 检测层数: {n_detected}, 模板层数: {n_template}")
            print(f"🔝 顶层实际检测数: {top_layer_observed}")
            print(f"📉 下层模板总和: {lower_layers_sum}")
            print(f"💡 计算说明: {calculation}")
            print(f"✅ 总箱数: {total}")
            print("="*50 + "\n")
        
        return result


# 默认处理器实例
_default_partial_processor = TemplateBasedPartialProcessor()


def process_partial_stack(layers: List[Dict], template_layers: List[int], 
                         detection_result: Dict,
                         processor: PartialStackProcessor = None) -> Dict:
    """
    处理非满层堆垛（便捷函数）
    
    :param layers: 分层结果列表
    :param template_layers: 模板层配置
    :param detection_result: 满层判断结果
    :param processor: 自定义处理器（可选，默认使用 TemplateBasedPartialProcessor）
    :return: 处理结果字典
    """
    if processor is None:
        processor = _default_partial_processor
    return processor.process(layers, template_layers, detection_result)

