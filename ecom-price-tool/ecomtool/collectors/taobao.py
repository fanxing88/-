"""淘宝/天猫采集器（骨架 + 明确的能力边界说明）。

淘宝搜索结果由 JS 动态渲染，且强依赖登录态 + 滑块验证码，
无浏览器环境/登录态时无法通过简单 HTTP 抓取到结构化数据。
因此这里仅保留接口骨架与 Cookie 注入点，实际运行会抛出
CollectError，由上层统一降级到演示数据。

如你已有合法登录态 Cookie，可通过构造函数传入 self.cookies，
并在 `search` 中替换为真实的接口/解析实现。
"""
from __future__ import annotations

import urllib.parse
from typing import List

from ..models import Product
from .base import BaseCollector, CollectError
from ._http import fetch_text


class TaobaoCollector(BaseCollector):
    platform = "taobao"

    def search(self, keyword: str, limit: int = 8) -> List[Product]:
        url = "https://s.taobao.com/search?" + urllib.parse.urlencode({"q": keyword})
        text = fetch_text(url, self.timeout, self.cookies)
        # 未登录时页面不包含商品结构数据，此处作为示例仅检测是否被拦截。
        if "login" in text.lower() or "data-nid" not in text:
            raise CollectError(
                "淘宝需要登录态/滑块验证，未解析到商品结构（请注入有效 Cookie 后重试）"
            )
        raise CollectError("淘宝解析逻辑待实现")
