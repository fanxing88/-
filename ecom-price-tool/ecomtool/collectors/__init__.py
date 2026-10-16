"""采集器注册表与工厂。

source 取值：
- "mock":   直接使用演示数据（默认，保证开箱即用）
- "auto":   依次尝试 jd/taobao/pdd 真实抓取，全部失败时降级到 mock
- 具体平台: 只抓取指定平台，失败时降级到 mock
"""
from __future__ import annotations

from typing import List, Tuple

from ..models import Product
from .base import BaseCollector, CollectError
from .jd import JdCollector
from .mock import MockCollector
from .pdd import PddCollector
from .taobao import TaobaoCollector

_COLLECTORS = {
    "jd": JdCollector,
    "taobao": TaobaoCollector,
    "pdd": PddCollector,
    "mock": MockCollector,
}

SUPPORTED_SOURCES = ("mock", "auto", "jd", "taobao", "pdd")


def collect(
    keyword: str,
    source: str = "mock",
    limit: int = 8,
    cookies: str = "",
    timeout: int = 8,
) -> Tuple[List[Product], str, str]:
    """按关键词采集商品。

    返回 (products, source_mode, fallback_reason)：
    - source_mode：实际生效的数据源描述
    - fallback_reason：发生降级时的原因（空串表示未降级）
    """
    if source not in SUPPORTED_SOURCES:
        raise ValueError(f"未知数据源 {source!r}，可选 {SUPPORTED_SOURCES}")

    if source == "mock":
        return MockCollector().search(keyword, limit), "mock", ""

    platforms = list(_COLLECTORS) if source == "auto" else [source]
    if source == "auto":
        platforms = [p for p in ("jd", "taobao", "pdd")]

    collected: List[Product] = []
    reasons: List[str] = []
    for platform in platforms:
        if platform == "mock":
            continue
        collector_cls = _COLLECTORS[platform]
        try:
            items = collector_cls(timeout=timeout, cookies=cookies).search(keyword, limit)
            collected.extend(items)
        except CollectError as e:
            reasons.append(f"{platform}: {e}")

    if collected:
        mode = "+".join(platforms)
        return collected, mode, "; ".join(reasons)

    # 全部失败 -> 降级演示数据
    fallback = MockCollector().search(keyword, limit)
    reason = "真实平台采集失败，已降级到演示数据。 " + "; ".join(reasons) if reasons else ""
    return fallback, "mock(fallback)", reason
