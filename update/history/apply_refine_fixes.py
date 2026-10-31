#!/usr/bin/env python3
"""按 refine 照片标定结果修正 pile_ID_*.json 的 width_ranges（2026-10-31）。

对应关系表与依据见 data/refine_对应关系表.md，共 5 条：
1. 3x10 新增 doubles_long_3(+_mir)：剩3箱形态 [s,s,l@0.23-0.2648]，插在 vc=3 块最前
2. 3x10 doubles_long_9t/9t_mir 短槽下限 0.147→0.10（实测 0.122）
3. 3x10 dl_4/dl_5 的 l 槽分界 0.2994→0.319（实测4箱0.296/0.299、5箱0.340/0.348 的中点）
4. 5x6 single_l_1 上限 0.3391→0.3559（实测 0.343，与 single_l_2 无缝相接）
5. 5x5 longshort_2 槽1 / longshort_2_mir 槽2 下限 0.315→0.24（实测 0.253）
"""
import json
from pathlib import Path

CFG = Path("/home/zihui-lang/code/LeafDepot/core/config")


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def fix_3x10():
    p = CFG / "pile_ID_1_3x10.json"
    cfg = json.loads(p.read_text())

    # 1. 新增剩3箱 pattern，插在 triple_s_6（vc=3 块开头）之前，
    #    否则 triple_s_5_mir 会先命中把3箱误判成5箱
    new_patterns = [
        {
            "pattern_id": "doubles_long_3",
            "visible_count": 3,
            "match": {
                "width_ranges": [[0.126, 0.1781], [0.126, 0.1781], [0.23, 0.2648]],
                "depth_ranges": [[16950, 19450], [16950, 19450], [18750, 21950]],
            },
            "result_ids": [3, 4, 5],
        },
        {
            "pattern_id": "doubles_long_3_mir",
            "visible_count": 3,
            "match": {
                "width_ranges": [[0.23, 0.2648], [0.126, 0.1781], [0.126, 0.1781]],
                "depth_ranges": [[18750, 21950], [16950, 19450], [16950, 19450]],
            },
            "result_ids": [5, 3, 4],
        },
    ]
    names = [x["pattern_id"] for x in cfg]
    assert "doubles_long_3" not in names
    i = names.index("triple_s_6")
    cfg[i:i] = new_patterns

    by_id = {x["pattern_id"]: x for x in cfg}

    # 2. 9t 短槽下限 0.147→0.10
    for pid, slot in (("doubles_long_9t", 2), ("doubles_long_9t_mir", 0)):
        wr = by_id[pid]["match"]["width_ranges"]
        assert wr[slot] == [0.147, 0.23], (pid, wr[slot])
        wr[slot] = [0.1, 0.23]

    # 3. 4箱/5箱 l 槽分界 0.2994→0.319
    for pid, slot, which in (("doubles_long_4", 0, 1), ("doubles_long_4_mir", 2, 1),
                             ("doubles_long_5", 2, 0), ("doubles_long_5_mir", 0, 0)):
        wr = by_id[pid]["match"]["width_ranges"]
        assert wr[slot][which] == 0.2994, (pid, wr[slot])
        wr[slot][which] = 0.319

    save(p, cfg)
    print(f"pile_ID_1_3x10.json: {len(cfg)} patterns（+2 新增）")


def fix_5x6():
    p = CFG / "pile_ID_3_5x6.json"
    cfg = json.loads(p.read_text())
    by_id = {x["pattern_id"]: x for x in cfg}
    wr = by_id["single_l_1"]["match"]["width_ranges"]
    assert wr[0] == [0.2715, 0.3391], wr
    wr[0] = [0.2715, 0.3559]
    save(p, cfg)
    print("pile_ID_3_5x6.json: single_l_1 →", wr)


def fix_5x5():
    p = CFG / "pile_ID_5_5x5.json"
    cfg = json.loads(p.read_text())
    by_id = {x["pattern_id"]: x for x in cfg}
    # longshort_2 槽1 / mir 槽2 下限 0.315→0.24
    wr = by_id["longshort_2"]["match"]["width_ranges"]
    assert wr[0] == [0.315, 0.399], wr
    wr[0] = [0.24, 0.399]
    wr = by_id["longshort_2_mir"]["match"]["width_ranges"]
    assert wr[1] == [0.315, 0.399], wr
    wr[1] = [0.24, 0.399]
    save(p, cfg)
    print("pile_ID_5_5x5.json: longshort_2 槽1 →", by_id["longshort_2"]["match"]["width_ranges"])


if __name__ == "__main__":
    fix_3x10()
    fix_5x6()
    fix_5x5()
