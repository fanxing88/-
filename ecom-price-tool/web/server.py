#!/usr/bin/env python3
"""演示网页服务（零依赖，标准库 http.server）。

启动：python web/server.py [--port 8000]

接口：
- GET /api/search?keyword=...&source=...&limit=...   现场运行采集脚本
- GET /api/sample                                     返回初始化用的数据示例与结果示例
- GET /                                               静态页面
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
PKG = ROOT.parent

sys.path.insert(0, str(PKG))

from ecomtool.collectors.mock import MockCollector  # noqa: E402
from ecomtool.models import Product  # noqa: E402
from ecomtool.runner import run_search  # noqa: E402

SAMPLE_KEYWORD = "蓝牙耳机"


def build_sample() -> dict:
    """构造初始化示例：一份原始数据样例 + 一份完整结果样例。"""
    raw = MockCollector().search(SAMPLE_KEYWORD, limit=5)
    report = run_search(SAMPLE_KEYWORD, source="mock", limit=5, record_history=False)
    return {
        "sample_keyword": SAMPLE_KEYWORD,
        "sample_raw": [p.to_dict() for p in raw[:6]],
        "sample_report": report.to_dict(),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "EcomPrice/1.0"

    def _send_json(self, obj, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, rel: str) -> None:
        if rel in ("", "/"):
            rel = "index.html"
        path = (STATIC / rel.lstrip("/")).resolve()
        if not str(path).startswith(str(STATIC.resolve())) or not path.is_file():
            self.send_error(404)
            return
        body = path.read_bytes()
        ctype = "text/html" if path.suffix == ".html" else (
            "text/javascript" if path.suffix == ".js" else "text/css"
        )
        self.send_response(200)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/search":
            self._handle_search(parsed.query)
        elif parsed.path == "/api/sample":
            self._send_json(build_sample())
        elif parsed.path.startswith("/api/"):
            self._send_json({"error": "未知接口"}, status=404)
        else:
            self._send_file(parsed.path)

    def _handle_search(self, query: str) -> None:
        params = urllib.parse.parse_qs(query)
        keyword = (params.get("keyword", [""])[0] or "").strip()
        if not keyword:
            self._send_json({"error": "关键词不能为空"}, status=400)
            return
        source = params.get("source", ["mock"])[0]
        try:
            limit = int(params.get("limit", ["8"])[0])
        except ValueError:
            limit = 8
        try:
            report = run_search(keyword, source=source, limit=limit)
        except Exception as e:  # noqa: BLE001
            self._send_json({"error": str(e)}, status=500)
            return
        self._send_json(report.to_dict())

    def log_message(self, fmt, *args):  # noqa: A002
        sys.stderr.write("[web] %s\n" % (fmt % args))


def main() -> None:
    ap = argparse.ArgumentParser(description="电商价格对比演示网页")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"演示网页已启动：http://{args.host}:{args.port}")
    print("按 Ctrl+C 停止")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
