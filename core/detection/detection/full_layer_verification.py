"""满层判断：根据覆盖率、间距变异系数等指标判断顶层是否满层

注意：此模块保持向后兼容，内部使用新的可扩展架构
"""

import numpy as np
from typing import Dict, List
from core.detection.detection.stack_processor_factory import StackProcessorFactory


def calc_coverage(boxes, pile_roi):
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


def calc_cv_gap(boxes):
    """计算box间距变异系数"""
    if len(boxes) < 3:
        return 0.0
    centers = sorted([(b["roi"]["x1"] + b["roi"]["x2"]) / 2 for b in boxes])
    gaps = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
    return float(np.std(gaps) / np.mean(gaps))


def calc_cv_width(boxes):
    """计算box宽度变异系数（仅日志用）"""
    if len(boxes) < 2:
        return 0.0
    widths = [b["roi"]["x2"] - b["roi"]["x1"] for b in boxes]
    return float(np.std(widths) / np.mean(widths))


def verify_full_stack(layers, template_layers, pile_roi):
    """
    改进版满层判定算法 v3（向后兼容接口）:
    1️⃣ 只看最高层是否连续填满横向空间；
    2️⃣ 宽度差异不影响判定。
    
    注意：此函数内部使用新的可扩展架构，但保持原有接口和返回格式
    """
    # 使用新的工厂模式处理（保持向后兼容）
    factory = StackProcessorFactory(enable_debug=True)
    result = factory.process(layers, template_layers, pile_roi)
    
    # 转换为原有返回格式（向后兼容）
    return {
        "full": result["full"],
        "total": result["total"],
        "reason": result["reason"],
        "top_layer": result["top_layer"]
    }

