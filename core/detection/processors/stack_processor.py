"""堆垛处理模块：处理满层和非满层堆垛的计数逻辑"""

import logging
from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


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
            logger.info("\n" + "="*50)
            logger.info("📦 满层处理模块 - 处理结果")
            logger.info("="*50)
            logger.info(f"🎯 处理策略: {strategy}")
            logger.info(f"📊 检测层数: {n_detected}, 模板层数: {n_template}")
            logger.info(f"💡 计算说明: {calculation}")
            logger.info(f"✅ 总箱数: {total}")
            logger.info("="*50 + "\n")
        
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
                logger.info("\n" + "=" * 50)
                logger.info("📊 开始处理深度图（非满层处理模块）...")
            
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
                    logger.info(f"ℹ️  未找到深度图: {depth_image_path}，跳过深度处理")
                return None
            
            # 加载深度图
            import cv2
            depth_img = cv2.imread(str(depth_image_path), cv2.IMREAD_UNCHANGED)
            if depth_img is None:
                if self.enable_debug:
                    logger.info(f"⚠️  无法读取深度图: {depth_image_path}，跳过深度处理")
                return None
            
            # 如果是彩色图像，转换为灰度图
            if len(depth_img.shape) == 3:
                depth_img = cv2.cvtColor(depth_img, cv2.COLOR_BGR2GRAY)
            self.depth_image = depth_img
            
            if self.enable_debug:
                logger.info(f"✅ 深度图加载成功，尺寸: {self.depth_image.shape}")
            
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
                logger.info(f"💾 已保存加载的原始深度图（旋转前）: {original_depth_path}")
                
                # 保存旋转后的深度图（仅用于调试对比，不用于处理）
                rotated_depth_filename = f"{depth_stem}_rotated_for_debug{depth_suffix}"
                rotated_depth_path = output_dir / rotated_depth_filename
                
                rotated_depth_path_str = self.depth_calculator.rotate_image(
                    str(depth_image_path),
                    rotation_angle=90,
                    output_path=str(rotated_depth_path),
                    overwrite=False
                )
                logger.info(f"💾 已保存旋转后的深度图（仅用于调试）: {rotated_depth_path_str}")
                logger.info(f"   注意：实际处理时使用原始深度图，不旋转")
            
            # 准备深度缓存目录
            depth_cache_dir = output_dir / "depth_cache"
            depth_cache_dir.mkdir(parents=True, exist_ok=True)
            
            # 计算深度矩阵（只对深度图进行split和处理，不旋转）
            # 视差图可视化保存到主output目录
            debug_output_dir = str(output_dir) if self.enable_debug else None
            if self.enable_debug:
                logger.info(f"📁 深度缓存目录: {depth_cache_dir}")
                logger.info(f"📁 视差图可视化目录: {debug_output_dir if debug_output_dir else '未设置'}")
                logger.info(f"   处理流程：直接对原始深度图进行split，不旋转")
            
            # 使用原始深度图进行处理（不旋转，直接split）
            depth_array, csv_path = self.depth_calculator.process_stereo_image(
                str(depth_image_path),  # 使用原始深度图，不旋转
                str(depth_cache_dir),
                debug_output_dir=debug_output_dir,
                skip_rotation=True  # 跳过旋转
            )
            
            # 更新深度图数组
            self.depth_image = depth_array
            
            if self.enable_debug:
                logger.info(f"✅ 深度矩阵缓存已生成: {csv_path}")
                logger.info("=" * 50 + "\n")
            
            return csv_path
                
        except Exception as e:
            if self.enable_debug:
                logger.info(f"⚠️  处理深度图时出错: {e}")
                logger.info("继续处理，但不使用深度数据...")
                import traceback
                traceback.print_exc()
            return None
        self.enable_debug = enable_debug
    
    def _calculate_top_layer_count_with_depth(self,
                                               top_layer: Dict,
                                               top_layer_boxes: List[Dict],
                                               pile_roi: Dict[str, float],
                                               pile_id: Optional[int],
                                               depth_image: Optional[np.ndarray],
                                               depth_matrix_csv_path: Optional[str]) -> int:
        """
        使用深度图 + pile JSON 配置计算顶层箱子数量。

        算法：
        1. 加载 pile_ID_{pile_id}_*.json 配置文件
        2. 提取每个顶层 box 的归一化宽度和中心点深度值
        3. 按 visible_count 分组匹配 JSON 中的 pattern
        4. 命中 pattern 后返回其 visible_count

        :param top_layer: 顶层layer信息
        :param top_layer_boxes: 顶层的所有烟箱boxes（已过滤）
        :param pile_roi: 堆垛ROI区域
        :param pile_id: 垛型ID
        :param depth_image: 深度图（可选，numpy数组）
        :param depth_matrix_csv_path: 深度矩阵CSV路径（可选）
        :return: 顶层箱子数量
        """
        import json

        # ========== Step 1: 加载 pile JSON ==========
        pile_json_path = None
        pile_patterns = None
        if pile_id is not None:
            config_dir = Path(__file__).parent.parent.parent / "config"
            for f in config_dir.glob(f"pile_ID_{pile_id}_*.json"):
                pile_json_path = f
                break

        if pile_json_path is None or not pile_json_path.exists():
            count = len(top_layer_boxes)
            logger.info(f"[PartialProcessor] 未找到pile_ID_{pile_id}对应的JSON配置，回落YOLO: {count}")
            return count

        with open(pile_json_path, "r", encoding="utf-8") as f:
            pile_patterns = json.load(f)

        logger.info(f"[PartialProcessor] 加载pile_ID={pile_id}配置: {pile_json_path.name}, 共{len(pile_patterns)}条规则")
        logger.info(f"[PartialProcessor] YOLO检测到顶层箱数: {len(top_layer_boxes)}")

        # ========== Step 2: 提取每个 box 的宽度和深度 ==========
        depth_matrix = None
        if depth_matrix_csv_path is not None and Path(depth_matrix_csv_path).exists():
            try:
                from core.detection.depth import DepthProcessor
                dp = DepthProcessor(enable_debug=self.enable_debug)
                depth_matrix = dp.load_depth_matrix(depth_matrix_csv_path)
                logger.info(f"[PartialProcessor] 深度矩阵尺寸: {depth_matrix.shape}")
            except Exception as e:
                logger.info(f"[PartialProcessor] 加载深度矩阵失败: {e}")

        if depth_matrix is None and depth_image is not None:
            depth_matrix = depth_image

        # 计算 pile 宽度
        pile_w = float(pile_roi["x2"]) - float(pile_roi["x1"])
        image_width = pile_roi.get("image_width", pile_w)
        image_height = pile_roi.get("image_height", 0)

        # 提取每个 box 的 (norm_width, depth)
        box_data = []
        for i, box in enumerate(top_layer_boxes):
            roi = box.get("roi", box)
            bx1, by1 = roi.get("x1", 0), roi.get("y1", 0)
            bx2, by2 = roi.get("x2", 0), roi.get("y2", 0)
            box_w = bx2 - bx1
            box_h = by2 - by1
            cx = (bx1 + bx2) / 2.0
            cy = (by1 + by2) / 2.0
            norm_w = box_w / pile_w if pile_w > 0 else 0

            depth_mm = None
            if depth_matrix is not None:
                cx_n = max(0.0, min(1.0, cx / image_width)) if image_width > 0 else 0
                cy_n = max(0.0, min(1.0, cy / image_height)) if image_height > 0 else 0
                if depth_matrix is not None:
                    from core.detection.depth import DepthProcessor
                    dp2 = DepthProcessor(enable_debug=False)
                    res = dp2.extract_depth_at_position(depth_matrix, cx_n, cy_n)
                    if res.get("success") and res.get("value", 0) > 0:
                        depth_mm = res["value"]

            box_data.append({
                "idx": i,
                "roi": (bx1, by1, bx2, by2),
                "width_px": box_w,
                "height_px": box_h,
                "center": (cx, cy),
                "norm_width": norm_w,
                "depth_mm": depth_mm,
            })

            logger.info(f"[PartialProcessor] box[{i}]: roi=({bx1:.0f},{by1:.0f},{bx2:.0f},{by2:.0f}), "
                        f"box_w={box_w:.0f}px, norm_w={norm_w:.4f}, depth={depth_mm:.0f}mm" if depth_mm
                        else f"[PartialProcessor] box[{i}]: box_w={box_w:.0f}px, norm_w={norm_w:.4f}, depth=None")

        # ========== Step 3: 按 visible_count 分组匹配 ==========
        detected_count = len(box_data)
        matched_pattern_id = None
        matched_visible_count = None

        # 按 visible_count 分组
        patterns_by_count = {}
        for p in pile_patterns:
            vc = p.get("visible_count", 1)
            patterns_by_count.setdefault(vc, []).append(p)

        logger.info(f"[PartialProcessor] 检测到{detected_count}个box，尝试匹配visible_count={detected_count}的patterns")
        if detected_count in patterns_by_count:
            candidates = patterns_by_count[detected_count]
            logger.info(f"[PartialProcessor] 命中{len(candidates)}条候选规则，开始逐一匹配...")
            for p in candidates:
                pid = p.get("pattern_id", "?")
                w_ranges = p.get("match", {}).get("width_ranges", [])
                d_ranges = p.get("match", {}).get("depth_ranges", [])

                logger.info(f"[PartialProcessor]   候选: {pid}, width_ranges={w_ranges}, depth_ranges={d_ranges}")

                if len(w_ranges) != detected_count or len(d_ranges) != detected_count:
                    continue

                match_ok = True
                for j, bd in enumerate(box_data):
                    w_lo, w_hi = w_ranges[j]
                    if not (w_lo <= bd["norm_width"] <= w_hi):
                        match_ok = False
                        logger.info(f"[PartialProcessor]     box[{j}] norm_w={bd['norm_width']:.4f} 不在 [{w_lo},{w_hi}]")
                        break
                    if bd["depth_mm"] is not None:
                        d_lo, d_hi = d_ranges[j]
                        if not (d_lo <= bd["depth_mm"] <= d_hi):
                            match_ok = False
                            logger.info(f"[PartialProcessor]     box[{j}] depth={bd['depth_mm']:.0f} 不在 [{d_lo},{d_hi}]")
                            break
                    else:
                        logger.info(f"[PartialProcessor]     box[{j}] depth=None，跳过深度匹配")

                if match_ok:
                    matched_pattern_id = pid
                    # 从 pattern_id 末尾提取数字作为箱数（如 single_l_3 → 3）
                    import re
                    nums = re.findall(r'\d+', pid)
                    matched_visible_count = int(nums[-1]) if nums else detected_count
                    result_ids = p.get("result_ids", [])
                    logger.info(f"[PartialProcessor] ✅ 匹配成功! pattern_id={pid}, 箱数={matched_visible_count}, result_ids={result_ids}")
                    break
        else:
            logger.info(f"[PartialProcessor] 没有visible_count={detected_count}的规则，回落YOLO检测数")

        if matched_visible_count is not None:
            logger.info(f"[PartialProcessor] 最终结果: 箱数={matched_visible_count} (pattern={matched_pattern_id}), result_ids={p.get('result_ids', [])}")
            return matched_visible_count
        else:
            logger.info(f"[PartialProcessor] 未匹配到规则，回落YOLO: {detected_count}")
            return detected_count
    
    def process(self, layers: List[Dict], template_layers: List[int],
                detection_result: Dict,
                pile_id: Optional[int] = None,
                depth_image: Optional[np.ndarray] = None,
                depth_matrix_csv_path: Optional[str] = None,
                image_path: Optional[Union[str, Path]] = None,
                output_dir: Optional[Union[str, Path]] = None) -> Dict:
        """
        处理非满层堆垛

        :param pile_id: 垛型ID（用于加载pile_ID_X.json匹配规则）
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
        # 注意：深度图处理已移到detect模块顶层（在满层判断之前）
        # 这里不再重复处理深度图，直接使用从factory传递过来的depth_matrix_csv_path

        # ========== 详细调试日志 ==========
        if self.enable_debug:
            logger.info("\n" + "="*60)
            logger.info("📦 非满层处理模块 - 输入数据")
            logger.info("="*60)
            logger.info(f"  [基本信息]")
            logger.info(f"  检测到的层数 n_detected = {len(layers)}")
            logger.info(f"  模板层数 n_template = {len(template_layers)}")
            logger.info(f"  模板层配置 template_layers = {template_layers}")
            logger.info(f"  每层箱数: {[len(l.get('boxes',[])) for l in layers]}")
            logger.info("="*60)

        n_detected = len(layers)
        n_template = len(template_layers)

        # 获取顶层layer（layers已按avg_y排序，最上层为layers[0]）
        if not layers:
            raise ValueError("layers列表为空，无法处理")

        top_layer = layers[0]  # 顶层layer
        # 注意：顶层箱子已经在满层判断时过滤过了，这里直接使用过滤后的结果
        top_layer_boxes = top_layer.get("boxes", [])  # 顶层的所有烟箱boxes（已过滤）

        # ========== 顶层 box 详情 ==========
        if self.enable_debug:
            logger.info(f"  [顶层 box 详情]  共 {len(top_layer_boxes)} 个:")
            for i, box in enumerate(top_layer_boxes):
                roi = box.get("roi", box)
                cx = (roi.get("x1",0) + roi.get("x2",0)) / 2
                cy = (roi.get("y1",0) + roi.get("y2",0)) / 2
                w = roi.get("x2",0) - roi.get("x1",0)
                h = roi.get("y2",0) - roi.get("y1",0)
                logger.info(f"    box[{i}]: roi=({roi.get('x1',0):.0f},{roi.get('y1',0):.0f},{roi.get('x2',0):.0f},{roi.get('y2',0):.0f}), 中心=({cx:.0f},{cy:.0f}), 宽高=({w:.0f}x{h:.0f})")
            logger.info("="*60)

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

        # ========== ROI 详情 ==========
        if self.enable_debug:
            pile_w = pile_roi["x2"] - pile_roi["x1"]
            pile_h = pile_roi["y2"] - pile_roi["y1"]
            logger.info(f"  [pile_roi] = ({pile_roi['x1']:.0f},{pile_roi['y1']:.0f},{pile_roi['x2']:.0f},{pile_roi['y2']:.0f})")
            logger.info(f"  pile ROI 宽度={pile_w:.0f}, 高度={pile_h:.0f}")
            logger.info("="*60)

        # 使用深度图算法计算顶层箱子数量
        top_layer_observed = self._calculate_top_layer_count_with_depth(
            top_layer=top_layer,
            top_layer_boxes=top_layer_boxes,
            pile_roi=pile_roi,
            pile_id=pile_id,
            depth_image=depth_image,
            depth_matrix_csv_path=depth_matrix_csv_path
        )

        # ========== 核心公式 ==========
        # 下层使用：检测到的层数 - 1（而非模板层数），避免模板层数 > 检测层数时多算
        if self.enable_debug:
            logger.info(f"  [核心公式]")
            logger.info(f"  公式1: lower_layers_sum = sum(template_layers[:n_detected-1])")
            logger.info(f"        = sum({template_layers[:max(0, n_detected-1)]})")
            logger.info(f"        = {sum(template_layers[:max(0, n_detected-1)])}")

        # 计算下层模板总和（排除顶层）：使用检测层数而非模板层数
        if n_detected > 1:
            lower_layers_sum = sum(template_layers[:n_detected - 1])
        else:
            lower_layers_sum = 0

        if self.enable_debug:
            logger.info(f"  公式2: top_layer_observed = {top_layer_observed}  (来自深度算法/fallback YOLO)")
            logger.info(f"  公式3: total = lower_layers_sum + top_layer_observed")
            logger.info(f"        = {lower_layers_sum} + {top_layer_observed}")
            logger.info(f"        = {lower_layers_sum + top_layer_observed}")

        # 顶层不满 → 总箱数 = 下层模板之和 + 顶层实际检测数
        total = lower_layers_sum + top_layer_observed
        
        strategy = "partial_with_template"
        calculation = (
            f"顶层不满 → 下层检测({lower_layers_sum}) + "
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
                "lower_layers_count": n_detected - 1,  # 下层层数（排除顶层）
                "top_layer_boxes": top_layer_boxes,  # 顶层的所有烟箱boxes数据
                "top_layer": top_layer  # 完整的顶层layer信息
            }
        }
        
        if self.enable_debug:
            logger.info("\n" + "="*50)
            logger.info("📦 非满层处理模块 - 处理结果")
            logger.info("="*50)
            logger.info(f"🎯 处理策略: {strategy}")
            logger.info(f"📊 检测层数: {n_detected}, 模板层数: {n_template}")
            logger.info(f"🔝 顶层实际检测数: {top_layer_observed}")
            logger.info(f"📉 下层检测层数: {n_detected - 1}, 下层模板总和: {lower_layers_sum}")
            logger.info(f"💡 计算说明: {calculation}")
            logger.info(f"✅ 总箱数: {total}")
            logger.info("="*50 + "\n")
        
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
    单层 → 使用深度算法计算箱子数量（复用partial_processor的深度匹配逻辑）
    """

    def __init__(self, enable_debug: bool = True):
        """
        :param enable_debug: 是否启用调试输出
        """
        self.enable_debug = enable_debug

    # ===== 以下为旧逻辑（已注释，用深度算法替代）=====
    # 旧逻辑：使用top类检测框数量来计算单层箱数
    #   - 从yolo_detections中筛选cls=="top"的检测框
    #   - 只保留中心点在pile_roi内的top框
    #   - total = len(top_boxes)（或fallback到len(layer_boxes)）
    # 问题：top类检测不稳定，导致计数不准
    # ==================================================

    def process(self, layers: List[Dict], template_layers: List[int],
                detection_result: Dict,
                pile_id: Optional[int] = None,
                depth_image: Optional[np.ndarray] = None,
                depth_matrix_csv_path: Optional[str] = None) -> Dict:
        """
        处理单层堆垛（使用深度算法计算）

        :param pile_id: 垛型ID（用于加载pile_ID_X.json匹配规则）
        :param depth_image: 深度图（可选，numpy数组）
        :param depth_matrix_csv_path: 深度矩阵CSV路径（可选）
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
                logger.info(f"⚠️  警告：单层处理器接收到 {n_detected} 层，预期为1层")

        layer = layers[0]  # 唯一的layer
        layer_boxes = layer.get("boxes", [])  # 所有烟箱boxes（已过滤）

        # 从detection_result中获取pile_roi（如果存在），否则从layers推断
        pile_roi = detection_result.get("pile_roi")
        if pile_roi is None:
            if layer_boxes:
                x_coords, y_coords = [], []
                for box in layer_boxes:
                    if "roi" in box:
                        x_coords.extend([box["roi"]["x1"], box["roi"]["x2"]])
                        y_coords.extend([box["roi"]["y1"], box["roi"]["y2"]])
                    else:
                        x_coords.extend([box["x1"], box["x2"]])
                        y_coords.extend([box["y1"], box["y2"]])
                if x_coords and y_coords:
                    pile_roi = {"x1": min(x_coords), "y1": min(y_coords),
                                 "x2": max(x_coords), "y2": max(y_coords)}
                else:
                    pile_roi = {"x1": 0, "y1": 0, "x2": 1000, "y2": 1000}
            else:
                pile_roi = {"x1": 0, "y1": 0, "x2": 1000, "y2": 1000}

        # ========== 使用深度算法计算顶层箱子数量（复用partial_processor的逻辑）==========
        # 创建partial_processor实例用于调用深度计算
        partial = TemplateBasedPartialProcessor(enable_debug=self.enable_debug)
        top_layer_observed = partial._calculate_top_layer_count_with_depth(
            top_layer=layer,
            top_layer_boxes=layer_boxes,
            pile_roi=pile_roi,
            pile_id=pile_id,
            depth_image=depth_image,
            depth_matrix_csv_path=depth_matrix_csv_path
        )

        total = top_layer_observed
        strategy = "single_layer_with_depth"
        calculation = f"单层堆垛 → 深度算法计算箱数: {total} 个箱子"

        result = {
            "total": int(total),
            "strategy": strategy,
            "details": {
                "n_detected": n_detected,
                "n_template": n_template,
                "observed": top_layer_observed,
                "calculation": calculation,
                "layer_boxes": layer_boxes,
                "layer": layer
            }
        }

        if self.enable_debug:
            logger.info("\n" + "="*50)
            logger.info("📦 单层处理模块 - 处理结果")
            logger.info("="*50)
            logger.info(f"🎯 处理策略: {strategy}")
            logger.info(f"📊 检测层数: {n_detected}, 模板层数: {n_template}")
            logger.info(f"📦 深度算法箱数: {top_layer_observed}")
            logger.info(f"💡 计算说明: {calculation}")
            logger.info(f"✅ 总箱数: {total}")
            logger.info("="*50 + "\n")

        return result


# 默认单层处理器实例
_default_single_layer_processor = TemplateBasedSingleLayerProcessor()


def process_single_layer(layers: List[Dict], template_layers: List[int],
                        detection_result: Dict,
                        processor: SingleLayerProcessor = None,
                        pile_id: Optional[int] = None,
                        depth_image: Optional[np.ndarray] = None,
                        depth_matrix_csv_path: Optional[str] = None) -> Dict:
    """
    处理单层堆垛（便捷函数）

    :param layers: 分层结果列表
    :param template_layers: 模板层配置
    :param detection_result: 满层判断结果
    :param processor: 自定义处理器（可选，默认使用 TemplateBasedSingleLayerProcessor）
    :param pile_id: 垛型ID
    :param depth_image: 深度图（可选，numpy数组）
    :param depth_matrix_csv_path: 深度矩阵CSV路径（可选）
    :return: 处理结果字典
    """
    if processor is None:
        processor = _default_single_layer_processor
    return processor.process(layers, template_layers, detection_result,
                               pile_id=pile_id, depth_image=depth_image,
                               depth_matrix_csv_path=depth_matrix_csv_path)
