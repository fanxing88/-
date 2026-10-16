"""基于 Playwright 的浏览器自动化真实采集器。

用途：驱动真实 Chrome 抓取京东 / 淘宝 / 拼多多的商品名称、价格、销量、店铺、链接。

使用前提（在你自己的电脑上执行）：
    pip install playwright
    playwright install chromium

首次扫码登录（会弹出浏览器窗口，登录后回到终端按回车）：
    python cli.py "蓝牙耳机" --source browser --login

之后抓取（自动复用已保存的登录态）：
    python cli.py "蓝牙耳机" --source browser

注意事项：
- 三大平台均有强反爬 / 滑块验证码，遇到时需要在弹出的浏览器窗口里手动通过一次。
- 平台页面结构会改版，下列 CSS 选择器是当前常见结构；若某平台抓不到，
  请按实际页面 DOM 微调对应 _extract 中的选择器（已集中在一起方便修改）。
"""
from __future__ import annotations

import re
import urllib.parse
from pathlib import Path
from typing import List

from ..config import AUTH_DIR, PLATFORMS
from ..models import Product
from .base import BaseCollector, CollectError

_AUTH_DIR = Path(AUTH_DIR)

_HOME_URLS = {
    "jd": "https://www.jd.com/",
    "taobao": "https://www.taobao.com/",
    "pdd": "https://www.pinduoduo.com/",
}

_SEARCH_URLS = {
    "jd": lambda k: f"https://search.jd.com/Search?keyword={k}&enc=utf-8",
    "taobao": lambda k: f"https://s.taobao.com/search?q={k}",
    "pdd": lambda k: f"https://mobile.yangkeduo.com/search_result.html?search_key={k}",
}


def _auth_path(platform: str) -> Path:
    return _AUTH_DIR / f"{platform}.json"


def _import_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError as e:
        raise CollectError(
            "未安装 Playwright，请先执行：pip install playwright && playwright install chromium"
        ) from e


_SALES_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(万|千|亿)?")


def _parse_sales(text: str) -> int:
    """把"1.2万+人付款/已售3.4万件/2.5万+评价"等文本解析为整数销量。"""
    text = (text or "").replace(",", "").replace("+", "")
    m = _SALES_RE.search(text)
    if not m:
        return 0
    num = float(m.group(1))
    unit = m.group(2)
    if unit == "万":
        num *= 10000
    elif unit == "亿":
        num *= 100000000
    elif unit == "千":
        num *= 1000
    return int(num)


def _parse_price(text: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)", (text or "").replace(",", "").replace("¥", ""))
    return float(m.group(1)) if m else 0.0


class BrowserCollector(BaseCollector):
    """浏览器自动化采集器基类：启动 Chrome、加载登录态、打开搜索页并提取。"""

    platform: str = ""

    def __init__(self, timeout: int = 8, cookies: str = "", headless: bool = True) -> None:
        super().__init__(timeout=timeout, cookies=cookies)
        self.headless = headless

    def search(self, keyword: str, limit: int = 8) -> List[Product]:
        sync_playwright = _import_playwright()
        auth = _auth_path(self.platform)
        kw = urllib.parse.quote(keyword)
        url = _SEARCH_URLS[self.platform](kw)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            ctx_kwargs = {}
            if auth.exists():
                ctx_kwargs["storage_state"] = str(auth)
            ctx = browser.new_context(**ctx_kwargs)
            page = ctx.new_page()
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)  # 等待异步渲染
                # 被反爬/登录页拦截的统一检测
                cur = page.url.lower()
                if "login" in cur or "verify" in cur or "captcha" in cur:
                    raise CollectError(
                        f"{PLATFORMS[self.platform]['name']} 触发登录/验证码，请用 --login 先扫码登录"
                    )
                results = self._extract(page, keyword, limit)
            finally:
                browser.close()

        if not results:
            raise CollectError(
                f"{PLATFORMS[self.platform]['name']} 未解析到商品（可能改版需调整选择器，或触发风控）"
            )
        return results

    def _extract(self, page, keyword: str, limit: int) -> List[Product]:
        raise NotImplementedError


class JdBrowserCollector(BrowserCollector):
    platform = "jd"

    def _extract(self, page, keyword: str, limit: int) -> List[Product]:
        page.wait_for_selector("li.gl-item", timeout=20000)
        items = page.query_selector_all("li.gl-item")
        out: List[Product] = []
        for el in items:
            if len(out) >= limit:
                break
            sku = el.get_attribute("data-sku")
            if not sku:  # 跳过无 sku 的推广位
                continue
            title_el = el.query_selector(".p-name em") or el.query_selector(".p-name a")
            title = title_el.inner_text().strip() if title_el else keyword

            price = _parse_price(el.get_attribute("data-price") or "")
            if price <= 0:
                price_el = el.query_selector(".p-price i")
                price = _parse_price(price_el.inner_text() if price_el else "")

            shop_el = el.query_selector(".p-shop a")
            shop = shop_el.inner_text().strip() if shop_el else ""

            commit_el = el.query_selector(".p-commit a")
            sales = _parse_sales(commit_el.inner_text() if commit_el else "")

            out.append(
                Product(
                    platform=self.platform,
                    title=title,
                    price=price,
                    sales=sales,
                    shop_rating=4.5,  # 京东搜索页通常无店铺评分，用中值占位
                    url=f"https://item.jd.com/{sku}.html",
                    shop_name=shop,
                    product_id=sku,
                )
            )
        return out


class TaobaoBrowserCollector(BrowserCollector):
    platform = "taobao"

    def _extract(self, page, keyword: str, limit: int) -> List[Product]:
        # 淘宝改版频繁，这里按候选选择器尝试定位商品卡片
        card_sel = _first_match_selector(
            page,
            ["div[class*='Card--doubleCardWrapper']", ".items .item", "div[class*='content--'] .row"],
            timeout=20000,
        )
        cards = page.query_selector_all(card_sel)
        out: List[Product] = []
        for el in cards:
            if len(out) >= limit:
                break
            title_el = _first(el, ["[class*='title--']", ".title a", ".row-2 a"])
            title = title_el.inner_text().strip() if title_el else keyword
            link = title_el.get_attribute("href") if title_el else ""
            if link and not link.startswith("http"):
                link = "https:" + link

            price_el = _first(el, ["[class*='price--']", ".price strong"])
            price = _parse_price(price_el.inner_text() if price_el else "")

            sales_el = _first(el, ["[class*='deal-cnt']", ".deal-cnt", "[class*='sales']"])
            sales = _parse_sales(sales_el.inner_text() if sales_el else "")

            shop_el = _first(el, ["[class*='shopName']", ".shopname", "[class*='shop']"])
            shop = shop_el.inner_text().strip() if shop_el else ""

            out.append(
                Product(
                    platform=self.platform,
                    title=title,
                    price=price,
                    sales=sales,
                    shop_rating=4.5,  # 搜索页通常无评分，用中值占位
                    url=link or f"https://s.taobao.com/search?q={urllib.parse.quote(keyword)}",
                    shop_name=shop,
                    product_id=title,
                )
            )
        return out


class PddBrowserCollector(BrowserCollector):
    platform = "pdd"

    def _extract(self, page, keyword: str, limit: int) -> List[Product]:
        card_sel = _first_match_selector(
            page,
            ["[class*='goods-item']", ".goods-item", "[class*='search-result'] [class*='item']"],
            timeout=20000,
        )
        cards = page.query_selector_all(card_sel)
        out: List[Product] = []
        for el in cards:
            if len(out) >= limit:
                break
            title_el = _first(el, ["[class*='goods-name']", ".goods-name", "[class*='name']"])
            title = title_el.inner_text().strip() if title_el else keyword

            price_el = _first(el, ["[class*='goods-price']", ".goods-price", "[class*='price']"])
            price = _parse_price(price_el.inner_text() if price_el else "")

            sales_el = _first(el, ["[class*='sales']", ".goods-sales", "[class*='sold']"])
            sales = _parse_sales(sales_el.inner_text() if sales_el else "")

            shop_el = _first(el, ["[class*='mall-name']", "[class*='shop']", "[class*='brand']"])
            shop = shop_el.inner_text().strip() if shop_el else ""

            out.append(
                Product(
                    platform=self.platform,
                    title=title,
                    price=price,
                    sales=sales,
                    shop_rating=4.5,  # 搜索页通常无评分，用中值占位
                    url=page.url,
                    shop_name=shop,
                    product_id=title,
                )
            )
        return out


def _first(el, selectors: List[str]):
    for sel in selectors:
        node = el.query_selector(sel)
        if node:
            return node
    return None


def _first_match_selector(page, selectors: List[str], timeout: int = 20000) -> str:
    """依次尝试各选择器，返回第一个实际出现的；全部失败则抛错。"""
    last_err = None
    for sel in selectors:
        try:
            page.wait_for_selector(sel, timeout=timeout)
            return sel
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise CollectError("未匹配到商品列表结构（页面可能已改版）") from last_err


def login(platform: str) -> None:
    """打开有头浏览器让用户扫码登录，并保存登录态。"""
    sync_playwright = _import_playwright()
    _AUTH_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_context().new_page()
        page.goto(_HOME_URLS[platform], timeout=30000)
        print(f"请在打开的浏览器中完成「{PLATFORMS[platform]['name']}」登录，")
        print("登录成功后回到终端按回车以保存登录态……")
        input()
        page.context.storage_state(path=str(_auth_path(platform)))
        browser.close()
        print(f"登录态已保存：{_auth_path(platform)}")


def login_all() -> None:
    for platform in ("jd", "taobao", "pdd"):
        try:
            login(platform)
        except CollectError as e:
            print(f"[跳过] {platform}: {e}")
