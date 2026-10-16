"""拼多多采集器（骨架 + 明确的能力边界说明）。

拼多多移动端/PC 端搜索结果均有较强的反爬（签名、验证码、登录态），
普通 HTTP 抓取无法稳定拿到结构化数据，因此保留接口骨架与注入点，
实际运行抛 CollectError，由上层降级到演示数据。
"""
from __future__ import annotations

import urllib.parse
from typing import List

from ..models import Product
from .base import BaseCollector, CollectError
from ._http import fetch_text


class PddCollector(BaseCollector):
    platform = "pdd"

    def search(self, keyword: str, limit: int = 8) -> List[Product]:
        url = (
            "https://mobile.yangkeduo.com/search_result.html?"
            + urllib.parse.urlencode({"search_key": keyword})
        )
        text = fetch_text(url, self.timeout, self.cookies)
        if "verify" in text.lower() or "goods_id" not in text:
            raise CollectError(
                "拼多多触发反爬/验证，未解析到商品结构（请注入有效 Cookie 后重试）"
            )
        raise CollectError("拼多多解析逻辑待实现")
