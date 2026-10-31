#!/usr/bin/env python3
"""余量调优第三轮（收尾）：修复顺序感知审计中剩余 3 处 <0.015 的余量。

1. 5x5 longshort_3d 槽0 / 3d_mir 槽1 下限 0.2625→0.268
   （5.5_2 [0.2527,0.3431] 翻转到 count3 的余量 0.0098→0.0153）
2. 5x5 longshort_3t_mir 槽1 下限 0.357→0.359（次近威胁 0.0139→0.0159）
3. 3x10 triple_s_5 槽0 / triple_s_5_mir 槽2 上限 0.2835→0.281
   （3.10_4 槽2=0.2962 翻转到 count5 的余量 0.0127→0.0152）
4. 3x10 doubles_long_9t / 9t_mir 槽1 上限 0.2835→0.285
   （3.10_9(2) 槽1=0.2693 自身余量 0.0142→0.0157）
"""
import json
from pathlib import Path

CFG = Path("/home/zihui-lang/code/LeafDepot/core/config")


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def tune_5x5():
    p = CFG / "pile_ID_5_5x5.json"
    cfg = json.loads(p.read_text())
    by_id = {x["pattern_id"]: x for x in cfg}
    wr = by_id["longshort_3d"]["match"]["width_ranges"]
    assert wr[0] == [0.2625, 0.357]
    wr[0] = [0.268, 0.357]
    wr = by_id["longshort_3d_mir"]["match"]["width_ranges"]
    assert wr[1] == [0.2625, 0.357]
    wr[1] = [0.268, 0.357]
    wr = by_id["longshort_3t_mir"]["match"]["width_ranges"]
    assert wr[1] == [0.357, 0.4725]
    wr[1] = [0.359, 0.4725]
    save(p, cfg)
    print("pile_ID_5_5x5.json: 3d 槽下限→0.268, 3t_mir 槽1 下限→0.359")


def tune_3x10():
    p = CFG / "pile_ID_1_3x10.json"
    cfg = json.loads(p.read_text())
    by_id = {x["pattern_id"]: x for x in cfg}
    wr = by_id["triple_s_5"]["match"]["width_ranges"]
    assert wr[0] == [0.23, 0.2835]
    wr[0] = [0.23, 0.281]
    wr = by_id["triple_s_5_mir"]["match"]["width_ranges"]
    assert wr[2] == [0.23, 0.2835]
    wr[2] = [0.23, 0.281]
    for pid in ("doubles_long_9t", "doubles_long_9t_mir"):
        wr = by_id[pid]["match"]["width_ranges"]
        assert wr[1] == [0.23, 0.2835], (pid, wr[1])
        wr[1] = [0.23, 0.285]
    save(p, cfg)
    print("pile_ID_1_3x10.json: triple_s_5(_mir) 上限→0.281, 9t(_mir) 槽1 上限→0.285")


if __name__ == "__main__":
    tune_5x5()
    tune_3x10()
