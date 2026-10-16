"""电商商品价格自动化采集与对比工具。

本包提供：
- collectors:  可插拔的多平台采集器（京东/淘宝/拼多多 + 演示用 Mock）
- pipeline:    清洗、去重、排序、性价比分析与价格趋势
- exporter:    JSON / CSV / HTML 报告导出
- report:      HTML 可视化报告（横向对比 + 价格趋势图）

设计原则：零第三方依赖，仅使用 Python 标准库，保证可直接运行。
"""

__version__ = "1.0.0"
