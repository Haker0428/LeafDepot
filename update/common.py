#!/usr/bin/env python3
"""update 工具包公共库：数据加载 + 生产同款匹配逻辑。

数据约定（与 core/detection/processors/stack_processor.py 的匹配口径一致）：
- 照片名 {垛型}_{顶层剩余箱数}.jpg，垛型 = 配置文件名中的 x 换成 .（3x10→3.10）
- 同名 .txt 为 YOLO 格式 class cx cy w h，归一化到整幅图像
- class 1 大框 = 垛 ROI（norm_width 的分母），其余 class = 烟箱
- 顶层箱 = 画面最上方一行（按 cy 聚类），脚本自动提取并按中心 x 从左到右排序
- norm_width = 箱像素宽 / 垛ROI像素宽，逐槽与 pattern 的 width_ranges[j] 比对
- 匹配按配置文件顺序，首个全部槽命中即返回（排在后面的 pattern 不构成威胁）
"""
import json
import re
import sys
from pathlib import Path

UPDATE_DIR = Path(__file__).resolve().parent
DATA_DIR = UPDATE_DIR / "data"
CONFIG_DIR = UPDATE_DIR.parent / "core" / "config"

if str(UPDATE_DIR) not in sys.path:
    sys.path.insert(0, str(UPDATE_DIR))


def discover_piles():
    """从 core/config/pile_ID_{id}_{name}.json 推导 照片垛型前缀 -> 垛型ID。

    自动适配新增垛型：3x10 -> "3.10"，4x7+2 -> "4.7+2"。
    """
    mapping = {}
    for f in sorted(CONFIG_DIR.glob("pile_ID_*_*.json")):
        m = re.match(r"pile_ID_(\d+)_(.+)\.json$", f.name)
        if m:
            mapping[m.group(2).replace("x", ".")] = int(m.group(1))
    return mapping


def load_configs():
    """加载全部垛型 pattern 配置：{垛型ID: pattern列表}。"""
    by_cfg = {}
    for f in sorted(CONFIG_DIR.glob("pile_ID_*_*.json")):
        m = re.match(r"pile_ID_(\d+)", f.name)
        if m:
            by_cfg[int(m.group(1))] = json.loads(f.read_text())
    return by_cfg


def parse_stem(stem):
    """照片名 -> (垛型前缀, 顶层真实剩余箱数)。'3.10_5 (2)' -> ('3.10', 5)。"""
    pile, seq = stem.rsplit("_", 1)
    n = int("".join(filter(str.isdigit, seq.split("(")[0])))
    return pile, n


def load_top_row(txt_path):
    """解析 YOLO txt -> (顶层各箱 norm_width 左->右, ROI宽)。"""
    boxes = []
    for line in Path(txt_path).read_text().splitlines():
        if not line.strip():
            continue
        c, cx, cy, w, h = line.split()
        boxes.append(dict(cls=int(c), cx=float(cx), cy=float(cy),
                          w=float(w), h=float(h)))
    rois = [b for b in boxes if b["cls"] == 1]
    rest = [b for b in boxes if b["cls"] != 1]
    if not rois:
        # 个别文件类别号噪声(如15/16)：退化为取面积最大框当 ROI
        rois = [max(boxes, key=lambda b: b["w"] * b["h"])]
        rest = [b for b in boxes if b is not rois[0]]
    roi_w = rois[0]["w"]
    rows = []  # 按 cy 聚行(gap=0.06)，最上一行 = 顶层
    for b in sorted(rest, key=lambda b: b["cy"]):
        if rows and b["cy"] - rows[-1][-1]["cy"] <= 0.06:
            rows[-1].append(b)
        else:
            rows.append([b])
    top = sorted(rows[0], key=lambda b: b["cx"])
    return [b["w"] / roi_w for b in top], roi_w


def match(norm_ws, patterns):
    """生产逻辑匹配：返回 (命中pattern, 每槽明细, 是否命中)。

    未命中时 pattern = 与观测偏差总和最小的候选（用于定位问题），ok=False。
    """
    best = None  # ((偏差和, pattern_id), pattern, 明细)
    for p in patterns:
        wr = p["match"]["width_ranges"]
        if len(wr) != len(norm_ws):
            continue
        viol, detail, ok = 0, [], True
        for j, w in enumerate(norm_ws):
            lo, hi = wr[j]
            if lo <= w <= hi:
                detail.append(f"{w:.4f}∈[{lo},{hi}]")
            else:
                d = lo - w if w < lo else w - hi
                viol += d
                ok = False
                detail.append(f"{w:.4f}∉[{lo},{hi}](差{d:.4f})")
        if ok:
            return p, detail, True
        key = (viol, p["pattern_id"])
        if best is None or key < best[0]:
            best = (key, p, detail)
    return (best[1], best[2], False) if best else (None, [], False)


def count_of(pattern_id):
    """pattern_id 末尾数字 = 该 pattern 代表的顶层箱数（生产代码同款取法）。"""
    n = re.findall(r"\d+", pattern_id)
    return int(n[-1]) if n else None
