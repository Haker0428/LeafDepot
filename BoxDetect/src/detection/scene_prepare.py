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

