"""满层判断：根据覆盖率、间距变异系数等指标判断顶层是否满层"""

import numpy as np
from typing import Dict, List


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
    改进版满层判定算法 v3:
    1️⃣ 只看最高层是否连续填满横向空间；
    2️⃣ 宽度差异不影响判定。
    """
    if not layers:
        return {"full": False, "total": 0, "reason": "empty layers"}

    # 层顺序确认：y小在上
    layers = sorted(layers, key=lambda l: l["avg_y"])
    top_layer = layers[0]  # ✅ 最上层
    C_top = template_layers[0] if template_layers else 0
    O_top = len(top_layer["boxes"])

    coverage = calc_coverage(top_layer["boxes"], pile_roi)
    cv_gap = calc_cv_gap(top_layer["boxes"])
    cv_width = calc_cv_width(top_layer["boxes"])

    # 满层判断逻辑
    if O_top == C_top:
        full = True
        reason = "match_template"
    elif coverage > 0.9 and cv_gap < 0.4:
        full = True
        reason = "continuous_filled"
    else:
        full = False
        reason = "low_coverage_or_gap"

    total = sum(template_layers) if full else sum(template_layers[:-1]) + O_top

    result = {
        "full": full,
        "top_layer": {
            "index": 1,
            "expected": C_top,
            "observed": O_top,
            "coverage": round(coverage, 3),
            "cv_gap": round(cv_gap, 3),
            "cv_width": round(cv_width, 3),
            "reason": reason
        },
        "total": int(total)
    }

    # 打印调试日志
    print("\n🧮 顶层判定结果：", "✅ 满层" if full else "❌ 不满层")
    print(f" - 检测数: {O_top}, 模板: {C_top}")
    print(f" - coverage: {coverage:.3f}, cv_gap: {cv_gap:.3f}, cv_width: {cv_width:.3f}")
    print(f" - 判定依据: {reason}")
    print(f"整堆总箱数: {total}\n")

    # 宽度差异告警提示
    if cv_width > 0.4:
        print("⚠️ 宽度差异较大，可能横竖混放或检测框偏移。")

    return result

