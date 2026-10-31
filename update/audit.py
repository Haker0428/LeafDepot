#!/usr/bin/env python3
"""余量审计：每张照片的自身余量 + 顺序感知翻转余量。

用法（仓库根目录）：
    python3 update/audit.py [阈值]      # 默认 0.015

两项口径：
- 自身余量：实测宽度到命中区间边界的最小距离（太小 → 容易掉出区间失配）
- 翻转余量：把整张照片漂移成"错误箱数"所需的最小单槽漂移。
  只统计配置文件里排在命中 pattern 之前、箱数不同的 pattern
  （匹配是顺序首个命中即返回，排后面的永远轮不到抢）。
  值为 ∞ 表示前面没有可竞争的异箱数 pattern。

目标：两项均 ≥ 阈值。低于阈值的照片按最紧的排序列出。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DATA_DIR, discover_piles, load_configs, load_top_row,
                    match, count_of, parse_stem)

INF = float("inf")


def audit_photo(norm_ws, patterns):
    """返回 (命中pattern, 自身余量, 翻转余量, 最近威胁pattern_id)。"""
    pat, _, ok = match(norm_ws, patterns)
    if not ok:
        return None, None, None, None
    wr = pat["match"]["width_ranges"]
    own = min(min(w - lo, hi - w) for w, (lo, hi) in zip(norm_ws, wr))

    mi = patterns.index(pat)
    cm = count_of(pat["pattern_id"])
    flip, threat = INF, None
    for p in patterns[:mi]:
        pr = p["match"]["width_ranges"]
        if len(pr) != len(norm_ws):
            continue
        c = count_of(p["pattern_id"])
        if c is None or c == cm:
            continue
        # 每槽独立漂移；pattern 抢走需所有槽同时进带 → 最近距离 = 各槽需求的最大值
        need = [0.0 if lo <= w <= hi else (lo - w if w < lo else w - hi)
                for w, (lo, hi) in zip(norm_ws, pr)]
        m = max(need)
        if m < flip:
            flip, threat = m, p["pattern_id"]
    return pat, own, flip, threat


def main(threshold=0.015):
    piles = discover_piles()
    cfgs = load_configs()

    rows = []
    for txt in sorted(DATA_DIR.glob("*.txt")):
        stem = txt.stem
        pile_name, truth = parse_stem(stem)
        pid = piles[pile_name]
        norm_ws, _ = load_top_row(txt)
        pat, own, flip, threat = audit_photo(norm_ws, cfgs[pid])
        if pat is None:
            print(f"!! {stem} 未命中任何 pattern，先跑 validate.py 处理")
            continue
        rows.append((min(own, flip), own, flip, threat, stem, pid, truth))

    rows.sort()
    print(f"== 余量低于 {threshold} 的照片（自身/翻转取小者排序） ==")
    n_bad = 0
    for m, own, flip, threat, stem, pid, truth in rows:
        if m < threshold:
            n_bad += 1
            flip_s = "∞" if flip == INF else f"{flip:.4f}({threat})"
            print(f"  pile{pid} {stem:16s} 真实={truth:2d} 自身={own:.4f} 翻转={flip_s}")
    if n_bad == 0:
        print("  (无)")

    owns = [r[1] for r in rows]
    flips = [r[2] for r in rows]
    print(f"\n全部{len(rows)}张: 自身余量 min={min(owns):.4f} 中位={sorted(owns)[len(owns)//2]:.4f}, "
          f"翻转余量 min={min(flips):.4f}")
    print(f"结论: {'✓ 全部达标' if n_bad == 0 else f'✗ {n_bad} 张低于阈值'}")
    return 0 if n_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main(float(sys.argv[1]) if len(sys.argv) > 1 else 0.015))
