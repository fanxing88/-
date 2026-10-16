"""数据清洗、去重、排序与性价比分析管道。"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

from .config import SCORE_WEIGHTS, VALUE_SCORE_THRESHOLD
from .models import Product, ProductResult, normalize_title


def clean(products: List[Product]) -> List[Product]:
    """清洗：过滤无效记录、规整字段。

    规则：
    - 丢弃标题为空、价格 <= 0 的记录
    - 评分裁剪到 [0, 5]，缺失时用中值 4.5 填充
    - 销量负值归零
    """
    out: List[Product] = []
    for p in products:
        if not p.title or not p.title.strip():
            continue
        if p.price <= 0:
            continue
        p.title = " ".join(p.title.split())  # 压缩空白
        if not (0 < p.shop_rating <= 5):
            p.shop_rating = 4.5
        if p.sales < 0:
            p.sales = 0
        out.append(p)
    return out


def dedupe(products: List[Product]) -> List[Product]:
    """去重：同平台内按归一化标题去重，保留信息更完整的一条。

    跨平台不去重——不同平台间的同一商品是"横向对比"的核心价值。
    """
    seen: Dict[str, Product] = {}
    for p in products:
        key = p.fingerprint
        if key not in seen:
            seen[key] = p
            continue
        # 信息更完整（有店铺名/销量更大）则替换
        old = seen[key]
        if (p.shop_name and not old.shop_name) or p.sales > old.sales:
            seen[key] = p
    return list(seen.values())


def sort_by_price(products: List[Product]) -> List[Product]:
    """按价格从低到高排序。"""
    return sorted(products, key=lambda p: (p.price, -p.sales))


def score_products(products: List[Product]) -> List[ProductResult]:
    """计算性价比评分并打标签，返回附带排名的结果列表。"""
    if not products:
        return []

    prices = [p.price for p in products]
    ratings = [p.shop_rating for p in products]
    log_sales = [math.log1p(p.sales) for p in products]

    p_min, p_max = min(prices), max(prices)
    r_min, r_max = min(ratings), max(ratings)
    s_min, s_max = min(log_sales), max(log_sales)

    def norm(v, lo, hi):
        return 0.0 if hi == lo else (v - lo) / (hi - lo)

    price_q1 = sorted(prices)[max(0, len(prices) // 4)]

    results: List[ProductResult] = []
    for rank, p in enumerate(products, start=1):
        rating_n = norm(p.shop_rating, r_min, r_max)
        sales_n = norm(math.log1p(p.sales), s_min, s_max)
        price_n = norm(p.price, p_min, p_max)          # 越贵越接近 1
        price_score = 1.0 - price_n                    # 越便宜分越高

        score = 100 * (
            SCORE_WEIGHTS["rating"] * rating_n
            + SCORE_WEIGHTS["sales"] * sales_n
            + SCORE_WEIGHTS["price"] * price_score
        )

        # 标注
        if score >= VALUE_SCORE_THRESHOLD:
            label = "性价比推荐"
        elif p.price <= price_q1:
            label = "价格优势"
        elif p.shop_rating >= 4.7:
            label = "评分优势"
        else:
            label = "一般"

        results.append(
            ProductResult(
                product=p,
                price_rank=rank,
                value_score=round(score, 1),
                value_label=label,
            )
        )
    return results


def compute_stats(results: List[ProductResult], source_mode: str) -> Dict:
    """汇总统计信息。"""
    prices = [r.product.price for r in results]
    platforms = sorted({r.product.platform for r in results})
    best = max(results, key=lambda r: r.value_score) if results else None
    cheapest = results[0] if results else None  # 已按价格排序
    return {
        "total": len(results),
        "platforms": platforms,
        "price_min": round(min(prices), 2) if prices else 0,
        "price_max": round(max(prices), 2) if prices else 0,
        "price_avg": round(sum(prices) / len(prices), 2) if prices else 0,
        "cheapest_title": cheapest.product.title if cheapest else "",
        "cheapest_price": cheapest.product.price if cheapest else 0,
        "best_value_title": best.product.title if best else "",
        "best_value_score": best.value_score if best else 0,
        "recommended_count": sum(1 for r in results if r.value_label == "性价比推荐"),
        "source_mode": source_mode,
    }
