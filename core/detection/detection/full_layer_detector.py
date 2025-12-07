"""满层判断模块：可独立调试的满层判定逻辑"""

import numpy as np
from typing import Dict, List, Optional
from abc import ABC, abstractmethod


class FullLayerDetector(ABC):
    """满层判断器抽象基类"""
    
    @abstractmethod
    def detect(self, layers: List[Dict], template_layers: List[int], 
               pile_roi: Dict[str, float]) -> Dict:
        """
        判断是否满层
        
        :param layers: 分层结果列表
        :param template_layers: 模板层配置（每层期望的箱数）
        :param pile_roi: 堆垛ROI区域
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
                 enable_debug: bool = True):
        """
        :param coverage_threshold: 覆盖率阈值
        :param cv_gap_threshold: 间距变异系数阈值
        :param enable_debug: 是否启用调试输出
        """
        self.coverage_threshold = coverage_threshold
        self.cv_gap_threshold = cv_gap_threshold
        self.enable_debug = enable_debug
    
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
               pile_roi: Dict[str, float]) -> Dict:
        """
        判断是否满层
        
        :return: {
            "full": bool,  # 是否满层
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
                "full": False,
                "reason": "empty_layers",
                "top_layer": None,
                "metrics": {}
            }
        
        # 层顺序确认：y小在上
        layers = sorted(layers, key=lambda l: l["avg_y"])
        top_layer = layers[0]  # 最上层
        
        C_top = template_layers[0] if template_layers else 0
        O_top = len(top_layer["boxes"])
        
        # 计算关键指标
        coverage = self._calc_coverage(top_layer["boxes"], pile_roi)
        cv_gap = self._calc_cv_gap(top_layer["boxes"])
        cv_width = self._calc_cv_width(top_layer["boxes"])
        
        # 满层判断逻辑
        if O_top == C_top:
            full = True
            reason = "match_template"
        elif coverage > self.coverage_threshold and cv_gap < self.cv_gap_threshold:
            full = True
            reason = "continuous_filled"
        else:
            full = False
            reason = "low_coverage_or_gap"
        
        result = {
            "full": full,
            "reason": reason,
            "top_layer": {
                "index": 1,
                "expected": C_top,
                "observed": O_top,
                "coverage": round(coverage, 3),
                "cv_gap": round(cv_gap, 3),
                "cv_width": round(cv_width, 3)
            },
            "metrics": {
                "coverage": round(coverage, 3),
                "cv_gap": round(cv_gap, 3),
                "cv_width": round(cv_width, 3),
                "coverage_threshold": self.coverage_threshold,
                "cv_gap_threshold": self.cv_gap_threshold
            }
        }
        
        # 调试输出
        if self.enable_debug:
            print("\n" + "="*50)
            print("🔍 满层判断模块 - 调试信息")
            print("="*50)
            print(f"📊 顶层检测数: {O_top}, 模板期望: {C_top}")
            print(f"📈 覆盖率: {coverage:.3f} (阈值: {self.coverage_threshold})")
            print(f"📉 间距变异系数: {cv_gap:.3f} (阈值: {self.cv_gap_threshold})")
            print(f"📏 宽度变异系数: {cv_width:.3f}")
            print(f"✅ 判断结果: {'满层' if full else '非满层'}")
            print(f"📝 判断依据: {reason}")
            print("="*50 + "\n")
            
            if cv_width > 0.4:
                print("⚠️  宽度差异较大，可能横竖混放或检测框偏移。\n")
        
        return result


# 默认检测器实例（向后兼容）
_default_detector = CoverageBasedDetector()


def detect_full_layer(layers: List[Dict], template_layers: List[int], 
                     pile_roi: Dict[str, float],
                     detector: Optional[FullLayerDetector] = None) -> Dict:
    """
    判断是否满层（便捷函数）
    
    :param layers: 分层结果列表
    :param template_layers: 模板层配置
    :param pile_roi: 堆垛ROI区域
    :param detector: 自定义检测器（可选，默认使用 CoverageBasedDetector）
    :return: 判断结果字典
    """
    if detector is None:
        detector = _default_detector
    return detector.detect(layers, template_layers, pile_roi)

