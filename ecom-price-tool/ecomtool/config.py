"""全局配置：平台元信息、评分权重、趋势参数、请求头等。"""
from __future__ import annotations

# 平台元信息
PLATFORMS = {
    "jd": {"name": "京东", "home": "https://www.jd.com/"},
    "taobao": {"name": "淘宝", "home": "https://www.taobao.com/"},
    "pdd": {"name": "拼多多", "home": "https://www.pinduoduo.com/"},
    "mock": {"name": "演示数据", "home": ""},
}

# 性价比评分权重（归一化后的线性加权，和为 1）
SCORE_WEIGHTS = {
    "rating": 0.35,   # 店铺/商品评分
    "sales": 0.35,    # 销量（对数压缩后）
    "price": 0.30,    # 价格（越低分越高）
}

# 判定为"性价比推荐"的分数阈值（百分制）
VALUE_SCORE_THRESHOLD = 72.0

# 价格趋势参数
TREND_DAYS = 7                 # 展示近 N 日价格曲线
TREND_BACKFILL = True          # 首次采集时是否合成模拟历史曲线
HISTORY_FILE = "data/history.json"

# 网络请求参数
HTTP_TIMEOUT = 8               # 秒
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 每平台默认采集条数上限
DEFAULT_LIMIT_PER_PLATFORM = 8
