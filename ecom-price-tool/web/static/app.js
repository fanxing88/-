/* 前端逻辑：初始化示例渲染 + 现场运行脚本并渲染结果 */
(function () {
  "use strict";

  const PLATFORM_NAMES = { jd: "京东", taobao: "淘宝", pdd: "拼多多", mock: "演示" };
  const BADGE_COLORS = {
    "性价比推荐": "#0a7d34",
    "价格优势": "#0d6efd",
    "评分优势": "#8a5cf6",
    "一般": "#6c757d",
  };
  const TREND_COLORS = ["#2563eb", "#f59e0b", "#0a7d34", "#dc2626", "#8a5cf6"];

  const $ = (sel) => document.querySelector(sel);

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtSales(n) {
    if (n >= 10000) return (n / 10000).toFixed(1) + "万";
    return Number(n).toLocaleString();
  }

  function buildStatsHTML(stats) {
    return `
      <div class="cards">
        <div class="card"><div class="k">采集商品数</div><div class="v">${stats.total}</div></div>
        <div class="card"><div class="k">最低价</div><div class="v">¥${stats.price_min}</div></div>
        <div class="card"><div class="k">平均价</div><div class="v">¥${stats.price_avg}</div></div>
        <div class="card"><div class="k">最高价</div><div class="v">¥${stats.price_max}</div></div>
        <div class="card"><div class="k">性价比推荐</div><div class="v">${stats.recommended_count}<small> 款</small></div></div>
      </div>`;
  }

  function buildTableHTML(results) {
    const rows = results
      .map((r) => {
        const color = BADGE_COLORS[r.value_label] || "#6c757d";
        return `<tr>
          <td class="num">${r.price_rank}</td>
          <td>${PLATFORM_NAMES[r.platform] || r.platform}</td>
          <td>${esc(r.title)}</td>
          <td class="num"><b>¥${r.price.toFixed(2)}</b></td>
          <td class="num">${fmtSales(r.sales)}</td>
          <td class="num">${r.shop_rating.toFixed(1)}</td>
          <td class="num">${r.value_score.toFixed(1)}</td>
          <td><span class="badge" style="background:${color}">${r.value_label}</span></td>
          <td class="num">${r.trend_pct >= 0 ? "+" : ""}${r.trend_pct}%</td>
          <td><a href="${esc(r.url)}" target="_blank" rel="noopener">查看</a></td>
        </tr>`;
      })
      .join("");
    return `<table>
      <thead><tr>
        <th>#</th><th>平台</th><th>商品名称</th><th>价格</th><th>销量</th>
        <th>评分</th><th>性价比分</th><th>标注</th><th>7日涨跌</th><th>链接</th>
      </tr></thead>
      <tbody>${rows}</tbody></table>`;
  }

  function reportBodyHTML(report, idPrefix) {
    return `
      ${buildStatsHTML(report.stats)}
      <div class="grid">
        <div class="panel"><h2>价格横向对比（升序）</h2><canvas id="${idPrefix}-bar"></canvas></div>
        <div class="panel"><h2>价格趋势（性价比 Top5）</h2><canvas id="${idPrefix}-trend"></canvas></div>
      </div>
      <div class="panel" style="margin-top:16px;">
        <h2>商品明细（按价格从低到高）</h2>
        ${buildTableHTML(report.results)}
      </div>`;
  }

  function drawCharts(report, idPrefix) {
    if (!window.Chart) return;
    const results = report.results;

    const barEl = document.getElementById(idPrefix + "-bar");
    if (barEl) {
      new Chart(barEl, {
        type: "bar",
        data: {
          labels: results.map((r) => (PLATFORM_NAMES[r.platform] || r.platform) + "·" + r.title.slice(0, 10)),
          datasets: [{
            label: "价格(¥)",
            data: results.map((r) => r.price),
            backgroundColor: results.map((r) =>
              r.value_label === "性价比推荐" ? "#0a7d34" : "#60a5fa"),
          }],
        },
        options: {
          indexAxis: "y",
          plugins: { legend: { display: false } },
          scales: { x: { title: { display: true, text: "价格 (¥)" } } },
        },
      });
    }

    const trendEl = document.getElementById(idPrefix + "-trend");
    if (trendEl) {
      const top = [...results].sort((a, b) => b.value_score - a.value_score).slice(0, 5);
      const days = top.length ? top[0].trend.length : 0;
      const labels = Array.from({ length: days }, (_, i) =>
        i === days - 1 ? "今日" : "T-" + (days - 1 - i));
      new Chart(trendEl, {
        type: "line",
        data: {
          labels,
          datasets: top.map((r, i) => ({
            label: r.title.slice(0, 20),
            data: r.trend,
            borderColor: TREND_COLORS[i % TREND_COLORS.length],
            tension: 0.3,
            pointRadius: 2,
            borderWidth: 2,
            fill: false,
          })),
        },
        options: {
          plugins: {
            legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 10 } } },
          },
          scales: { y: { title: { display: true, text: "价格 (¥)" } } },
        },
      });
    }
  }

  function renderReport(report, container, idPrefix, title, subtitle) {
    container.innerHTML = `
      <div class="section-title">📊 ${esc(title)}
        <span class="badge" style="background:#3730a3">${esc(subtitle)}</span>
      </div>
      ${reportBodyHTML(report, idPrefix)}`;
    drawCharts(report, idPrefix);
  }

  function renderSample(data) {
    const raw = data.sample_raw || [];
    const rawHTML = raw
      .map(
        (p) => `<div class="raw-item">
          <span class="tag">${PLATFORM_NAMES[p.platform] || p.platform}</span>
          <div class="t">${esc(p.title)}</div>
          <div class="meta">¥${p.price.toFixed(2)} ｜ 销量 ${fmtSales(p.sales)} ｜ 评分 ${p.shop_rating}</div>
          <div class="meta">店铺：${esc(p.shop_name)}</div>
          <a href="${esc(p.url)}" target="_blank" rel="noopener">查看链接</a>
        </div>`
      )
      .join("");

    const sample = data.sample_report;
    const area = document.getElementById("sample-area");
    area.innerHTML = `
      <div class="section-title">🧪 初始化示例（关键词：${esc(data.sample_keyword)}）</div>
      <div class="two-col">
        <div class="panel">
          <h2>① 数据示例 — 原始采集记录</h2>
          <div class="raw-grid">${rawHTML}</div>
        </div>
        <div class="panel">
          <h2>② 结果示例 — 清洗 · 排序 · 分析后</h2>
          <div id="sample-result-slot"></div>
        </div>
      </div>`;
    renderReport(
      sample,
      document.getElementById("sample-result-slot"),
      "sample",
      "结果示例",
      "示例"
    );
  }

  async function loadSample() {
    try {
      const resp = await fetch("/api/sample");
      const data = await resp.json();
      renderSample(data);
    } catch (e) {
      document.getElementById("warn-box").innerHTML =
        '<div class="warn">加载示例失败：' + esc(e.message) + "</div>";
    }
  }

  async function runSearch() {
    const keyword = document.getElementById("keyword").value.trim();
    if (!keyword) {
      document.getElementById("warn-box").innerHTML =
        '<div class="warn">请先输入关键词。</div>';
      return;
    }
    const source = document.getElementById("source").value;
    const limit = document.getElementById("limit").value || "8";
    const headed = document.getElementById("headed").checked;
    const headless = headed ? "0" : "1";
    const btn = document.getElementById("run");
    const spinner = document.getElementById("spinner");

    btn.disabled = true;
    spinner.style.display = "block";
    document.getElementById("warn-box").innerHTML = "";

    try {
      const qs = new URLSearchParams({ keyword, source, limit, headless });
      const resp = await fetch("/api/search?" + qs.toString());
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.error || "请求失败");
      }
      const container = document.getElementById("result-area");
      const note = data.fallback_reason ? "（含降级说明）" : "";
      renderReport(
        data,
        container,
        "live",
        "采集结果 — " + keyword,
        "实时运行" + note
      );
      if (data.fallback_reason) {
        document.getElementById("warn-box").innerHTML =
          '<div class="warn">' + esc(data.fallback_reason) + "</div>";
      }
    } catch (e) {
      document.getElementById("warn-box").innerHTML =
        '<div class="warn">运行失败：' + esc(e.message) + "</div>";
    } finally {
      btn.disabled = false;
      spinner.style.display = "none";
    }
  }

  document.getElementById("run").addEventListener("click", runSearch);
  document.getElementById("keyword").addEventListener("keydown", (e) => {
    if (e.key === "Enter") runSearch();
  });

  document.getElementById("login").addEventListener("click", loginAll);

  async function loginAll() {
    const platforms = ["jd", "taobao", "pdd"];
    const btn = document.getElementById("login");
    const warnBox = document.getElementById("warn-box");
    btn.disabled = true;
    for (const p of platforms) {
      warnBox.innerHTML = `<div class="hint">正在登录「${p}」，请在弹出的浏览器窗口扫码登录……</div>`;
      try {
        const resp = await fetch("/api/login?platform=" + p);
        const data = await resp.json();
        warnBox.innerHTML = `<div class="${data.ok ? "hint" : "warn"}">${esc(data.message || data.error)}</div>`;
      } catch (e) {
        warnBox.innerHTML = `<div class="warn">登录失败：${esc(e.message)}</div>`;
        break;
      }
    }
    btn.disabled = false;
  }

  loadSample();
})();
