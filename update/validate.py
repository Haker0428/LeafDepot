#!/usr/bin/env python3
"""校验 data/ 下全部照片：配置判定箱数 vs 文件名标注的真实剩余箱数。

用法（仓库根目录）：
    python3 update/validate.py [数据目录]     # 默认 update/data

输出每张照片一行：✓ 判定正确 / ✗未命中(回落YOLO) / ⚠假匹配(判错箱数)。
未命中时附最近候选 pattern 与逐槽偏差，作为修改 width_ranges 的依据。
退出码：全部正确 0，存在问题 1。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DATA_DIR, discover_piles, load_configs, load_top_row,
                    match, count_of, parse_stem)


def main(data_dir=None):
    data_dir = Path(data_dir) if data_dir else DATA_DIR
    piles = discover_piles()
    cfgs = load_configs()

    txts = sorted(data_dir.glob("*.txt"))
    if not txts:
        print(f"!! {data_dir} 下没有 .txt 文件")
        return 1
    for jpg in data_dir.glob("*.jpg"):
        if not jpg.with_suffix(".txt").exists():
            print(f"!! 照片缺少同名 txt: {jpg.name}")

    bad = 0
    per_pile = {}
    for txt in txts:
        stem = txt.stem
        try:
            pile_name, truth = parse_stem(stem)
            pid = piles[pile_name]
        except (ValueError, KeyError):
            print(f"?? 文件名无法解析/未知垛型: {stem} (已知: {piles})")
            bad += 1
            continue

        norm_ws, _ = load_top_row(txt)
        pat, detail, ok = match(norm_ws, cfgs[pid])
        judged = count_of(pat["pattern_id"]) if ok else len(norm_ws)

        if ok and judged == truth:
            mark = "✓"
        elif ok:
            mark, bad = f"⚠假匹配(判{judged})", bad + 1
        else:
            mark, bad = f"✗未命中(回落YOLO={judged})", bad + 1
        ok_count, tot = per_pile.get(pid, (0, 0))
        per_pile[pid] = (ok_count + (1 if mark == "✓" else 0), tot + 1)

        print(f"{stem:16s} 真实={truth:2d} 检出宽={[round(w, 4) for w in norm_ws]} "
              f"→ {mark} {pat['pattern_id'] if pat else '无'}")
        if not ok:
            for d in detail:
                print(f"    {d}")

    print(f"\n汇总: {'全对' if bad == 0 else f'{bad} 张有问题'}  "
          + "  ".join(f"pile{p}:{ok}/{tot}" for p, (ok, tot) in sorted(per_pile.items())))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
