"""堆垛处理模块：处理满层和非满层堆垛的计数逻辑"""

from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod
import numpy as np
from pathlib import Path


# ==================== 满层处理器 ====================

class FullStackProcessor(ABC):
    """满层堆垛处理器抽象基类"""
    
    @abstractmethod
    def process(self, layers: List[Dict], template_layers: List[int], 
                detection_result: Dict, 
                depth_image: Optional[np.ndarray] = None,
                depth_matrix_csv_path: Optional[str] = None) -> Dict:
        """
        处理满层堆垛，计算总箱数
        
        :param layers: 分层结果列表
        :param template_layers: 模板层配置（每层期望的箱数）
        :param detection_result: 满层判断结果
        :param depth_image: 深度图（可选，numpy数组）
        :param depth_matrix_csv_path: 深度矩阵CSV路径（可选，从深度处理中获取）
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
                detection_result: Dict, 
                depth_image: Optional[np.ndarray] = None,
                depth_matrix_csv_path: Optional[str] = None) -> Dict:
        """
        处理满层堆垛
        
        :param depth_image: 深度图（可选，numpy数组）
        :param depth_matrix_csv_path: 深度矩阵CSV路径（可选）
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
                      depth_image: Optional[np.ndarray] = None,
                      depth_matrix_csv_path: Optional[str] = None) -> Dict:
    """
    处理满层堆垛（便捷函数）
    
    :param layers: 分层结果列表
    :param template_layers: 模板层配置
    :param detection_result: 满层判断结果
    :param processor: 自定义处理器（可选，默认使用 TemplateBasedFullProcessor）
    :param depth_image: 深度图（可选，numpy数组）
    :param depth_matrix_csv_path: 深度矩阵CSV路径（可选）
    :return: 处理结果字典
    """
    if processor is None:
        processor = _default_full_processor
    return processor.process(layers, template_layers, detection_result, 
                            depth_image=depth_image,
                            depth_matrix_csv_path=depth_matrix_csv_path)


# ==================== 非满层处理器 ====================

class PartialStackProcessor(ABC):
    """非满层堆垛处理器抽象基类"""
    
    @abstractmethod
    def process(self, layers: List[Dict], template_layers: List[int], 
                detection_result: Dict, 
                depth_image: Optional[np.ndarray] = None,
                depth_matrix_csv_path: Optional[str] = None,
                image_path: Optional[Union[str, Path]] = None,
                output_dir: Optional[Union[str, Path]] = None) -> Dict:
        """
        处理非满层堆垛，计算总箱数
        
        :param layers: 分层结果列表
        :param template_layers: 模板层配置（每层期望的箱数）
        :param detection_result: 满层判断结果
        :param depth_image: 深度图（可选，numpy数组）
        :param depth_matrix_csv_path: 深度矩阵CSV路径（可选，从满层检测缓存中获取）
        :param image_path: 图像路径（可选，用于深度图处理）
        :param output_dir: 输出目录（可选，用于保存深度图处理结果）
        :return: 处理结果字典，包含 total(int), details(dict) 等
        """
        pass


class TemplateBasedPartialProcessor(PartialStackProcessor):
    """
    基于模板的非满层处理器（当前默认实现）
    
    处理逻辑：
    顶层不满 → 总箱数 = 下层模板之和 + 顶层实际检测数
    """
    
    def __init__(self, enable_debug: bool = True, depth_calculator=None):
        """
        :param enable_debug: 是否启用调试输出
        :param depth_calculator: 深度计算器实例（可选，用于深度图处理）
        """
        self.enable_debug = enable_debug
        self.depth_calculator = depth_calculator
        self.depth_image_path_for_processing = None
        self.depth_image = None
    
    def _process_depth_image(self, image_path: Union[str, Path],
                             output_dir: Optional[Union[str, Path]]) -> Optional[str]:
        """
        处理深度图：生成深度矩阵缓存
        
        :param image_path: 原始图像路径（RGB图像，已旋转）
        :param output_dir: 输出目录（用于保存视差图可视化）
        :return: 深度矩阵CSV路径（如果成功），否则返回None
        """
        if self.depth_calculator is None:
            return None
            
        try:
            if self.enable_debug:
                print("\n" + "=" * 50)
                print("📊 开始处理深度图（非满层处理模块）...")
            
            # 检查是否有深度图路径（需要从factory传递）
            # 这里我们需要从image_path推断深度图路径
            image_path_obj = Path(image_path) if not isinstance(image_path, Path) else image_path
            image_stem = image_path_obj.stem
            image_suffix = image_path_obj.suffix
            
            # 移除可能的 "_rotated" 后缀，获取原始图像名
            if image_stem.endswith("_rotated"):
                original_stem = image_stem[:-8]  # 移除 "_rotated"
            else:
                original_stem = image_stem
            
            # 生成深度图路径：原始图名 + "d" + 扩展名
            depth_image_path = image_path_obj.parent / f"{original_stem}d{image_suffix}"
            
            if not depth_image_path.exists():
                if self.enable_debug:
                    print(f"ℹ️  未找到深度图: {depth_image_path}，跳过深度处理")
                return None
            
            # 加载深度图
            import cv2
            depth_img = cv2.imread(str(depth_image_path), cv2.IMREAD_UNCHANGED)
            if depth_img is None:
                if self.enable_debug:
                    print(f"⚠️  无法读取深度图: {depth_image_path}，跳过深度处理")
                return None
            
            # 如果是彩色图像，转换为灰度图
            if len(depth_img.shape) == 3:
                depth_img = cv2.cvtColor(depth_img, cv2.COLOR_BGR2GRAY)
            self.depth_image = depth_img
            
            if self.enable_debug:
                print(f"✅ 深度图加载成功，尺寸: {self.depth_image.shape}")
            
            # 准备输出目录
            if output_dir is None:
                output_dir = image_path_obj.parent
            else:
                output_dir = Path(output_dir)
            
            # 在debug模式下，保存深度图旋转前后的版本（用于调试对比）
            if self.enable_debug:
                depth_stem = depth_image_path.stem
                depth_suffix = depth_image_path.suffix
                
                # 保存加载的原始深度图（旋转前）
                original_depth_path = output_dir / f"{depth_stem}_loaded_original{depth_suffix}"
                cv2.imwrite(str(original_depth_path), self.depth_image)
                print(f"💾 已保存加载的原始深度图（旋转前）: {original_depth_path}")
                
                # 保存旋转后的深度图（仅用于调试对比，不用于处理）
                rotated_depth_filename = f"{depth_stem}_rotated_for_debug{depth_suffix}"
                rotated_depth_path = output_dir / rotated_depth_filename
                
                rotated_depth_path_str = self.depth_calculator.rotate_image(
                    str(depth_image_path),
                    rotation_angle=-90,
                    output_path=str(rotated_depth_path),
                    overwrite=False
                )
                print(f"💾 已保存旋转后的深度图（仅用于调试）: {rotated_depth_path_str}")
                print(f"   注意：实际处理时使用原始深度图，不旋转")
            
            # 准备深度缓存目录
            depth_cache_dir = output_dir / "depth_cache"
            depth_cache_dir.mkdir(parents=True, exist_ok=True)
            
            # 计算深度矩阵（直接处理深度图，不旋转，不分割）
            # 视差图可视化保存到主output目录
            debug_output_dir = str(output_dir) if self.enable_debug else None
            if self.enable_debug:
                print(f"📁 深度缓存目录: {depth_cache_dir}")
                print(f"📁 视差图可视化目录: {debug_output_dir if debug_output_dir else '未设置'}")
                print(f"   处理流程：分割深度图，旋转，然后处理左上深度图")
            
            # 使用深度图进行处理（分割、旋转，然后处理左上）
            depth_array, csv_path = self.depth_calculator.process_depth_image(
                str(depth_image_path),  # 深度图（立体图像格式，需要分割）
                str(depth_cache_dir),
                debug_output_dir=debug_output_dir,
                skip_rotation=False,  # 需要旋转
                split_image=True  # 需要分割（深度图是立体图像格式）
            )
            
            # 更新深度图数组
            self.depth_image = depth_array
            
            if self.enable_debug:
                print(f"✅ 深度矩阵缓存已生成: {csv_path}")
                print("=" * 50 + "\n")
            
            return csv_path
                
        except Exception as e:
            if self.enable_debug:
                print(f"⚠️  处理深度图时出错: {e}")
                print("继续处理，但不使用深度数据...")
                import traceback
                traceback.print_exc()
            return None
        self.enable_debug = enable_debug
    
    def _calculate_top_layer_count_with_depth(self, 
                                               top_layer: Dict,
                                               top_layer_boxes: List[Dict],
                                               pile_roi: Dict[str, float],
                                               depth_image: Optional[np.ndarray],
                                               depth_matrix_csv_path: Optional[str]) -> int:
        """
        使用深度图计算最高层的箱子数量
        
        算法思路：
        1. 如果提供了深度矩阵CSV路径，优先使用CSV数据
        2. 如果提供了深度图数组，使用深度信息进行更精确的计算
        3. 如果没有深度数据，则使用检测到的箱子数量
        
        :param top_layer: 顶层layer信息
        :param top_layer_boxes: 顶层的所有烟箱boxes（已过滤）
        :param pile_roi: 堆垛ROI区域
        :param depth_image: 深度图（可选，numpy数组）
        :param depth_matrix_csv_path: 深度矩阵CSV路径（可选，从满层检测缓存中获取）
        :return: 计算出的顶层箱子数量
        """
        # 如果没有深度数据，直接返回检测到的箱子数量
        if depth_image is None and depth_matrix_csv_path is None:
            count = len(top_layer_boxes)
            if self.enable_debug:
                print(f"📊 未提供深度数据，使用检测结果: {count} 个箱子")
            return count
        
        # 优先使用深度矩阵CSV（如果存在）
        if depth_matrix_csv_path is not None and Path(depth_matrix_csv_path).exists():
            if self.enable_debug:
                print(f"📊 使用深度矩阵CSV缓存: {depth_matrix_csv_path}")
            
            try:
                from core.detection.depth import DepthProcessor
                depth_processor = DepthProcessor(enable_debug=self.enable_debug)
                
                # 加载深度矩阵以获取图像尺寸
                depth_matrix = depth_processor.load_depth_matrix(depth_matrix_csv_path)
                depth_height, depth_width = depth_matrix.shape
                
                # 获取原始图像尺寸（从pile_roi推断，或使用深度矩阵尺寸）
                # 注意：pile_roi中的坐标是像素坐标，需要知道原始图像尺寸来归一化
                # 如果pile_roi中没有图像尺寸信息，使用深度矩阵尺寸作为参考
                image_width = pile_roi.get("image_width", depth_width)
                image_height = pile_roi.get("image_height", depth_height)
                
                if self.enable_debug:
                    print(f"📊 深度矩阵尺寸: {depth_width}x{depth_height}, "
                          f"图像尺寸: {image_width}x{image_height}")
                
                # 对每个顶层box的中心点提取深度值
                depth_values = []
                for box in top_layer_boxes:
                    # 获取box的中心点（像素坐标）
                    if "roi" in box:
                        box_x1, box_y1 = box["roi"]["x1"], box["roi"]["y1"]
                        box_x2, box_y2 = box["roi"]["x2"], box["roi"]["y2"]
                    else:
                        box_x1, box_y1 = box["x1"], box["y1"]
                        box_x2, box_y2 = box["x2"], box["y2"]
                    
                    # 计算中心点（归一化坐标）
                    center_x_norm = (box_x1 + box_x2) / 2.0 / image_width
                    center_y_norm = (box_y1 + box_y2) / 2.0 / image_height
                    
                    # 确保归一化坐标在[0, 1]范围内
                    center_x_norm = max(0.0, min(1.0, center_x_norm))
                    center_y_norm = max(0.0, min(1.0, center_y_norm))
                    
                    # 提取深度值
                    result = depth_processor.extract_depth_at_position(
                        depth_matrix,
                        center_x_norm,
                        center_y_norm
                    )
                    
                    if result["success"] and result["value"] > 0:
                        depth_values.append(result["value"])
                
                if self.enable_debug:
                    print(f"📊 从深度矩阵CSV提取到 {len(depth_values)} 个有效深度值")
                    if depth_values:
                        print(f"   深度值范围: {min(depth_values):.1f} - {max(depth_values):.1f} mm")
                
                # 当前实现：使用检测结果，深度数据可用于后续验证
                # TODO: 可以基于深度值进行更精确的计数
                base_count = len(top_layer_boxes)
                
            except Exception as e:
                if self.enable_debug:
                    print(f"⚠️  读取深度矩阵CSV时出错: {e}，回退使用检测结果")
                base_count = len(top_layer_boxes)
        elif depth_image is not None:
            # 使用深度图数组进行计算
            if self.enable_debug:
                print(f"📊 使用深度图数组计算顶层箱子数量，深度图尺寸: {depth_image.shape}")
            
            base_count = len(top_layer_boxes)
            
            # 示例：可以在这里添加深度图分析逻辑
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
        else:
            base_count = len(top_layer_boxes)
        
        # 当前返回检测到的数量，后续可以基于深度数据分析结果进行调整
        return base_count
    
    def process(self, layers: List[Dict], template_layers: List[int], 
                detection_result: Dict, 
                depth_image: Optional[np.ndarray] = None,
                depth_matrix_csv_path: Optional[str] = None,
                image_path: Optional[Union[str, Path]] = None,
                output_dir: Optional[Union[str, Path]] = None) -> Dict:
        """
        处理非满层堆垛
        
        :param depth_image: 深度图（可选，numpy数组）
        :param depth_matrix_csv_path: 深度矩阵CSV路径（可选，从满层检测缓存中获取）
        :param image_path: 图像路径（可选，用于深度图处理）
        :param output_dir: 输出目录（可选，用于保存深度图处理结果）
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
        # Step 0: 处理深度图（如果提供了深度计算器和图像路径）
        if self.depth_calculator is not None and image_path is not None:
            processed_csv_path = self._process_depth_image(image_path, output_dir)
            if processed_csv_path:
                # 更新depth_matrix_csv_path
                depth_matrix_csv_path = processed_csv_path
        
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
            depth_image=depth_image,
            depth_matrix_csv_path=depth_matrix_csv_path
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
                         depth_image: Optional[np.ndarray] = None,
                         depth_matrix_csv_path: Optional[str] = None,
                         image_path: Optional[Union[str, Path]] = None,
                         output_dir: Optional[Union[str, Path]] = None) -> Dict:
    """
    处理非满层堆垛（便捷函数）
    
    :param layers: 分层结果列表
    :param template_layers: 模板层配置
    :param detection_result: 满层判断结果
    :param processor: 自定义处理器（可选，默认使用 TemplateBasedPartialProcessor）
    :param depth_image: 深度图（可选，numpy数组）
    :param depth_matrix_csv_path: 深度矩阵CSV路径（可选，从满层检测缓存中获取）
    :param image_path: 图像路径（可选，用于深度图处理）
    :param output_dir: 输出目录（可选，用于保存深度图处理结果）
    :return: 处理结果字典
    """
    if processor is None:
        processor = _default_partial_processor
    return processor.process(layers, template_layers, detection_result, 
                            depth_image=depth_image,
                            depth_matrix_csv_path=depth_matrix_csv_path,
                            image_path=image_path,
                            output_dir=output_dir)


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
    单层 → 总箱数 = YOLO识别的top类数量（对于单层场景，使用top类的检测框数量）
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
                "observed": int,  # 实际检测数（top类数量）
                "calculation": str,  # 计算说明
                "layer_boxes": List[Dict],  # 所有烟箱boxes数据
                "top_boxes": List[Dict],  # YOLO识别的top类检测框
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
        
        # 从detection_result中获取原始YOLO检测结果
        yolo_detections = detection_result.get("yolo_detections", [])
        
        # 筛选出top类的检测框
        top_boxes = []
        if yolo_detections:
            # 筛选出类别为"top"的检测框
            top_boxes = [det for det in yolo_detections if det.get("cls") == "top"]
            
            # 如果提供了pile_roi，只保留在pile_roi内的top类检测框
            if pile_roi and top_boxes:
                filtered_top_boxes = []
                for det in top_boxes:
                    xc = 0.5 * (det["x1"] + det["x2"])
                    yc = 0.5 * (det["y1"] + det["y2"])
                    if (pile_roi["x1"] <= xc <= pile_roi["x2"] and 
                        pile_roi["y1"] <= yc <= pile_roi["y2"]):
                        filtered_top_boxes.append(det)
                top_boxes = filtered_top_boxes
        
        # 单层场景：使用top类的数量作为箱子数量
        if top_boxes:
            observed = len(top_boxes)
            strategy = "single_layer_with_top_class"
            calculation = f"单层堆垛 → 使用YOLO识别的top类数量: {observed} 个箱子"
            if self.enable_debug:
                print(f"📊 单层场景：从YOLO检测结果中提取到 {observed} 个top类检测框")
        else:
            # 如果没有找到top类，回退到使用layer_boxes的数量
            observed = len(layer_boxes)
            strategy = "single_layer_fallback"
            calculation = f"单层堆垛 → 未找到top类，回退使用layer_boxes数量: {observed} 个箱子"
            if self.enable_debug:
                print(f"⚠️  未找到top类检测框，回退使用layer_boxes数量: {observed}")
        
        # 单层 → 总箱数 = top类的数量（如果找到）或layer_boxes的数量（回退）
        total = observed
        
        result = {
            "total": int(total),
            "strategy": strategy,
            "details": {
                "n_detected": n_detected,
                "n_template": n_template,
                "observed": observed,
                "calculation": calculation,
                "layer_boxes": layer_boxes,  # 所有烟箱boxes数据
                "top_boxes": top_boxes,  # YOLO识别的top类检测框
                "layer": layer  # 完整的layer信息
            }
        }
        
        if self.enable_debug:
            print("\n" + "="*50)
            print("📦 单层处理模块 - 处理结果")
            print("="*50)
            print(f"🎯 处理策略: {strategy}")
            print(f"📊 检测层数: {n_detected}, 模板层数: {n_template}")
            print(f"📦 top类检测数: {observed}")
            if top_boxes:
                print(f"🔝 YOLO识别的top类检测框数量: {len(top_boxes)}")
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
