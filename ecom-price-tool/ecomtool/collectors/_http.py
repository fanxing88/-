"""共享的 HTTP 抓取工具（仅标准库 urllib）。"""
from __future__ import annotations

import urllib.error
import urllib.request
from typing import Optional

from ..config import HTTP_HEADERS, HTTP_TIMEOUT
from .base import CollectError


def fetch_text(url: str, timeout: int = HTTP_TIMEOUT, cookies: str = "") -> str:
    """抓取 URL 文本。返回解码后的文本；失败抛 CollectError。

    说明：真实电商平台普遍有反爬/登录/验证码等限制，这里仅做标准库级别的
    尽力而为，不承诺一定能拿到数据——调用方（factory）会自动降级到演示数据。
    """
    headers = dict(HTTP_HEADERS)
    if cookies:
        headers["Cookie"] = cookies

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="ignore")
    except urllib.error.HTTPError as e:
        raise CollectError(f"HTTP {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise CollectError(f"网络错误: {e.reason}") from e
    except TimeoutError as e:
        raise CollectError("请求超时") from e
