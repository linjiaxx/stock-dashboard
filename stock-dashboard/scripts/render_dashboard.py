#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票仪表盘渲染
将所有数据渲染成一张商业风格的蓝色仪表盘图片
需要: pip install jinja2 weasyprint pillow
"""

import os
import sys
import json
import io
import base64
import argparse
from datetime import datetime

# ─────────────────────────────────────────────
# 路径
# ─────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR  = os.path.dirname(SCRIPT_DIR)
ASSETS_DIR = os.path.join(SKILL_DIR, "assets")


# ─────────────────────────────────────────────
# 读取 HTML 模板
# ─────────────────────────────────────────────
def load_template(name="dashboard.html"):
    path = os.path.join(ASSETS_DIR, name)
    if not os.path.exists(path):
        # 回退到当前目录
        path = name
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ─────────────────────────────────────────────
# 图片 → Base64
# ─────────────────────────────────────────────
def img_to_b64(buf, fmt="PNG"):
    if buf is None:
        return ""
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode("utf-8")


# ─────────────────────────────────────────────
# 涨跌颜色
# ─────────────────────────────────────────────
def up_down_color(val, ref):
    if val > ref:
        return "#00D4AA", "+"
    elif val < ref:
        return "#FF4D6A", ""
    else:
        return "#7EB8E8", ""


# ─────────────────────────────────────────────
# 格式化数字
# ─────────────────────────────────────────────
def fmt_price(v, decimals=2):
    if v is None:
        return "—"
    return f"{v:.{decimals}f}"


def fmt_pct(v):
    if v is None:
        return "—%"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"


def fmt_vol(v):
    if v is None or v == 0:
        return "—"
    if v >= 1e8:
        return f"{v/1e8:.2f}亿"
    elif v >= 1e4:
        return f"{v/1e4:.2f}万"
    else:
        return f"{v:.0f}"


# ─────────────────────────────────────────────
# 行情摘要卡片
# ─────────────────────────────────────────────
def make_quote_card(stock, buf_min, buf_daily):
    """生成单只股票的行情摘要 HTML"""
    daily = stock.get("daily", [])
    if not daily:
        close, change, chg_pct, ref_price = "—", 0, 0, 0
        vol = 0
    else:
        today = daily[-1]
        prev  = daily[-2] if len(daily) >= 2 else daily[-1]
        close = today["close"]
        ref_price = prev["close"]
        change    = close - ref_price
        chg_pct   = change / ref_price * 100 if ref_price else 0
        vol = today["volume"]

    color, sign = up_down_color(close, ref_price)
    arrow = "▲" if close >= ref_price else "▼"

    minute_img = img_to_b64(buf_min)
    daily_img  = img_to_b64(buf_daily)

    # 资讯摘要
    news = stock.get("news", [])[:3]
    news_html = ""
    for n in news:
        news_html += f"""
        <div class="news-item">
            <span class="news-tag">热</span>
            <span class="news-title">{n.get('title','')[:40]}</span>
        </div>"""

    card = f"""
<div class="stock-card">
    <div class="card-header">
        <div class="stock-title">
            <span class="stock-name">{stock['name']}</span>
            <span class="stock-code">{stock['code']}</span>
        </div>
        <div class="price-block">
            <span class="price" style="color:{color}">{fmt_price(close)}</span>
            <span class="change" style="color:{color}">{arrow} {sign}{fmt_price(abs(change))} ({fmt_pct(chg_pct)})</span>
        </div>
    </div>
    <div class="charts-row">
        <div class="chart-cell">
            <div class="chart-label">📈 分时图</div>
            <img class="chart-img" src="{minute_img}" alt="分时图" />
        </div>
        <div class="chart-cell">
            <div class="chart-label">📊 日线图</div>
            <img class="chart-img" src="{daily_img}" alt="日线图" />
        </div>
    </div>
    <div class="news-section">
        <div class="section-label">📰 今日资讯</div>
        {news_html}
    </div>
</div>"""
    return card


# ─────────────────────────────────────────────
# 五浪分析摘要
# ─────────────────────────────────────────────
def make_wave_summary(wave_result):
    """生成波浪分析摘要 HTML"""
    if not wave_result or wave_result.get("error"):
        return '<div class="wave-section"><p>暂无波浪数据</p></div>'

    analysis = wave_result["analysis"]
    fib      = wave_result.get("fib", {})
    strategies = wave_result.get("strategies", [])

    fib_html = ""
    if fib:
        for k, v in fib.items():
            fib_html += f'<span class="fib-tag">{k} → {v}</span>'

    strategies_html = ""
    for st in strategies[:3]:
        emoji = {"buy": "🟢", "sell": "🔴", "neutral": "🟡"}.get(st.get("signal","neutral"), "⚪")
        strategies_html += f'<div class="strategy-item">{emoji} {st.get("action","")}: {st.get("reason","")}</div>'

    waves_html = ""
    for w in analysis.get("waves", [])[:5]:
        waves_html += f'''
        <div class="wave-item">
            <span class="wave-badge">浪{w['wave']}</span>
            <span class="wave-type">{w['type']}</span>
            <span class="wave-chg">{fmt_pct(w['change_pct'])}</span>
            <span class="wave-dates">{w['start_date']} ~ {w['end_date']}</span>
        </div>'''

    html = f'''
<div class="wave-section">
    <div class="section-title">🌊 五浪理论分析 · {analysis.get('current_phase','数据不足')}</div>
    <div class="wave-grid">
        {waves_html}
    </div>
    <div class="fib-row">{fib_html}</div>
    <div class="strategy-block">
        <div class="strategy-label">📋 操作策略</div>
        {strategies_html}
    </div>
</div>'''
    return html


# ─────────────────────────────────────────────
# 渲染完整仪表盘
# ─────────────────────────────────────────────
def render(stocks_data, wave_results, output_html="dashboard.html", output_img=None):
    """
    stocks_data:   fetch_stock.py 返回的完整列表
    wave_results:  wave_analysis.py 返回的列表
    """
    template = load_template("dashboard.html")

    # 生成卡片
    cards_html = ""
    wave_map   = {r["stock"]["code"]: r for r in wave_results}

    from generate_chart import generate_charts

    for stock in stocks_data:
        buf_min, buf_daily = generate_charts(stock)
        cards_html += make_quote_card(stock, buf_min, buf_daily)
        wave_result = wave_map.get(stock["code"], {})
        cards_html += make_wave_summary(wave_result)

    # 全局信息
    now_str  = datetime.now().strftime("%Y-%m-%d %H:%M")
    top_info = f"⏰ 报告时间: {now_str}  |  覆盖: {', '.join(s['name'] for s in stocks_data)}"

    html = template.replace("{{REPORT_TIME}}", now_str) \
                   .replace("{{TOP_INFO}}",      top_info) \
                   .replace("{{STOCK_CARDS}}",   cards_html)

    # 保存 HTML
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[HTML] → {output_html}")

    # 生成图片（需要 weasyprint）
    if output_img:
        try:
            from weasyprint import HTML as WPHTML
            WPHTML(filename=output_html).write_png(output_img)
            print(f"[PNG]  → {output_img}")
        except Exception as e:
            print(f"[weasyprint not available: {e}]，请手动用浏览器截图 {output_html}")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="渲染股票仪表盘")
    parser.add_argument("--input",   default="fetch_result.json",  help="fetch_stock.py 输出文件")
    parser.add_argument("--output",   default="dashboard.html",     help="输出 HTML")
    parser.add_argument("--png",      default="dashboard.png",      help="输出 PNG 图片")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        stocks_data = json.load(f)

    wave_results = []
    from wave_analysis import analyze
    for stock in stocks_data:
        wave_results.append(analyze(stock))

    render(stocks_data, wave_results, output_html=args.output, output_img=args.png)
