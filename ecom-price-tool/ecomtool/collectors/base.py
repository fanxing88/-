"""采集器基类与异常。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..models import Product


class CollectError(Exception):
    """采集失败（网络/解析/反爬/未登录等）。"""


class BaseCollector(ABC):
    """所有平台采集器的统一接口。"""

    platform: str = ""

    def __init__(self, timeout: int = 8, cookies: str = "") -> None:
        self.timeout = timeout
        self.cookies = cookies  # 可选：用户自行注入的登录态 Cookie

    @abstractmethod
    def search(self, keyword: str, limit: int = 8) -> List[Product]:
        """按关键词搜索并返回商品列表，失败时抛 CollectError。"""
        raise NotImplementedError
