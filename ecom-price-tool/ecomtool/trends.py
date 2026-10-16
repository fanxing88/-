"""价格趋势与历史快照存储。

价格趋势来源于两部分：
1. 历史累积：每次运行都会把当次价格写入 data/history.json，跨多次运行
   即可形成真实的"价格随时间变化"曲线。
2. 首次回填：某商品还没有历史记录时，用其商品 ID 做种子生成一条确定性的
   模拟 7 日曲线（标注 is_simulated=True），保证单次运行也能展示趋势图。
"""
from __future__ import annotations

import json
import random
import threading
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

from .config import TREND_DAYS
from .models import Product

_lock = threading.Lock()

# 历史文件放在项目根目录下（data/history.json），与运行目录解耦
_HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "history.json"


def _key(keyword: str) -> str:
    return " ".join(keyword.split()).lower()


def _seed_from_id(product_id: str) -> int:
    return int.from_bytes(product_id.encode("utf-8")[:4], "big", signed=False) or 1


def _synthetic_trend(product: Product, days: int) -> List[float]:
    """确定性模拟曲线：以当前价为终点，构造一条有起伏的历史价格。"""
    rng = random.Random(_seed_from_id(product.product_id or product.title))
    start = product.price * rng.uniform(0.88, 1.18)
    trend: List[float] = []
    for i in range(days):
        t = 0.0 if days == 1 else i / (days - 1)
        base = start + (product.price - start) * t
        noise = rng.uniform(-0.03, 0.03) * product.price
        trend.append(round(max(0.01, base + noise), 2))
    trend[-1] = round(product.price, 2)
    return trend


class HistoryStore:
    """线程安全的 JSON 历史存储。"""

    def __init__(self, path: Path = _HISTORY_PATH) -> None:
        self.path = path
        self._data: Dict[str, Dict[str, List[Dict]]] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def record(self, keyword: str, product: Product) -> Tuple[List[float], float, bool]:
        """记录一次价格快照，返回 (趋势序列, 涨跌幅%, 是否模拟)。"""
        today = date.today().isoformat()
        pid = product.product_id or product.title

        with _lock:
            bucket = self._data.setdefault(_key(keyword), {})
            history = bucket.setdefault(pid, [])
            if not history or history[-1]["date"] != today:
                history.append({"date": today, "price": round(product.price, 2)})
                self._save()

            prices = [h["price"] for h in history]

            simulated = False
            if len(prices) < TREND_DAYS:
                # 历史不足时回填模拟曲线，前缀补足到 TREND_DAYS 长度
                back = _synthetic_trend(product, TREND_DAYS)
                back[-len(prices):] = prices
                trend = back
                simulated = True
            else:
                trend = prices[-TREND_DAYS:]

        pct = 0.0
        if trend and trend[0] > 0:
            pct = (trend[-1] - trend[0]) / trend[0] * 100
        return trend, round(pct, 2), simulated
