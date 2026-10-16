"""数据模型定义。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

# 标题归一化用：去掉品牌/促销噪声与空白，用于跨平台去重
_WS_RE = re.compile(r"\s+")
_NOISE_RE = re.compile(
    r"(官方旗舰店|旗舰店|专卖店|自营|正品|包邮|全新|直营|补贴|plus会员|京东|淘宝|天猫|拼多多)",
    re.IGNORECASE,
)


def normalize_title(title: str) -> str:
    """归一化标题：去空白、去营销噪声、统一小写，用于去重指纹。"""
    t = _WS_RE.sub("", title or "")
    t = _NOISE_RE.sub("", t)
    return t.lower()


@dataclass
class Product:
    """一条采集到的商品原始记录。"""

    platform: str                 # 平台标识：jd / taobao / pdd / mock
    title: str                    # 商品名称
    price: float                  # 当前售价（元）
    sales: int                    # 累计销量
    shop_rating: float            # 店铺评分（0~5）
    url: str                      # 商品/搜索链接
    shop_name: str = ""           # 店铺名称
    product_id: str = ""          # 平台侧商品 ID（去重辅助）

    @property
    def fingerprint(self) -> str:
        """去重指纹：平台 + 归一化标题。"""
        return f"{self.platform}|{normalize_title(self.title)}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProductResult:
    """清洗、排序、分析后的一条结果。"""

    product: Product
    price_rank: int               # 价格从低到高的排名（1 起）
    value_score: float            # 性价比评分（0~100）
    value_label: str              # 推荐标注
    trend: List[float] = field(default_factory=list)   # 近 N 日价格序列
    trend_pct: float = 0.0        # 相对首日涨跌幅（%）
    trend_is_simulated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = self.product.to_dict()
        d.update(
            {
                "price_rank": self.price_rank,
                "value_score": round(self.value_score, 1),
                "value_label": self.value_label,
                "trend": [round(x, 2) for x in self.trend],
                "trend_pct": round(self.trend_pct, 2),
                "trend_is_simulated": self.trend_is_simulated,
            }
        )
        return d


@dataclass
class SearchReport:
    """一次完整搜索任务的输出结果。"""

    keyword: str
    generated_at: str
    source_mode: str              # 实际使用数据源（含降级说明）
    fallback_reason: str = ""
    results: List[ProductResult] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keyword": self.keyword,
            "generated_at": self.generated_at,
            "source_mode": self.source_mode,
            "fallback_reason": self.fallback_reason,
            "stats": self.stats,
            "results": [r.to_dict() for r in self.results],
        }
