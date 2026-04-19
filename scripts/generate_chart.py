#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成分时图和日线K线图
需要: pip install matplotlib pillow
"""

import sys
import os
import json
import base64
import io

# ─────────────────────────────────────────────
# 图表配色（商业蓝色系）
# ─────────────────────────────────────────────
COLORS = {
    "bg":         "#0A1628",   # 深蓝背景
    "grid":       "#1E3A5F",   # 网格线
    "up":         "#00D4AA",   # 上涨（青绿）
    "down":       "#FF4D6A",   # 下跌（红）
    "neutral":    "#4A9EFF",   # 平盘（蓝）
    "text":       "#E8F4FF",   # 主文字
    "subtext":    "#7EB8E8",   # 副文字
    "ma5":        "#FFD700",   # MA5 黄
    "ma10":       "#FF8C00",   # MA10 橙
    "ma20":       "#9370DB",   # MA20 紫
    "volume_up":  "rgba(0,212,170,0.5)",
    "volume_down":"rgba(255,77,106,0.5)",
    "accent":     "#4A9EFF",   # 强调色
}

# ─────────────────────────────────────────────
# 懒加载 matplotlib（避免 CI 环境中报错）
# ─────────────────────────────────────────────
_mpl_ok = None

def check_mpl():
    global _mpl_ok
    if _mpl_ok is None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            import matplotlib.ticker as mticker
            _mpl_ok = (matplotlib, plt, mdates, mticker)
        except Exception as e:
            print(f"[matplotlib not available] {e}", file=sys.stderr)
            _mpl_ok = False
    return _mpl_ok


# ─────────────────────────────────────────────
# 分时图
# ─────────────────────────────────────────────
def plot_minute(stock_data, output_path=None):
    """
    生成分时图（叠加成交量柱状图）
    """
    mpl = check_mpl()
    if not mpl:
        return None
    matplotlib, plt, mdates, mticker = mpl

    minute = stock_data.get("minute", [])
    if not minute:
        print(f"[warn] 无分时数据: {stock_data.get('name')}", file=sys.stderr)
        return None

    times  = list(range(len(minute)))
    prices = [m["price"] for m in minute]
    vols   = [m["volume"] for m in minute]

    # 计算均价线
    avg_prices = []
    cum_vol = cum_val = 0
    for m in minute:
        cum_vol += m["volume"]
        cum_val += m["price"] * m["volume"]
        avg_prices.append(cum_val / cum_vol if cum_vol else m["price"])

    fig, (ax_price, ax_vol) = plt.subplots(
        2, 1, figsize=(12, 7),
        gridspec_kw={"height_ratios": [3, 1]},
        facecolor=COLORS["bg"]
    )
    fig.subplots_adjust(hspace=0.05)

    # ── 价格线 ──
    ax_price.set_facecolor(COLORS["bg"])
    # 昨收参考线（取第一条数据的均价作为参考）
    ref = prices[0] if prices else 0
    ax_price.axhline(ref, color=COLORS["subtext"], linestyle="--", linewidth=0.8, alpha=0.6)
    ax_price.text(len(times)-1, ref, f"昨收 {ref:.2f}", color=COLORS["subtext"],
                  fontsize=8, va="bottom", ha="right")

    # 涨跌判断颜色
    first_price = prices[0]
    last_price  = prices[-1] if prices else first_price
    line_color  = COLORS["up"] if last_price >= first_price else COLORS["down"]

    ax_price.plot(times, prices, color=line_color, linewidth=1.8, label="价格")
    ax_price.plot(times, avg_prices, color=COLORS["accent"], linewidth=1.2,
                  linestyle="--", label="均价")
    ax_price.set_ylabel("价格", color=COLORS["text"], fontsize=10)
    ax_price.tick_params(axis="x", colors="none")
    ax_price.tick_params(axis="y", colors=COLORS["subtext"], labelsize=8)
    ax_price.grid(True, color=COLORS["grid"], linestyle="-", linewidth=0.4, alpha=0.5)
    ax_price.spines["top"].set_visible(False)
    ax_price.spines["right"].set_visible(False)
    ax_price.spines["bottom"].set_visible(False)
    ax_price.spines["left"].set_color(COLORS["grid"])

    # 标题
    change = (last_price - first_price) / first_price * 100 if first_price else 0
    sign   = "+" if change >= 0 else ""
    title  = f"{stock_data['name']} ({stock_data['code']})  分时图  {last_price:.2f}  {sign}{change:.2f}%"
    ax_price.set_title(title, color=COLORS["text"], fontsize=13, fontweight="bold", pad=8)

    # ── 成交量柱 ──
    ax_vol.set_facecolor(COLORS["bg"])
    bar_colors = [
        COLORS["volume_up"] if p >= first_price else COLORS["volume_down"]
        for p in prices
    ]
    ax_vol.bar(times, vols, color=bar_colors, width=0.8)
    ax_vol.set_ylabel("成交量", color=COLORS["subtext"], fontsize=8)
    ax_vol.tick_params(axis="both", colors=COLORS["subtext"], labelsize=7)
    ax_vol.grid(True, color=COLORS["grid"], linestyle="-", linewidth=0.3, alpha=0.4)
    ax_vol.spines["top"].set_visible(False)
    ax_vol.spines["right"].set_visible(False)
    ax_vol.spines["bottom"].set_color(COLORS["grid"])
    ax_vol.spines["left"].set_color(COLORS["grid"])

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=COLORS["bg"], edgecolor="none")
    buf.seek(0)
    plt.close(fig)

    if output_path:
        with open(output_path, "wb") as f:
            f.write(buf.read())
        buf.seek(0)

    return buf


# ─────────────────────────────────────────────
# 日线K线图
# ─────────────────────────────────────────────
def plot_daily(stock_data, output_path=None):
    """
    生成日线K线图（含MA5/MA10/MA20）
    """
    mpl = check_mpl()
    if not mpl:
        return None
    matplotlib, plt, mdates, mticker = mpl

    daily = stock_data.get("daily", [])
    if not daily:
        print(f"[warn] 无日线数据: {stock_data.get('name')}", file=sys.stderr)
        return None

    # 最近60天
    daily = daily[-60:]
    dates = [d["date"] for d in daily]
    opens  = [d["open"]  for d in daily]
    closes = [d["close"] for d in daily]
    highs  = [d["high"]  for d in daily]
    lows   = [d["low"]   for d in daily]

    # 转换日期用于 matplotlib
    import datetime
    xdates = [datetime.datetime.strptime(d, "%Y-%m-%d") for d in dates]
    x      = list(range(len(dates)))

    # MA 计算
    def ma(values, n):
        result = []
        for i, v in enumerate(values):
            if i < n - 1:
                result.append(float("nan"))
            else:
                result.append(sum(values[i-n+1:i+1]) / n)
        return result

    ma5  = ma(closes, 5)
    ma10 = ma(closes, 10)
    ma20 = ma(closes, 20)

    # K线颜色
    up_color   = COLORS["up"]
    down_color = COLORS["down"]

    fig, (ax_k, ax_vol) = plt.subplots(
        2, 1, figsize=(12, 7),
        gridspec_kw={"height_ratios": [3, 1]},
        facecolor=COLORS["bg"]
    )
    fig.subplots_adjust(hspace=0.05)

    for i in range(len(daily)):
        open_  = opens[i]
        close_ = closes[i]
        color  = up_color if close_ >= open_ else down_color
        Wick_color = color
        body_height = abs(close_ - open_) or open_ * 0.005

        ax_k.plot([x[i], x[i]], [lows[i], highs[i]],  color=Wick_color, linewidth=0.8)
        rect = plt.Rectangle(
            (x[i] - 0.35, min(open_, close_)),
            0.7, body_height,
            facecolor=color, edgecolor=color, linewidth=0.5
        )
        ax_k.add_patch(rect)

    ax_k.plot(x, ma5,  color=COLORS["ma5"],  linewidth=1.2, label="MA5")
    ax_k.plot(x, ma10, color=COLORS["ma10"], linewidth=1.2, label="MA10")
    ax_k.plot(x, ma20, color=COLORS["ma20"], linewidth=1.2, label="MA20")
    ax_k.legend(loc="upper left", fontsize=8,
                facecolor=COLORS["bg"], edgecolor="none", labelcolor=COLORS["text"])

    ax_k.set_facecolor(COLORS["bg"])
    ax_k.set_ylabel("价格", color=COLORS["text"], fontsize=10)
    ax_k.tick_params(axis="x", colors="none")
    ax_k.tick_params(axis="y", colors=COLORS["subtext"], labelsize=8)
    ax_k.grid(True, color=COLORS["grid"], linestyle="-", linewidth=0.4, alpha=0.5)
    ax_k.spines["top"].set_visible(False)
    ax_k.spines["right"].set_visible(False)
    ax_k.spines["bottom"].set_color("none")
    ax_k.spines["left"].set_color(COLORS["grid"])
    ax_k.set_title(f"{stock_data['name']} ({stock_data['code']})  日线K线图", 
                   color=COLORS["text"], fontsize=13, fontweight="bold", pad=8)

    # 成交量
    vols = [d["volume"] for d in daily]
    bar_colors = [
        COLORS["volume_up"] if closes[i] >= opens[i] else COLORS["volume_down"]
        for i in range(len(daily))
    ]
    ax_vol.bar(x, vols, color=bar_colors, width=0.7)
    ax_vol.set_facecolor(COLORS["bg"])
    ax_vol.set_ylabel("成交量", color=COLORS["subtext"], fontsize=8)
    ax_vol.tick_params(axis="both", colors=COLORS["subtext"], labelsize=7)
    ax_vol.grid(True, color=COLORS["grid"], linestyle="-", linewidth=0.3, alpha=0.4)
    ax_vol.spines["top"].set_visible(False)
    ax_vol.spines["right"].set_visible(False)
    ax_vol.spines["bottom"].set_color(COLORS["grid"])
    ax_vol.spines["left"].set_color(COLORS["grid"])

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=COLORS["bg"], edgecolor="none")
    buf.seek(0)
    plt.close(fig)

    if output_path:
        with open(output_path, "wb") as f:
            f.write(buf.read())
        buf.seek(0)

    return buf


# ─────────────────────────────────────────────
# 主函数: 生成单只股票的两张图
# ─────────────────────────────────────────────
def generate_charts(stock_data, out_dir=None):
    """
    生成分时图 + 日线图，返回 BytesIO buffers。
    """
    os.makedirs(out_dir or ".", exist_ok=True)
    name = stock_data["code"]

    buf_min = plot_minute(stock_data,
        output_path=os.path.join(out_dir, f"{name}_minute.png") if out_dir else None)
    buf_daily = plot_daily(stock_data,
        output_path=os.path.join(out_dir, f"{name}_daily.png") if out_dir else None)

    return buf_min, buf_daily


if __name__ == "__main__":
    import json
    with open("fetch_result.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    for stock in data:
        bufs = generate_charts(stock, out_dir="charts")
        print(f"[生成完毕] {stock['name']}")
