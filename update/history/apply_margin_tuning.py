#!/usr/bin/env python3
"""余量调优：让相邻实测簇到判定边界的双侧余量 ≥0.015（2026-10-31 第二轮）。

依据 refine_margin_audit.py 的贴边清单，新边界都取在实测簇间空隙的可行窗口内：
- pile1 3/4箱分界 0.2648→0.278（窗口[0.2756,0.2812]）
- pile1 s档上界 0.1781→0.19（实测最大0.1708，上邻0.1967属另一档带不共享边界）
- pile2 深度4/3分界 0.3088→0.3185（窗口[0.3153,0.3216]）
- pile3 1/2箱分界 0.3559→0.3666（窗口[0.3582,0.3749]，single_l_2 下限同步保持无缝）
- pile4 2/4箱分界 0.294→0.317（窗口[0.3038,0.3302]，dl_4/dl_3 的 l2 档下限）
- pile5 longshort_2 槽下界 0.24→0.235（实测0.2527）
"""
import json
from pathlib import Path

CFG = Path("/home/zihui-lang/code/LeafDepot/core/config")


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def tune_3x10():
    p = CFG / "pile_ID_1_3x10.json"
    cfg = json.loads(p.read_text())
    n_s = 0
    for pat in cfg:
        for wr in pat["match"]["width_ranges"]:
            if wr == [0.126, 0.1781]:
                wr[1] = 0.19
                n_s += 1
    by_id = {x["pattern_id"]: x for x in cfg}

    wr = by_id["doubles_long_3"]["match"]["width_ranges"]
    assert wr[2] == [0.23, 0.2648]
    wr[2] = [0.23, 0.278]
    wr = by_id["doubles_long_3_mir"]["match"]["width_ranges"]
    assert wr[0] == [0.23, 0.2648]
    wr[0] = [0.23, 0.278]

    for pid, slot in (("doubles_long_4", 0), ("doubles_long_4_mir", 2)):
        wr = by_id[pid]["match"]["width_ranges"]
        assert wr[slot] == [0.2648, 0.319], (pid, wr[slot])
        wr[slot] = [0.278, 0.319]

    save(p, cfg)
    print(f"pile_ID_1_3x10.json: s档上界×{n_s} →0.19, 3/4箱分界 →0.278")


def tune_5x8():
    p = CFG / "pile_ID_2_5x8.json"
    cfg = json.loads(p.read_text())
    n = 0
    for pat in cfg:
        for wr in pat["match"]["width_ranges"]:
            for i, v in enumerate(wr):
                if v == 0.3088:
                    wr[i] = 0.3185
                    n += 1
    save(p, cfg)
    print(f"pile_ID_2_5x8.json: 0.3088→0.3185 ×{n}处")


def tune_5x6():
    p = CFG / "pile_ID_3_5x6.json"
    cfg = json.loads(p.read_text())
    by_id = {x["pattern_id"]: x for x in cfg}
    wr = by_id["single_l_1"]["match"]["width_ranges"]
    assert wr[0] == [0.2715, 0.3559]
    wr[0] = [0.2715, 0.3666]
    wr = by_id["single_l_2"]["match"]["width_ranges"]
    assert wr[0] == [0.3559, 0.4064]
    wr[0] = [0.3666, 0.4064]
    save(p, cfg)
    print("pile_ID_3_5x6.json: 1/2箱分界 0.3559→0.3666（single_l_1/2 同步）")


def tune_4x7():
    p = CFG / "pile_ID_4_4x7+2.json"
    cfg = json.loads(p.read_text())
    by_id = {x["pattern_id"]: x for x in cfg}
    wr = by_id["double_l_4"]["match"]["width_ranges"]
    assert wr == [[0.294, 0.399], [0.294, 0.399]]
    wr[0] = [0.317, 0.399]
    wr[1] = [0.317, 0.399]
    wr = by_id["double_l_3"]["match"]["width_ranges"]
    assert wr[0] == [0.294, 0.399]
    wr[0] = [0.317, 0.399]
    wr = by_id["double_l_3_mir"]["match"]["width_ranges"]
    assert wr[1] == [0.294, 0.399]
    wr[1] = [0.317, 0.399]
    save(p, cfg)
    print("pile_ID_4_4x7+2.json: dl_4/dl_3 的 l2 档下限 0.294→0.317")


def tune_5x5():
    p = CFG / "pile_ID_5_5x5.json"
    cfg = json.loads(p.read_text())
    by_id = {x["pattern_id"]: x for x in cfg}
    wr = by_id["longshort_2"]["match"]["width_ranges"]
    assert wr[0] == [0.24, 0.399]
    wr[0] = [0.235, 0.399]
    wr = by_id["longshort_2_mir"]["match"]["width_ranges"]
    assert wr[1] == [0.24, 0.399]
    wr[1] = [0.235, 0.399]
    save(p, cfg)
    print("pile_ID_5_5x5.json: longshort_2 槽下界 0.24→0.235")


if __name__ == "__main__":
    tune_3x10()
    tune_5x8()
    tune_5x6()
    tune_4x7()
    tune_5x5()
