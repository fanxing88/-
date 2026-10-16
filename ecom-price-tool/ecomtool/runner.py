"""编排入口：采集 -> 清洗 -> 去重 -> 排序 -> 分析 -> 趋势 -> 统计。

CLI 与 Web 服务都复用该函数，保证行为一致。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .collectors import collect
from .config import DEFAULT_LIMIT_PER_PLATFORM
from .models import Product, ProductResult, SearchReport
from .pipeline import clean, compute_stats, dedupe, score_products, sort_by_price
from .trends import HistoryStore


def run_search(
    keyword: str,
    source: str = "mock",
    limit: int = DEFAULT_LIMIT_PER_PLATFORM,
    cookies: str = "",
    timeout: int = 8,
    record_history: bool = True,
) -> SearchReport:
    """执行一次完整搜索任务。

    参数：
    - keyword: 搜索关键词
    - source:  数据源（mock / auto / jd / taobao / pdd）
    - limit:   每平台采集条数上限
    - cookies: 可选登录态 Cookie（真实平台采集时注入）
    - record_history: 是否写入价格历史快照（用于价格趋势）
    """
    keyword = (keyword or "").strip()
    if not keyword:
        raise ValueError("关键词不能为空")

    products, source_mode, fallback_reason = collect(
        keyword, source=source, limit=limit, cookies=cookies, timeout=timeout
    )

    cleaned = clean(products)
    deduped = dedupe(cleaned)
    sorted_products = sort_by_price(deduped)
    results = score_products(sorted_products)

    # 附加价格趋势
    if record_history:
        store = HistoryStore()
        for r in results:
            trend, pct, simulated = store.record(keyword, r.product)
            r.trend = trend
            r.trend_pct = pct
            r.trend_is_simulated = simulated

    stats = compute_stats(results, source_mode)
    return SearchReport(
        keyword=keyword,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        source_mode=source_mode,
        fallback_reason=fallback_reason,
        results=results,
        stats=stats,
    )
