"""场景准备逻辑：过滤YOLO输出，确定ROI"""

from typing import Dict, List, Optional


def prepare_logic(yolo_output: List[Dict], conf_thr: float = 0.6) -> Optional[Dict]:
    """
    过滤 YOLO 输出，只保留 pile 内目标（不做绘图）
    """
    # 1️⃣ 找到唯一 pile
    piles = [b for b in yolo_output if b["cls"] == "pile" and b["conf"] >= conf_thr]
    if not piles:
        print("⚠️ 未检测到 pile")
        return None
    pile = max(piles, key=lambda b: b["conf"])
    pile_roi = {
        "x1": int(pile["x1"]),
        "y1": int(pile["y1"]),
        "x2": int(pile["x2"]),
        "y2": int(pile["y2"])
    }

    # 2️⃣ pile 内过滤
    boxes, barcodes = [], []
    for b in yolo_output:
        if b["conf"] < conf_thr:
            continue
        xc = 0.5 * (b["x1"] + b["x2"])
        yc = 0.5 * (b["y1"] + b["y2"])
        if not (pile_roi["x1"] <= xc <= pile_roi["x2"] and pile_roi["y1"] <= yc <= pile_roi["y2"]):
            continue
        if b["cls"] == "box":
            boxes.append(b)
        elif b["cls"] == "barcode":
            barcodes.append(b)

    return {
        "pile_roi": pile_roi,
        "boxes": boxes,
        "barcodes": barcodes,
        "count": {
            "boxes": len(boxes),
            "barcodes": len(barcodes)
        }
    }

import numpy as np

def filter_rear_boxes_if_multilayer(layers, pile_roi):
    """
    若层数>1，自动去除每层中的后排（y值较小的箱）
    若层数=1，不做任何过滤
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

def remove_fake_top_layer(layers, width_ratio_thr=0.7):
    """
    通过ROI宽度变化判断伪层：
    若最高层宽度明显小于下一层，则删除。
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
