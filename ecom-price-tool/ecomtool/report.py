"""生成自包含的 HTML 可视化报告（供 CLI --html 使用）。

包含：
- 汇总统计卡片
- 价格横向对比柱状图（Chart.js）
- 价格趋势折线图（性价比 Top 商品多条曲线）
- 按价格升序的商品明细表 + 性价比标注

为避免 Python f-string 与 JS 花括号转义互相打架，这里把 JS 逻辑拆成
普通字符串，仅通过占位符注入 JSON 数据。
"""
from __future__ import annotations

import json

from .config import PLATFORMS
from .models import SearchReport

BADGE_COLOR = {
    "性价比推荐": "#0a7d34",
    "价格优势": "#0d6efd",
    "评分优势": "#8a5cf6",
    "一般": "#6c757d",
}


def _json_safe(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def render_html(report: SearchReport) -> str:
    data = report.to_dict()
    stats = data["stats"]

    platform_name = {k: v["name"] for k, v in PLATFORMS.items()}

    rows = [
        {
            "rank": r["price_rank"],
            "platform": platform_name.get(r["platform"], r["platform"]),
            "title": r["title"],
            "price": r["price"],
            "sales": r["sales"],
            "rating": r["shop_rating"],
            "score": r["value_score"],
            "label": r["value_label"],
            "url": r["url"],
        }
        for r in data["results"]
    ]

    top = sorted(data["results"], key=lambda x: -x["value_score"])[:5]
    payload = {
        "rows": rows,
        "trendTop": [{"title": r["title"][:24], "trend": r["trend"]} for r in top],
        "badge": BADGE_COLOR,
    }

    warn = (
        f'<div class="warn">⚠️ {report.fallback_reason}</div>'
        if report.fallback_reason
        else ""
    )

    head = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>价格对比报告 · {report.keyword}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root {{ --bg:#f5f7fa; --card:#fff; --line:#e6e9ef; --text:#1f2733; --muted:#6b7280; --accent:#2563eb; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; background:var(--bg); color:var(--text); }}
.wrap {{ max-width:1180px; margin:0 auto; padding:24px 20px 60px; }}
header {{ background:linear-gradient(135deg,#1e3a8a,#2563eb); color:#fff; padding:28px 24px; border-radius:14px; }}
header h1 {{ margin:0 0 6px; font-size:24px; }}
header p {{ margin:0; opacity:.85; font-size:13px; }}
.warn {{ background:#fff7e0; color:#8a5d00; padding:10px 14px; border-radius:10px; margin:16px 0; font-size:13px; border:1px solid #ffe2a8; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:14px; margin:20px 0; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; }}
.card .k {{ font-size:12px; color:var(--muted); }}
.card .v {{ font-size:22px; font-weight:700; margin-top:6px; }}
.card .v small {{ font-size:12px; font-weight:400; color:var(--muted); }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
@media(max-width:860px) {{ .grid {{ grid-template-columns:1fr; }} }}
.panel {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px; }}
.panel h2 {{ font-size:15px; margin:0 0 14px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th,td {{ text-align:left; padding:10px 8px; border-bottom:1px solid var(--line); vertical-align:top; }}
th {{ color:var(--muted); font-weight:600; white-space:nowrap; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:20px; font-size:12px; color:#fff; }}
a {{ color:var(--accent); text-decoration:none; }}
tr:hover td {{ background:#f8fafc; }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>🛒 价格采集与对比报告</h1>
  <p>关键词：<b>{report.keyword}</b> ｜ 生成时间：{report.generated_at} ｜ 数据源：{report.source_mode}</p>
</header>
{warn}
<div class="cards">
  <div class="card"><div class="k">采集商品数</div><div class="v">{stats['total']}</div></div>
  <div class="card"><div class="k">最低价</div><div class="v">¥{stats['price_min']}</div></div>
  <div class="card"><div class="k">平均价</div><div class="v">¥{stats['price_avg']}</div></div>
  <div class="card"><div class="k">最高价</div><div class="v">¥{stats['price_max']}</div></div>
  <div class="card"><div class="k">性价比推荐</div><div class="v">{stats['recommended_count']}<small> 款</small></div></div>
</div>
<div class="grid">
  <div class="panel"><h2>价格横向对比（升序）</h2><canvas id="bar" height="260"></canvas></div>
  <div class="panel"><h2>价格趋势（性价比 Top5）</h2><canvas id="trend" height="260"></canvas></div>
</div>
<div class="panel" style="margin-top:16px;"><h2>商品明细（按价格从低到高）</h2>
<table>
<thead><tr><th>#</th><th>平台</th><th>商品名称</th><th>价格</th><th>销量</th><th>评分</th><th>性价比分</th><th>标注</th><th>链接</th></tr></thead>
<tbody id="tbody"></tbody>
</table>
</div>
</div>
"""

    script = """<script>
const DATA = __DATA__;
const tbody = document.getElementById('tbody');
tbody.innerHTML = DATA.rows.map(r => `<tr>
  <td>${r.rank}</td>
  <td>${r.platform}</td>
  <td>${r.title}</td>
  <td><b>¥${r.price}</b></td>
  <td>${r.sales.toLocaleString()}</td>
  <td>${r.rating}</td>
  <td>${r.score}</td>
  <td><span class="badge" style="background:${DATA.badge[r.label] || '#6c757d'}">${r.label}</span></td>
  <td><a href="${r.url}" target="_blank" rel="noopener">查看</a></td>
</tr>`).join('');

if (window.Chart) {
  new Chart(document.getElementById('bar'), {
    type: 'bar',
    data: {
      labels: DATA.rows.map(r => r.platform + '·' + r.title.slice(0, 10)),
      datasets: [{
        label: '价格(¥)',
        data: DATA.rows.map(r => r.price),
        backgroundColor: DATA.rows.map(r => r.label === '性价比推荐' ? '#0a7d34' : '#60a5fa')
      }]
    },
    options: { indexAxis: 'y', plugins: { legend: { display: false } },
      scales: { x: { title: { display: true, text: '价格 (¥)' } } } }
  });

  const colors = ['#2563eb', '#f59e0b', '#0a7d34', '#dc2626', '#8a5cf6'];
  const days = DATA.trendTop.length ? DATA.trendTop[0].trend.length : 0;
  new Chart(document.getElementById('trend'), {
    type: 'line',
    data: {
      labels: Array.from({ length: days }, (_, i) => i === days - 1 ? '今日' : 'T-' + (days - 1 - i)),
      datasets: DATA.trendTop.map((p, i) => ({
        label: p.title, data: p.trend, borderColor: colors[i % colors.length],
        tension: .3, pointRadius: 2, borderWidth: 2, fill: false
      }))
    },
    options: { plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } } },
      scales: { y: { title: { display: true, text: '价格 (¥)' } } } }
  });
}
</script>
</body>
</html>
"""

    return head + script.replace("__DATA__", _json_safe(payload))
