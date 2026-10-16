"""演示数据采集器（Mock）。

作用：在没有真实平台登录态、或真实接口受反爬/验证码限制时，
提供一个确定性的、贴近真实形态的样例数据源，保证 CLI 与网页开箱即用。
同一关键词每次生成的数据保持一致（用关键词哈希做随机种子），便于演示与对比。
"""
from __future__ import annotations

import hashlib
import random
from typing import List

from ..config import PLATFORMS
from ..models import Product
from .base import BaseCollector

# 用于拼装商品标题的品牌/型号/形容词池
_BRANDS = ["华为", "小米", "Apple", "三星", "索尼", "联想", "美的", "格力", "飞利浦", "戴森", "罗技", "安克"]
_ADJ = ["2025新款", "升级版", "旗舰", "高性价比", "热卖", "超薄", "大容量", "智能"]
_UNITS = ["件", "台", "个", "套"]

_SEARCH_URLS = {
    "jd": "https://search.jd.com/Search?keyword={kw}",
    "taobao": "https://s.taobao.com/search?q={kw}",
    "pdd": "https://mobile.yangkeduo.com/search_result.html?search_key={kw}",
}


def _seed(keyword: str) -> int:
    return int(hashlib.md5(keyword.encode("utf-8")).hexdigest()[:8], 16)


class MockCollector(BaseCollector):
    """生成确定性的演示数据，覆盖京东/淘宝/拼多多三个平台。"""

    platform = "mock"

    def search(self, keyword: str, limit: int = 8) -> List[Product]:
        rng = random.Random(_seed(keyword))
        products: List[Product] = []
        for platform in ("jd", "taobao", "pdd"):
            # 每平台条数在 limit 附近小幅浮动，模拟真实差异
            n = max(3, limit - 1 + rng.randint(0, 2))
            for i in range(n):
                brand = rng.choice(_BRANDS)
                adj = rng.choice(_ADJ)
                unit = rng.choice(_UNITS)
                spec = f"{rng.choice(['Pro', 'Max', '青春版', 'Plus', 'Lite', '标准版'])}"
                title = f"{brand} {keyword} {spec} {adj} {rng.randint(1, 12)}{unit}装"

                # 价格：以关键词哈希为基底制造差异化，且跨平台有梯度
                base_price = 30 + (_seed(keyword + platform) % 4000) / 10
                price = round(base_price + rng.uniform(-20, 120), 2)
                price = max(9.9, price)

                sales = rng.randint(200, 200000)
                shop_rating = round(rng.uniform(3.6, 5.0), 1)
                shop_name = f"{brand}官方{platform}店"

                pid = f"{platform}-mock-{_seed(keyword + title):x}"
                url = _SEARCH_URLS[platform].format(kw=keyword.replace(" ", "+"))

                products.append(
                    Product(
                        platform=platform,
                        title=title,
                        price=price,
                        sales=sales,
                        shop_rating=shop_rating,
                        url=url,
                        shop_name=shop_name,
                        product_id=pid,
                    )
                )
        return products
