"""堆配置数据库管理"""

import json
from pathlib import Path
from typing import Dict, List

from core.detection.utils.exceptions import PileNotFoundError


class PileTypeDatabase:
    """读取并解析堆配置文件，提供便捷查询接口。"""

    def __init__(self, json_path: str | Path):
        self.path = Path(json_path)
        if not self.path.exists():
            raise FileNotFoundError(f"未找到文件: {self.path}")
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._piles = {pile["id"]: pile for pile in data.get("piles", [])}

    def get_pile(self, pile_id: int) -> Dict:
        """返回指定堆的完整信息。"""
        pile = self._piles.get(pile_id)
        if not pile:
            raise PileNotFoundError(f"未找到 pile_id={pile_id} 的堆定义")
        return pile

    def get_layers(self, pile_id: int) -> List[Dict]:
        """获取指定堆的层信息。"""
        pile = self.get_pile(pile_id)
        return pile.get("layers", [])

    def get_total_count(self, pile_id: int) -> int:
        """计算并返回总烟箱数量。"""
        layers = self.get_layers(pile_id)
        return sum(layer.get("count", 0) for layer in layers)

    def list_piles(self) -> List[Dict]:
        """列出所有堆的基本信息。"""
        return [{"id": p["id"], "name": p["name"]} for p in self._piles.values()]
    
    def get_template_layers(self, pile_id: int) -> List[int]:
        """获取指定堆的模板层配置（每层期望的箱数列表）。"""
        layers = self.get_layers(pile_id)
        return [layer.get("count", 0) for layer in layers]

