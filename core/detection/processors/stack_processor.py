"""堆垛处理模块：处理满层和非满层堆垛的计数逻辑"""

from typing import Dict, List, Optional
from abc import ABC, abstractmethod
import numpy as np


# ==================== 满层处理器 ====================

class FullStackProcessor(ABC):
    """满层堆垛处理器抽象基类"""
    
    @abstractmethod
    def process(self, layers: List[Dict], template_layers: List[int], 
                detection_result: Dict, depth_image: Optional[np.ndarray] = None) -> Dict:
        """
        处理满层堆垛，计算总箱数
        
        :param layers: 分层结果列表
        :param template_layers: 模板层配置（每层期望的箱数）
        :param detection_result: 满层判断结果
        :param depth_image: 深度图（可选，numpy数组）
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
                detection_result: Dict, depth_image: Optional[np.ndarray] = None) -> Dict:
        """
        处理满层堆垛
        
        :param depth_image: 深度图（可选，numpy数组）
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
                      processor: FullStackProcessor = None,
                      depth_image: Optional[np.ndarray] = None) -> Dict:
    """
    处理满层堆垛（便捷函数）
    
    :param layers: 分层结果列表
    :param template_layers: 模板层配置
    :param detection_result: 满层判断结果
    :param processor: 自定义处理器（可选，默认使用 TemplateBasedFullProcessor）
    :param depth_image: 深度图（可选，numpy数组）
    :return: 处理结果字典
    """
    if processor is None:
        processor = _default_full_processor
    return processor.process(layers, template_layers, detection_result, depth_image)


# ==================== 非满层处理器 ====================

class PartialStackProcessor(ABC):
    """非满层堆垛处理器抽象基类"""
    
    @abstractmethod
    def process(self, layers: List[Dict], template_layers: List[int], 
                detection_result: Dict, depth_image: Optional[np.ndarray] = None) -> Dict:
        """
        处理非满层堆垛，计算总箱数
        
        :param layers: 分层结果列表
        :param template_layers: 模板层配置（每层期望的箱数）
        :param detection_result: 满层判断结果
        :param depth_image: 深度图（可选，numpy数组）
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
    
    def _calculate_top_layer_count_with_depth(self, 
                                               top_layer: Dict,
                                               top_layer_boxes: List[Dict],
                                               pile_roi: Dict[str, float],
                                               depth_image: Optional[np.ndarray]) -> int:
        """
        使用深度图计算最高层的箱子数量
        
        算法思路：
        1. 如果提供了深度图，使用深度信息进行更精确的计算
        2. 可以结合深度图的深度值、箱子位置等信息来验证或修正检测结果
        3. 如果没有深度图，则使用检测到的箱子数量
        
        :param top_layer: 顶层layer信息
        :param top_layer_boxes: 顶层的所有烟箱boxes（已过滤）
        :param pile_roi: 堆垛ROI区域
        :param depth_image: 深度图（可选，numpy数组）
        :return: 计算出的顶层箱子数量
        """
        # 如果没有深度图，直接返回检测到的箱子数量
        if depth_image is None:
            count = len(top_layer_boxes)
            if self.enable_debug:
                print(f"📊 未提供深度图，使用检测结果: {count} 个箱子")
            return count
        
        # 使用深度图进行更精确的计算
        if self.enable_debug:
            print(f"📊 使用深度图计算顶层箱子数量，深度图尺寸: {depth_image.shape}")
        
        # TODO: 在这里实现基于深度图的算法
        # 可能的算法思路：
        # 1. 提取顶层ROI区域的深度值
        # 2. 根据深度值的分布或变化来识别箱子边界
        # 3. 结合检测到的boxes位置，使用深度信息进行验证或补充
        # 4. 可以检测深度值的突变点来识别箱子之间的间隙
        
        # 当前实现：如果有深度图，先使用检测结果，后续可以扩展算法
        base_count = len(top_layer_boxes)
        
        # 示例：可以在这里添加深度图分析逻辑
        # 例如：分析顶层ROI区域的深度分布
        if len(top_layer_boxes) > 0:
            # 获取顶层ROI区域
            top_layer_roi = top_layer.get("roi", {})
            if top_layer_roi:
                y_top = int(top_layer_roi.get("y_top", pile_roi["y1"]))
                y_bottom = int(top_layer_roi.get("y_bottom", pile_roi["y2"]))
                x_left = int(pile_roi["x1"])
                x_right = int(pile_roi["x2"])
                
                # 确保索引在深度图范围内
                if (0 <= y_top < depth_image.shape[0] and 
                    0 <= y_bottom < depth_image.shape[0] and
                    0 <= x_left < depth_image.shape[1] and
                    0 <= x_right < depth_image.shape[1]):
                    
                    # 提取顶层区域的深度值
                    depth_roi = depth_image[y_top:y_bottom, x_left:x_right]
                    
                    if self.enable_debug:
                        print(f"📊 顶层深度ROI: 尺寸={depth_roi.shape}, "
                              f"平均深度={np.mean(depth_roi):.2f}, "
                              f"深度范围=[{np.min(depth_roi):.2f}, {np.max(depth_roi):.2f}]")
                    
                    # TODO: 在这里实现具体的深度图分析算法
                    # 例如：
                    # - 分析深度值的分布
                    # - 检测深度突变点（箱子边界）
                    # - 结合检测到的boxes位置进行验证
                    # - 使用深度信息补充遗漏的箱子
        
        # 当前返回检测到的数量，后续可以基于深度图分析结果进行调整
        return base_count
    
    def process(self, layers: List[Dict], template_layers: List[int], 
                detection_result: Dict, depth_image: Optional[np.ndarray] = None) -> Dict:
        """
        处理非满层堆垛
        
        :param depth_image: 深度图（可选，numpy数组）
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
        # 注意：顶层箱子已经在满层判断时过滤过了，这里直接使用过滤后的结果
        top_layer_boxes = top_layer.get("boxes", [])  # 顶层的所有烟箱boxes（已过滤）
        
        # 从detection_result中获取pile_roi（如果存在），否则从layers推断
        # 注意：如果factory中传递了pile_roi，应该添加到detection_result中
        pile_roi = detection_result.get("pile_roi")
        if pile_roi is None:
            # 如果没有pile_roi，尝试从顶层boxes推断一个基本的ROI
            if top_layer_boxes:
                x_coords = []
                y_coords = []
                for box in top_layer_boxes:
                    if "roi" in box:
                        x_coords.extend([box["roi"]["x1"], box["roi"]["x2"]])
                        y_coords.extend([box["roi"]["y1"], box["roi"]["y2"]])
                    else:
                        x_coords.extend([box["x1"], box["x2"]])
                        y_coords.extend([box["y1"], box["y2"]])
                if x_coords and y_coords:
                    pile_roi = {
                        "x1": min(x_coords),
                        "y1": min(y_coords),
                        "x2": max(x_coords),
                        "y2": max(y_coords)
                    }
                else:
                    pile_roi = {"x1": 0, "y1": 0, "x2": 1000, "y2": 1000}  # 默认值
            else:
                pile_roi = {"x1": 0, "y1": 0, "x2": 1000, "y2": 1000}  # 默认值
        
        # 使用深度图算法计算顶层箱子数量
        top_layer_observed = self._calculate_top_layer_count_with_depth(
            top_layer=top_layer,
            top_layer_boxes=top_layer_boxes,
            pile_roi=pile_roi,
            depth_image=depth_image
        )
    
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
                         processor: PartialStackProcessor = None,
                         depth_image: Optional[np.ndarray] = None) -> Dict:
    """
    处理非满层堆垛（便捷函数）
    
    :param layers: 分层结果列表
    :param template_layers: 模板层配置
    :param detection_result: 满层判断结果
    :param processor: 自定义处理器（可选，默认使用 TemplateBasedPartialProcessor）
    :param depth_image: 深度图（可选，numpy数组）
    :return: 处理结果字典
    """
    if processor is None:
        processor = _default_partial_processor
    return processor.process(layers, template_layers, detection_result, depth_image)


# ==================== 单层处理器 ====================

class SingleLayerProcessor(ABC):
    """单层堆垛处理器抽象基类"""
    
    @abstractmethod
    def process(self, layers: List[Dict], template_layers: List[int], 
                detection_result: Dict, depth_image: Optional[np.ndarray] = None) -> Dict:
        """
        处理单层堆垛，计算总箱数
        
        :param layers: 分层结果列表（只有一层）
        :param template_layers: 模板层配置（每层期望的箱数）
        :param detection_result: 满层判断结果
        :param depth_image: 深度图（可选，numpy数组）
        :return: 处理结果字典，包含 total(int), details(dict) 等
        """
        pass


class TemplateBasedSingleLayerProcessor(SingleLayerProcessor):
    """
    基于模板的单层处理器（当前默认实现）
    
    处理逻辑：
    单层 → 总箱数 = 实际检测数（直接使用检测到的箱子数量）
    """
    
    def __init__(self, enable_debug: bool = True):
        """
        :param enable_debug: 是否启用调试输出
        """
        self.enable_debug = enable_debug
    
    def process(self, layers: List[Dict], template_layers: List[int], 
                detection_result: Dict, depth_image: Optional[np.ndarray] = None) -> Dict:
        """
        处理单层堆垛
        
        :param depth_image: 深度图（可选，numpy数组）
        :return: {
            "total": int,  # 总箱数
            "strategy": str,  # 使用的策略
            "details": {
                "n_detected": int,  # 检测到的层数（应该为1）
                "n_template": int,  # 模板层数
                "observed": int,  # 实际检测数
                "calculation": str,  # 计算说明
                "layer_boxes": List[Dict],  # 所有烟箱boxes数据
                "layer": Dict  # 完整的layer信息
            }
        }
        """
        n_detected = len(layers)
        n_template = len(template_layers)
        
        # 获取单层layer
        if not layers:
            raise ValueError("layers列表为空，无法处理")
        
        if n_detected != 1:
            if self.enable_debug:
                print(f"⚠️  警告：单层处理器接收到 {n_detected} 层，预期为1层")
        
        layer = layers[0]  # 唯一的layer
        # 注意：顶层箱子已经在满层判断时过滤过了，这里直接使用过滤后的结果
        layer_boxes = layer.get("boxes", [])  # 所有烟箱boxes（已过滤）
        
        # 从detection_result中获取pile_roi（如果存在），否则从layers推断
        pile_roi = detection_result.get("pile_roi")
        if pile_roi is None:
            # 如果没有pile_roi，尝试从boxes推断一个基本的ROI
            if layer_boxes:
                x_coords = []
                y_coords = []
                for box in layer_boxes:
                    if "roi" in box:
                        x_coords.extend([box["roi"]["x1"], box["roi"]["x2"]])
                        y_coords.extend([box["roi"]["y1"], box["roi"]["y2"]])
                    else:
                        x_coords.extend([box["x1"], box["x2"]])
                        y_coords.extend([box["y1"], box["y2"]])
                if x_coords and y_coords:
                    pile_roi = {
                        "x1": min(x_coords),
                        "y1": min(y_coords),
                        "x2": max(x_coords),
                        "y2": max(y_coords)
                    }
                else:
                    pile_roi = {"x1": 0, "y1": 0, "x2": 1000, "y2": 1000}  # 默认值
            else:
                pile_roi = {"x1": 0, "y1": 0, "x2": 1000, "y2": 1000}  # 默认值
        
        # 单层直接使用检测到的箱子数量
        observed = len(layer_boxes)
        
        # 如果提供了深度图，可以在这里使用深度信息进行辅助判断
        if depth_image is not None:
            if self.enable_debug:
                print(f"📊 单层处理接收到深度图，尺寸: {depth_image.shape}")
            # TODO: 后续可以在这里使用深度图进行更精确的计算
        
        # 单层 → 总箱数 = 实际检测数
        total = observed
        
        strategy = "single_layer_direct"
        calculation = f"单层堆垛 → 直接使用检测结果: {observed} 个箱子"
        
        result = {
            "total": int(total),
            "strategy": strategy,
            "details": {
                "n_detected": n_detected,
                "n_template": n_template,
                "observed": observed,
                "calculation": calculation,
                "layer_boxes": layer_boxes,  # 所有烟箱boxes数据
                "layer": layer  # 完整的layer信息
            }
        }
        
        if self.enable_debug:
            print("\n" + "="*50)
            print("📦 单层处理模块 - 处理结果")
            print("="*50)
            print(f"🎯 处理策略: {strategy}")
            print(f"📊 检测层数: {n_detected}, 模板层数: {n_template}")
            print(f"📦 实际检测数: {observed}")
            print(f"💡 计算说明: {calculation}")
            print(f"✅ 总箱数: {total}")
            print("="*50 + "\n")
        
        return result


# 默认单层处理器实例
_default_single_layer_processor = TemplateBasedSingleLayerProcessor()


def process_single_layer(layers: List[Dict], template_layers: List[int], 
                        detection_result: Dict,
                        processor: SingleLayerProcessor = None,
                        depth_image: Optional[np.ndarray] = None) -> Dict:
    """
    处理单层堆垛（便捷函数）
    
    :param layers: 分层结果列表
    :param template_layers: 模板层配置
    :param detection_result: 满层判断结果
    :param processor: 自定义处理器（可选，默认使用 TemplateBasedSingleLayerProcessor）
    :param depth_image: 深度图（可选，numpy数组）
    :return: 处理结果字典
    """
    if processor is None:
        processor = _default_single_layer_processor
    return processor.process(layers, template_layers, detection_result, depth_image)
