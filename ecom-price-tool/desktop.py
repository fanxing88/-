#!/usr/bin/env python3
"""桌面/本机一键启动入口。

在本地启动内置 HTTP 服务并自动用默认浏览器打开演示页面。
既是"本机一键启动"的入口，也是 PyInstaller 打包成单文件可执行程序的入口。

用法：
    python desktop.py            # 自动选空闲端口并打开浏览器
    python desktop.py --port 8000
"""
from __future__ import annotations

import argparse
import socket
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from web.server import Handler  # noqa: E402


def pick_port(preferred: int = 8000) -> int:
    """从 preferred 开始找一个空闲端口。"""
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return preferred


def main() -> None:
    ap = argparse.ArgumentParser(description="电商价格对比工具（本地启动）")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-browser", action="store_true", help="只启动服务，不自动打开浏览器")
    args = ap.parse_args()

    port = pick_port(args.port)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    print(f"服务已启动：{url}")
    if not args.no_browser:
        print("浏览器即将自动打开；关闭本窗口即可停止。")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
