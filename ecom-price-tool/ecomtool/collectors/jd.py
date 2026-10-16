"""京东采集器（尽力而为的真实抓取）。

京东搜索页 `search.jd.com` 返回的 HTML 中，商品项形如
`<li class="gl-item" data-sku="..." data-price="123.00">`，
标题位于 `.p-name` 节点内。这里用正则做轻量抽取。

注意：受风控/登录态影响可能失败或返回空结果，调用方会降级到演示数据。
"""
from __future__ import annotations

import html
import re
import urllib.parse
from typing import List

from ..models import Product
from .base import BaseCollector, CollectError
from ._http import fetch_text

_PLATFORM = "jd"


class JdCollector(BaseCollector):
    platform = _PLATFORM

    def search(self, keyword: str, limit: int = 8) -> List[Product]:
        url = (
            "https://search.jd.com/Search?"
            + urllib.parse.urlencode({"keyword": keyword, "enc": "utf-8", "page": 1})
        )
        text = fetch_text(url, self.timeout, self.cookies)

        # 商品块：data-sku + data-price 是核心字段
        items = re.findall(
            r'<li\s+class="gl-item".*?data-sku="(\d+)".*?data-price="([\d.]+)"',
            text,
            re.S,
        )
        if not items:
            raise CollectError("未解析到商品（可能触发风控，需登录态 Cookie）")

        products: List[Product] = []
        for sku, price in items[: limit * 2]:
            # 粗略定位标题与销量：在 data-sku 附近截取一段
            pos = text.find(f'data-sku="{sku}"')
            seg = text[pos : pos + 4000]
            m_title = re.search(r'<em>([^<]+)</em>', seg)
            title = html.unescape(m_title.group(1)).strip() if m_title else keyword
            m_shop = re.search(r'class="p-shop".*?>([^<]+)<', seg, re.S)
            shop_name = m_shop.group(1).strip() if m_shop else ""
            m_sales = re.search(r"(\d+\.?\d*)\s*万?\+?\s*人?(?:评价|已售)", seg)
            sales = int(float(m_sales.group(1)) * 10000) if m_sales else 0

            products.append(
                Product(
                    platform=_PLATFORM,
                    title=title,
                    price=float(price),
                    sales=sales,
                    shop_rating=4.5,  # 页面非登录态通常拿不到评分，先用中值占位
                    url=f"https://item.jd.com/{sku}.html",
                    shop_name=shop_name,
                    product_id=sku,
                )
            )
            if len(products) >= limit:
                break

        if not products:
            raise CollectError("未解析到商品")
        return products
