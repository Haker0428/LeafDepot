"""满层判断模块：可独立调试的满层判定逻辑"""

import numpy as np
from typing import Dict, List, Optional
from abc import ABC, abstractmethod


class FullLayerDetector(ABC):
    """满层判断器抽象基类"""
    
    @abstractmethod
    def detect(self, layers: List[Dict], template_layers: List[int], 
               pile_roi: Dict[str, float], depth_image: Optional[np.ndarray] = None) -> Dict:
        """
        判断是否满层
        
        :param layers: 分层结果列表
        :param template_layers: 模板层配置（每层期望的箱数）
        :param pile_roi: 堆垛ROI区域
        :param depth_image: 深度图（可选，numpy数组）
        :return: 判断结果字典，包含 full(bool), reason(str), metrics(dict) 等
        """
        pass


class CoverageBasedDetector(FullLayerDetector):
    """
    基于覆盖率的满层判断器（当前默认实现）
    
    判断逻辑：
    1. 检测数 = 模板数 → 满层
    2. 覆盖率 > 0.9 且 间距变异系数 < 0.4 → 满层
    3. 否则 → 非满层
    """
    
    def __init__(self, 
                 coverage_threshold: float = 0.9,
                 cv_gap_threshold: float = 0.4,
                 enable_debug: bool = True,
                 height_filter_ratio: float = 0.5):
        """
        :param coverage_threshold: 覆盖率阈值
        :param cv_gap_threshold: 间距变异系数阈值
        :param enable_debug: 是否启用调试输出
        :param height_filter_ratio: 高度过滤比例，小于最大高度*该比例的箱子将被过滤（默认0.5）
        """
        self.coverage_threshold = coverage_threshold
        self.cv_gap_threshold = cv_gap_threshold
        self.enable_debug = enable_debug
        self.height_filter_ratio = height_filter_ratio
    
    def _get_box_height(self, box: Dict) -> float:
        """
        获取箱子的高度
        
        :param box: 箱子数据字典，支持两种格式：
                    {"roi": {"y1": ..., "y2": ...}} 或 {"y1": ..., "y2": ...}
        :return: 箱子高度
        """
        if "roi" in box:
            return abs(box["roi"]["y2"] - box["roi"]["y1"])
        else:
            return abs(box["y2"] - box["y1"])
    
    def _filter_boxes_by_height(self, boxes: List[Dict]) -> List[Dict]:
        """
        根据高度过滤箱子：删除高度小于最大高度*height_filter_ratio的箱子
        
        :param boxes: 箱子列表
        :return: 过滤后的箱子列表
        """
        if not boxes:
            return boxes
        
        # 计算每个箱子的高度
        box_heights = [self._get_box_height(box) for box in boxes]
        
        # 找到最大高度
        max_height = max(box_heights)
        height_threshold = max_height * self.height_filter_ratio
        
        # 过滤：保留高度 >= 阈值的箱子
        filtered_boxes = [
            box for box, height in zip(boxes, box_heights)
            if height >= height_threshold
        ]
        
        # 调试信息
        if self.enable_debug and len(filtered_boxes) != len(boxes):
            print(f"🔍 顶层箱子过滤: {len(boxes)} -> {len(filtered_boxes)} "
                  f"(最大高度: {max_height:.2f}, 阈值: {height_threshold:.2f})")
        
        return filtered_boxes
    
    def _calc_coverage(self, boxes: List[Dict], pile_roi: Dict[str, float]) -> float:
        """计算横向覆盖率"""
        if not boxes:
            return 0.0
        pile_w = pile_roi["x2"] - pile_roi["x1"]
        intervals = sorted([(b["roi"]["x1"], b["roi"]["x2"]) for b in boxes], key=lambda x: x[0])
        merged = []
        for s, e in intervals:
            if not merged or s > merged[-1][1]:
                merged.append([s, e])
            else:
                merged[-1][1] = max(merged[-1][1], e)
        cover_w = sum(e - s for s, e in merged)
        return min(1.0, cover_w / pile_w)
    
    def _calc_cv_gap(self, boxes: List[Dict]) -> float:
        """计算box间距变异系数"""
        if len(boxes) < 3:
            return 0.0
        centers = sorted([(b["roi"]["x1"] + b["roi"]["x2"]) / 2 for b in boxes])
        gaps = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
        if not gaps or np.mean(gaps) == 0:
            return 0.0
        return float(np.std(gaps) / np.mean(gaps))
    
    def _calc_cv_width(self, boxes: List[Dict]) -> float:
        """计算box宽度变异系数（仅日志用）"""
        if len(boxes) < 2:
            return 0.0
        widths = [b["roi"]["x2"] - b["roi"]["x1"] for b in boxes]
        if np.mean(widths) == 0:
            return 0.0
        return float(np.std(widths) / np.mean(widths))
    
    def detect(self, layers: List[Dict], template_layers: List[int], 
               pile_roi: Dict[str, float], depth_image: Optional[np.ndarray] = None) -> Dict:
        """
        判断是否满层
        
        :param depth_image: 深度图（可选，numpy数组）
        :return: {
            "status": str,  # 状态：'full'（满层）、'partial'（非满层）、'single_layer'（单层）
            "full": bool,  # 是否满层（向后兼容）
            "reason": str,  # 判断依据
            "top_layer": {
                "index": int,
                "expected": int,  # 期望箱数
                "observed": int,  # 实际检测数
                "coverage": float,
                "cv_gap": float,
                "cv_width": float
            },
            "metrics": {  # 所有计算指标（用于调试）
                "coverage": float,
                "cv_gap": float,
                "cv_width": float,
                "coverage_threshold": float,
                "cv_gap_threshold": float
            }
        }
        """
        if not layers:
            return {
                "status": "partial",
                "full": False,
                "reason": "empty_layers",
                "top_layer": None,
                "metrics": {}
            }
        
        # 层顺序确认：y小在上
        layers = sorted(layers, key=lambda l: l["avg_y"])
        n_layers = len(layers)
        
        # 判断是否为单层
        if n_layers == 1:
            top_layer = layers[0]  # 最上层
            top_layer_boxes = top_layer.get("boxes", [])
            top_layer_boxes = self._filter_boxes_by_height(top_layer_boxes)
            top_layer["boxes"] = top_layer_boxes
            
            return {
                "status": "single_layer",
                "full": False,  # 单层不算满层
                "reason": "single_layer_detected",
                "top_layer": {
                    "index": 1,
                    "expected": template_layers[0] if template_layers else 0,
                    "observed": len(top_layer_boxes)
                },
                "metrics": {}
            }
        
        top_layer = layers[0]  # 最上层
        
        # 过滤顶层箱子：删除高度小于最大高度*height_filter_ratio的箱子
        top_layer_boxes = top_layer.get("boxes", [])
        top_layer_boxes = self._filter_boxes_by_height(top_layer_boxes)
        top_layer["boxes"] = top_layer_boxes  # 更新top_layer中的boxes，确保后续处理使用过滤后的结果
        
        C_top = template_layers[0] if template_layers else 0
        O_top = len(top_layer_boxes)  # 使用过滤后的箱子数量
        
        # 如果提供了深度图，可以在这里使用深度信息进行辅助判断
        if depth_image is not None:
            if self.enable_debug:
                print(f"📊 满层判断接收到深度图，尺寸: {depth_image.shape}")
            # TODO: 后续可以在这里使用深度图进行更精确的满层判断
        
        # 计算关键指标（使用过滤后的箱子）
        coverage = self._calc_coverage(top_layer_boxes, pile_roi)
        cv_gap = self._calc_cv_gap(top_layer_boxes)
        cv_width = self._calc_cv_width(top_layer_boxes)
        
        # 满层判断逻辑
        if O_top == C_top:
            full = True
            status = "full"
            reason = "match_template"
        elif coverage > self.coverage_threshold and cv_gap < self.cv_gap_threshold:
            full = True
            status = "full"
            reason = "continuous_filled"
        else:
            full = False
            status = "partial"
            reason = "low_coverage_or_gap"
        
        result = {
            "status": status,
            "full": full,  # 向后兼容
            "reason": reason,
            "top_layer": {
                "index": 1,
                "expected": C_top,
                "observed": O_top
            }
        }
        
        # 调试输出（简化）
        if self.enable_debug:
            status_emoji = {"full": "✅ 满层", "partial": "❌ 非满层", "single_layer": "🔵 单层"}
            status_text = status_emoji.get(status, "❓ 未知")
            print(f"🔍 满层判断: {status_text} (顶层: {O_top}/{C_top}, 依据: {reason})")
        
        return result


# 默认检测器实例（向后兼容）
_default_detector = CoverageBasedDetector()


def detect_full_layer(layers: List[Dict], template_layers: List[int], 
                     pile_roi: Dict[str, float],
                     detector: Optional[FullLayerDetector] = None,
                     depth_image: Optional[np.ndarray] = None) -> Dict:
    """
    判断是否满层（便捷函数）
    
    :param layers: 分层结果列表
    :param template_layers: 模板层配置
    :param pile_roi: 堆垛ROI区域
    :param detector: 自定义检测器（可选，默认使用 CoverageBasedDetector）
    :param depth_image: 深度图（可选，numpy数组）
    :return: 判断结果字典
    """
    if detector is None:
        detector = _default_detector
    return detector.detect(layers, template_layers, pile_roi, depth_image)

