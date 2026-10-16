#!/usr/bin/env python3
"""命令行入口：电商商品价格采集与对比工具。

用法示例：
    python cli.py "蓝牙耳机"
    python cli.py "蓝牙耳机" --source mock --limit 10
    python cli.py "蓝牙耳机" -o json -o csv -o html
    python cli.py "蓝牙耳机" --cookies "your_cookie_string"

    # 浏览器自动化真实抓取（先装：pip install playwright && playwright install chromium）
    python cli.py "蓝牙耳机" --source browser --login    # 首次扫码登录并保存登录态
    python cli.py "蓝牙耳机" --source browser --headed   # 显示浏览器窗口抓取（便于手动过验证码）
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ecomtool import exporter
from ecomtool.config import PLATFORMS
from ecomtool.report import render_html
from ecomtool.runner import run_search

BLOCKS = "▁▂▃▄▅▆▇█"


def _dwidth(s: str) -> int:
    """计算终端显示宽度（中日韩全角按 2 计）。"""
    w = 0
    for ch in s:
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def _pad(s: str, width: int, align: str = "left") -> str:
    gap = width - _dwidth(s)
    if gap <= 0:
        return s
    if align == "right":
        return " " * gap + s
    return s + " " * gap


def sparkline(values, width: int = 7) -> str:
    """把价格序列压缩成 Unicode 迷你趋势线。"""
    if not values:
        return ""
    lo, hi = min(values), max(values)
    span = hi - lo or 1
    idx = [int((v - lo) / span * (len(BLOCKS) - 1)) for v in values]
    # 降采样到目标宽度
    step = max(1, len(idx) // width)
    return "".join(BLOCKS[idx[i]] for i in range(0, len(idx), step))[:width]


def print_table(report) -> None:
    pname = {k: v["name"] for k, v in PLATFORMS.items()}
    s = report.stats
    print()
    print(f"关键词：{report.keyword}   数据源：{report.source_mode}   时间：{report.generated_at}")
    if report.fallback_reason:
        print(f"[提示] {report.fallback_reason}")
    print(
        f"共 {s['total']} 款 ｜ 最低 ¥{s['price_min']} ｜ 平均 ¥{s['price_avg']} "
        f"｜ 最高 ¥{s['price_max']} ｜ 性价比推荐 {s['recommended_count']} 款"
    )
    print("-" * 96)

    header = ["#", "平台", "商品名称", "价格", "销量", "评分", "性价比", "标注", "趋势"]
    # 列宽
    widths = [3, 6, 30, 8, 10, 6, 8, 10, 9]
    print(" ".join(_pad(h, widths[i]) for i, h in enumerate(header)))

    for r in report.results:
        p = r.product
        row = [
            str(r.price_rank),
            pname.get(p.platform, p.platform),
            p.title[:28],
            f"¥{p.price:.2f}",
            f"{p.sales:,}",
            f"{p.shop_rating:.1f}",
            f"{r.value_score:.1f}",
            r.value_label,
            sparkline(r.trend),
        ]
        line = " ".join(_pad(c, widths[i]) for i, c in enumerate(row))
        print(line)

    print("-" * 96)
    if s.get("best_value_title"):
        print(f"最值得买（性价比）：{s['best_value_title'][:40]}  (评分 {s['best_value_score']})")
    if s.get("cheapest_title"):
        print(f"价格最低：{s['cheapest_title'][:40]}  (¥{s['cheapest_price']})")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ecom-price",
        description="电商商品价格采集与对比工具（京东/淘宝/拼多多，支持演示数据）",
    )
    parser.add_argument("keyword", nargs="?", help="搜索关键词")
    parser.add_argument(
        "--source",
        default="mock",
        choices=["mock", "auto", "browser", "jd", "taobao", "pdd"],
        help="数据源：mock=演示数据(默认)，browser=浏览器自动化真抓，auto=普通HTTP尝试后降级",
    )
    parser.add_argument("--limit", type=int, default=8, help="每平台采集条数上限（默认 8）")
    parser.add_argument(
        "-o", "--output", action="append", choices=["json", "csv", "html"],
        help="导出格式，可重复使用，如 -o json -o html",
    )
    parser.add_argument("--outdir", default="output", help="导出目录（默认 output）")
    parser.add_argument("--cookies", default="", help="真实平台登录态 Cookie（可选）")
    parser.add_argument("--timeout", type=int, default=8, help="网络超时秒数（默认 8）")
    parser.add_argument("--no-history", action="store_true", help="不写入价格历史快照")
    parser.add_argument("--headed", action="store_true", help="浏览器抓取时显示窗口（便于手动过验证码）")
    parser.add_argument("--login", action="store_true", help="扫码登录各平台并保存登录态（配合 --source browser）")
    args = parser.parse_args(argv)

    if args.login:
        from ecomtool.collectors.browser import login_all
        login_all()
        if not args.keyword:
            return 0

    if not args.keyword:
        parser.print_help()
        return 1

    try:
        report = run_search(
            args.keyword,
            source=args.source,
            limit=args.limit,
            cookies=args.cookies,
            timeout=args.timeout,
            headless=not args.headed,
            record_history=not args.no_history,
        )
    except ValueError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1

    print_table(report)

    if args.output:
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in args.keyword)
        for fmt in args.output:
            if fmt == "json":
                path = outdir / f"{safe}.json"
                exporter.save_file(exporter.to_json(report), str(path))
            elif fmt == "csv":
                path = outdir / f"{safe}.csv"
                exporter.save_file(exporter.to_csv(report), str(path))
            elif fmt == "html":
                path = outdir / f"{safe}.html"
                exporter.save_file(render_html(report), str(path))
            print(f"已导出：{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
