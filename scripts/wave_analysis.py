#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
艾略特五浪理论分析
基于日线数据自动识别波浪结构并输出操作策略

核心逻辑:
  1. 从日线数据中找到局部极值（峰/谷）
  2. 标注第1~5浪（趋势浪 + 调整浪）
  3. 计算斐波那契回撤比率（23.6%, 38.2%, 50%, 61.8%, 78.6%）
  4. 结合量价关系判断当前所处浪位
  5. 输出文字策略报告
"""

import sys
import json
from datetime import datetime

# ─────────────────────────────────────────────
# 极值检测（简单高低点算法）
# ─────────────────────────────────────────────
def find_peaks_and_troughs(prices, sensitivity=2):
    """
    找到局部极值点（峰=高点, 谷=低点）
    sensitivity: 窗口大小，越大越不敏感
    """
    n = len(prices)
    peaks   = []   # index of peaks (local max)
    troughs = []   # index of troughs (local min)

    for i in range(sensitivity, n - sensitivity):
        window = prices[i - sensitivity:i + sensitivity + 1]
        if prices[i] == max(window):
            peaks.append(i)
        if prices[i] == min(window):
            troughs.append(i)
    return peaks, troughs


# ─────────────────────────────────────────────
# 波浪标注
# ─────────────────────────────────────────────
def label_waves(daily, max_waves=5):
    """
    简化波浪标注逻辑：
    假设趋势向上:
      - 浪1: 第1个谷 → 第1个峰
      - 浪2: 第1个峰 → 第2个谷（回调，不破浪1起点）
      - 浪3: 第2个谷 → 第2个峰（最长驱动浪）
      - 浪4: 第2个峰 → 第3个谷（横向整理）
      - 浪5: 第3个谷 → 第3个峰（延长浪或衰竭）

    返回: list of {wave, type, start_idx, end_idx, start_price, end_price, change_pct}
    """
    prices = [d["close"] for d in daily]
    dates  = [d["date"]  for d in daily]
    highs  = [d["high"]  for d in daily]
    lows   = [d["low"]   for d in daily]

    peaks, troughs = find_peaks_and_troughs(prices, sensitivity=3)

    if len(peaks) < 2 or len(troughs) < 2:
        return {"status": "insufficient_data", "waves": [], "current_phase": "数据不足"}

    # 合并排序
    extrema = sorted([(i, "peak") for i in peaks] + [(i, "trough") for i in troughs],
                     key=lambda x: x[0])

    # 找起始谷（最低谷之后开始）
    all_prices = [p for p, _ in extrema]
    start_idx = min(all_prices) if all_prices else 0
    extrema = [(i, t) for i, t in extrema if i >= start_idx][:max_waves * 2 + 2]

    waves = []
    for j in range(0, len(extrema) - 1, 2):
        if j + 1 >= len(extrema):
            break
        s_i, s_t = extrema[j]
        e_i, e_t = extrema[j + 1]
        # 方向：谷→峰 = 驱动浪，峰→谷 = 调整浪
        wave_num  = j // 2 + 1
        wave_type = "驱动浪" if s_t == "trough" else "调整浪"
        start_p   = lows[s_i] if s_t == "trough" else highs[s_i]
        end_p     = highs[e_i] if e_t == "peak" else lows[e_i]
        chg       = (end_p - start_p) / start_p * 100 if start_p else 0
        waves.append({
            "wave":       wave_num,
            "type":       wave_type,
            "start_idx":  s_i,
            "end_idx":    e_i,
            "start_date": dates[s_i],
            "end_date":   dates[e_i],
            "start_price":start_p,
            "end_price":  end_p,
            "change_pct": round(chg, 2),
        })

    # 判断当前所处浪
    current = waves[-1] if waves else {}
    last_price = prices[-1]
    last_idx   = len(prices) - 1

    if current:
        wave_n = current["wave"]
        wave_t = current["type"]
        if wave_t == "驱动浪":
            if last_price > current["end_price"] * 0.95:
                phase = f"第{wave_n}浪进行中（{wave_t}，尚未确认结束）"
            else:
                phase = f"第{wave_n}浪已完成，进入调整"
        else:
            phase = f"第{wave_n}浪调整中（{wave_t}）"
    else:
        phase = "无法判断当前波浪位置"

    return {
        "status":       "ok",
        "waves":        waves,
        "current_phase": phase,
        "last_date":    dates[-1],
        "last_price":   last_price,
        "latest_high":  max(highs[-20:]),
        "latest_low":   min(lows[-20:]),
    }


# ─────────────────────────────────────────────
# 斐波那契回撤
# ─────────────────────────────────────────────
def fibonacci_retracements(waves):
    """
    基于已识别波浪计算斐波那契回撤位
    """
    if len(waves) < 3:
        return []

    # 取浪1的起点-终点作为基准
    wave1 = waves[0]
    w1_start = wave1["start_price"]
    w1_end   = wave1["end_price"]
    trend    = w1_end - w1_start

    levels = {
        "23.6%": round(w1_end - trend * 0.236, 3),
        "38.2%": round(w1_end - trend * 0.382, 3),
        "50.0%": round(w1_end - trend * 0.500, 3),
        "61.8%": round(w1_end - trend * 0.618, 3),
        "78.6%": round(w1_end - trend * 0.786, 3),
    }
    return levels


# ─────────────────────────────────────────────
# 操作策略
# ─────────────────────────────────────────────
def generate_strategy(analysis, stock_info):
    """
    根据波浪分析结果 + 最新行情生成操作策略
    """
    name   = stock_info["name"]
    code   = stock_info["code"]
    last_p = analysis.get("last_price", 0)
    phase  = analysis.get("current_phase", "未知")
    waves  = analysis.get("waves", [])
    fib    = fibonacci_retracements(waves)

    # 简单策略逻辑
    strategies = []

    if "浪进行中" in phase or "浪已完成" in phase:
        strategies.append({
            "action": "观望",
            "signal": "neutral",
            "reason": f"当前{phase}，等待明确信号"
        })
        if len(waves) >= 3:
            w3 = waves[2] if len(waves) > 2 else {}
            if w3:
                strategies.append({
                    "action": "关注买点",
                    "signal": "buy",
                    "reason": f"第3浪（最强势）已走完，回调至斐波那契支撑区间可考虑介入"
                })
    elif "调整" in phase:
        strategies.append({
            "action": "关注买点",
            "signal": "buy",
            "reason": f"调整浪中，注意50%-61.8%斐波回撤区间支撑"
        })

    # 加入斐波支撑
    if fib:
        s_fib = " | ".join([f"{k}: {v}" for k, v in fib.items()])
    else:
        s_fib = "数据不足"

    report = f"""
╔══════════════════════════════════════════════╗
  {name}（{code}）波浪分析报告
  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
╠══════════════════════════════════════════════╣
  最新价:  {last_p}
  当前浪:  {phase}
╠══════════════════════════════════════════════╣
  斐波那契回撤位（基于浪1）:
  {s_fib}
╠══════════════════════════════════════════════╣
  操作策略:
"""
    for st in strategies:
        emoji = {"buy": "🟢", "sell": "🔴", "neutral": "🟡"}.get(st["signal"], "⚪")
        report += f"\n  {emoji} {st['action']}: {st['reason']}"

    report += "\n╚══════════════════════════════════════════════╝"
    return report, strategies


# ─────────────────────────────────────────────
# 主函数
# ─────────────────────────────────────────────
def analyze(stock_data):
    """
    主分析入口
    stock_data: fetch_stock.py 返回的单只股票数据字典
    """
    daily = stock_data.get("daily", [])
    if not daily:
        return {"error": "无日线数据"}

    analysis = label_waves(daily)
    report, strategies = generate_strategy(analysis, stock_data)

    return {
        "stock":    stock_data,
        "analysis": analysis,
        "fib":      fibonacci_retracements(analysis.get("waves", [])),
        "strategies": strategies,
        "report":   report,
    }


if __name__ == "__main__":
    # 测试模式：读取 fetch_result.json
    import os
    test_file = "fetch_result.json"
    if os.path.exists(test_file):
        with open(test_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for stock in data:
            result = analyze(stock)
            print(result["report"])
            print()
    else:
        print(f"[请先运行 fetch_stock.py 生成 {test_file}]")
