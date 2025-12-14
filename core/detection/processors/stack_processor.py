"""堆垛处理模块：处理满层和非满层堆垛的计数逻辑"""

from typing import Dict, List
from abc import ABC, abstractmethod


# ==================== 满层处理器 ====================

class FullStackProcessor(ABC):
    """满层堆垛处理器抽象基类"""
    
    @abstractmethod
    def process(self, layers: List[Dict], template_layers: List[int], 
                detection_result: Dict) -> Dict:
        """
        处理满层堆垛，计算总箱数
        
        :param layers: 分层结果列表
        :param template_layers: 模板层配置（每层期望的箱数）
        :param detection_result: 满层判断结果
        :return: 处理结果字典，包含 total(int), details(dict) 等
        """
        pass


class TemplateBasedFullProcessor(FullStackProcessor):
    """
    基于模板的满层处理器（当前默认实现）
    
    处理逻辑：
    1. 检测层数 = 模板层数 → 总箱数 = 所有模板层之和
    2. 检测层数 < 模板层数 → 总箱数 = 已检测层的模板之和
    """
    
    def __init__(self, enable_debug: bool = True):
        """
        :param enable_debug: 是否启用调试输出
        """
        self.enable_debug = enable_debug
    
    def process(self, layers: List[Dict], template_layers: List[int], 
                detection_result: Dict) -> Dict:
        """
        处理满层堆垛
        
        :return: {
            "total": int,  # 总箱数
            "strategy": str,  # 使用的策略
            "details": {
                "n_detected": int,  # 检测到的层数
                "n_template": int,  # 模板层数
                "template_sum": int,  # 模板总和
                "calculation": str  # 计算说明
            }
        }
        """
        n_detected = len(layers)
        n_template = len(template_layers)
        
        if n_detected == n_template:
            # 完整匹配 → 满堆
            total = sum(template_layers)
            strategy = "full_match"
            calculation = f"检测层数({n_detected}) = 模板层数({n_template}) → 使用完整模板"
        elif n_detected < n_template:
            # 少拍了上层（相机视角），但可见部分是满层
            total = sum(template_layers[:n_detected])
            strategy = "partial_visible"
            calculation = f"检测层数({n_detected}) < 模板层数({n_template}) → 使用前{n_detected}层模板"
        else:
            # 检测层数 > 模板层数（异常情况，使用模板总和）
            total = sum(template_layers)
            strategy = "exceed_template"
            calculation = f"检测层数({n_detected}) > 模板层数({n_template}) → 使用完整模板（异常）"
        
        result = {
            "total": int(total),
            "strategy": strategy,
            "details": {
                "n_detected": n_detected,
                "n_template": n_template,
                "template_sum": sum(template_layers),
                "calculation": calculation
            }
        }
        
        if self.enable_debug:
            print("\n" + "="*50)
            print("📦 满层处理模块 - 处理结果")
            print("="*50)
            print(f"🎯 处理策略: {strategy}")
            print(f"📊 检测层数: {n_detected}, 模板层数: {n_template}")
            print(f"💡 计算说明: {calculation}")
            print(f"✅ 总箱数: {total}")
            print("="*50 + "\n")
        
        return result


# 默认满层处理器实例
_default_full_processor = TemplateBasedFullProcessor()


def process_full_stack(layers: List[Dict], template_layers: List[int], 
                      detection_result: Dict,
                      processor: FullStackProcessor = None) -> Dict:
    """
    处理满层堆垛（便捷函数）
    
    :param layers: 分层结果列表
    :param template_layers: 模板层配置
    :param detection_result: 满层判断结果
    :param processor: 自定义处理器（可选，默认使用 TemplateBasedFullProcessor）
    :return: 处理结果字典
    """
    if processor is None:
        processor = _default_full_processor
    return processor.process(layers, template_layers, detection_result)


# ==================== 非满层处理器 ====================

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
                "calculation": str,  # 计算说明
                "top_layer_boxes": List[Dict],  # 顶层的所有烟箱boxes数据
                "top_layer": Dict  # 完整的顶层layer信息
            }
        }
        """
        n_detected = len(layers)
        n_template = len(template_layers)
        
        # 获取顶层layer（layers已按avg_y排序，最上层为layers[0]）
        if not layers:
            raise ValueError("layers列表为空，无法处理")
        
        top_layer = layers[0]  # 顶层layer
        top_layer_boxes = top_layer.get("boxes", [])  # 顶层的所有烟箱boxes
        print("HPHP: ", top_layer_boxes)
        top_layer_observed = len(top_layer_boxes)  # 顶层实际检测数
    
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
                "calculation": calculation,
                "top_layer_boxes": top_layer_boxes,  # 顶层的所有烟箱boxes数据
                "top_layer": top_layer  # 完整的顶层layer信息
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


# 默认非满层处理器实例
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
