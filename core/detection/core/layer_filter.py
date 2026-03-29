"""层过滤：去除误层、过滤背面box"""

import numpy as np
from typing import List, Dict


def filter_rear_boxes_if_multilayer(layers: List[Dict], pile_roi: Dict[str, float]) -> List[Dict]:
    """
    若层数>1，自动去除每层中的后排（y值较小的箱）
    若层数=1，不做任何过滤
    
    Args:
        layers: 分层结果列表
        pile_roi: 堆垛ROI区域
        
    Returns:
        过滤后的分层结果列表
    """
    if len(layers) <= 1:
        return layers  # 单层直接返回
    
    filtered_layers = []
    for layer in layers:
        boxes = layer["boxes"]
        if len(boxes) <= 3:
            filtered_layers.append(layer)
            continue

        # 计算y中心
        y_mids = np.array([(b["roi"]["y1"] + b["roi"]["y2"]) / 2 for b in boxes])
        y_mean = np.mean(y_mids)
        y_std = np.std(y_mids)

        # 前排箱：中心y大于均值
        front_boxes = [b for i, b in enumerate(boxes) if y_mids[i] >= y_mean]

        layer_copy = dict(layer)
        layer_copy["boxes"] = front_boxes
        layer_copy["rear_removed"] = len(boxes) - len(front_boxes)
        filtered_layers.append(layer_copy)
    
    return filtered_layers


def remove_fake_top_layer(layers: List[Dict], width_ratio_thr: float = 0.7) -> List[Dict]:
    """
    通过ROI宽度变化判断伪层：
    若最高层宽度明显小于下一层，则删除。
    
    Args:
        layers: 分层结果列表（已按avg_y排序）
        width_ratio_thr: 宽度比例阈值
        
    Returns:
        去除伪层后的分层结果列表
    """
    if len(layers) < 2:
        return layers
    
    # layers = sorted(layers, key=lambda l: l["avg_y"])
    top, next_layer = layers[0], layers[1]

    w_top = top["roi"].get("y2", None)
    w_next = next_layer["roi"].get("y2", None)

    # 如果roi存的是x1/x2，直接计算宽度；如果不是，需要从boxes计算
    if w_top is None:
        def layer_width(l):
            xs = []
            for b in l["boxes"]:
                xs.extend([b["roi"]["y1"], b["roi"]["y2"]])
            return max(xs) - min(xs)
        width_top = layer_width(top)
        width_next = layer_width(next_layer)
    else:
        width_top = top["roi"]["y2"] - top["roi"]["y1"]
        width_next = next_layer["roi"]["y2"] - next_layer["roi"]["y1"]

    ratio = width_top / max(width_next, 1e-6)
    print(f"[高度比检测] top={width_top:.1f}, next={width_next:.1f}, ratio={ratio:.2f}")

    if ratio < width_ratio_thr:
        print("⚠️ 顶层宽度显著偏小，删除伪层。")
        return layers[1:]
    return layers
