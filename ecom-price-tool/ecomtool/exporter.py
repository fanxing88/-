"""结果导出：JSON / CSV。"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import List

from .models import SearchReport

_CSV_FIELDS = [
    "price_rank",
    "platform",
    "title",
    "price",
    "sales",
    "shop_rating",
    "shop_name",
    "value_score",
    "value_label",
    "trend_pct",
    "url",
]


def to_json(report: SearchReport, indent: int = 2) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=indent)


def to_csv(report: SearchReport) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for r in report.results:
        row = r.to_dict()
        # 展开 platform 便于阅读
        row["platform"] = r.product.platform
        writer.writerow(row)
    return buf.getvalue()


def save_file(content: str, path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
