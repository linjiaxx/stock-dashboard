#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同花顺网页数据抓取
抓取: 分时数据、日线K线、新闻资讯
"""

import urllib.request
import urllib.error
import json
import time
import sys

# ─────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────
STOCKS = [
    {"code": "603986", "name": "兆易创新", "market": "sh"},
    {"code": "1888",   "name": "中国铁建", "market": "hk"},
    {"code": "688146", "name": "诺唯赞",   "market": "sh"},
]

# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────
def fetch(url, headers=None, timeout=15):
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.10jqka.com.cn/",
        "Accept": "application/json, text/plain, */*",
    }
    if headers:
        default_headers.update(headers)
    req = urllib.request.Request(url, headers=default_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[fetch error] {url} → {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────
# 1. 分时数据 (同花顺 Mins K 线)
# ─────────────────────────────────────────────
def fetch_minute_data(code, market):
    """
    同花顺分时 API
    市场: 1=上证, 0=深证, 100=港股
    """
    market_map = {"sh": 1, "sz": 0, "hk": 100}
    mkt = market_map.get(market, 1)
    # 去掉前缀
    c = code.lstrip("sh").lstrip("sz").lstrip("hk").lstrip("SH").lstrip("SZ").lstrip("HK")
    url = (
        f"https://d.10jqka.com.cn/v2/line/hs_{c}/01/last20.js"
        f"?v={int(time.time())}"
    )
    raw = fetch(url)
    if not raw:
        return None
    # 同花顺返回格式: {datas: [["时间,价格,成交量", ...]]}
    data_str = raw.get("datas", [[]])[0]
    records = []
    for item in data_str:
        parts = item.split(",")
        if len(parts) >= 4:
            records.append({
                "time":  parts[0],   # "09:30"
                "price": float(parts[1]),
                "volume": float(parts[3]),
            })
    return records


# ─────────────────────────────────────────────
# 2. 日线数据 (K线)
# ─────────────────────────────────────────────
def fetch_daily_data(code, market, count=60):
    """
    同花顺日线 K 线
    """
    c = code.lstrip("sh").lstrip("sz").lstrip("SH").lstrip("SZ")
    url = (
        f"https://d.10jqka.com.cn/v2/line/hs_{c}/01/last{count}.js"
        f"?v={int(time.time())}"
    )
    raw = fetch(url)
    if not raw:
        return None
    data_str = raw.get("datas", [[]])[0]
    records = []
    for item in data_str:
        parts = item.split(",")
        if len(parts) >= 6:
            records.append({
                "date":   parts[0],    # "2026-04-16"
                "open":   float(parts[1]),
                "close":  float(parts[2]),
                "high":   float(parts[3]),
                "low":    float(parts[4]),
                "volume": float(parts[5]),
            })
    return records


# ─────────────────────────────────────────────
# 3. 当日新闻资讯
# ─────────────────────────────────────────────
def fetch_news(code):
    """
    同花顺个股资讯 API
    """
    c = code.lstrip("sh").lstrip("sz").lstrip("SH").lstrip("SZ")
    url = (
        f"https://news.10jqka.com.cn/tapp/news/push_stocks/?page=1&tag=&track=website"
        f"&pagesize=5&code=hs_{c}&type=0&_={int(time.time()*1000)}"
    )
    raw = fetch(url, timeout=20)
    if not raw:
        return []
    items = raw.get("data", {}).get("list", [])
    news = []
    for it in items[:5]:
        news.append({
            "title":   it.get("title", ""),
            "summary": it.get("summary", it.get("desc", ""))[:200],
            "time":    it.get("ctime", ""),
            "source":  it.get("media", "同花顺"),
        })
    return news


# ─────────────────────────────────────────────
# 主函数: 抓取单只股票全部数据
# ─────────────────────────────────────────────
def fetch_stock(code, name, market):
    print(f"[抓取] {name}({code}) ...")
    stock_data = {
        "code":   code,
        "name":   name,
        "market": market,
        "minute": fetch_minute_data(code, market),
        "daily":  fetch_daily_data(code, market),
        "news":   fetch_news(code),
        "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    return stock_data


def fetch_all():
    """抓取所有股票"""
    return [fetch_stock(**s) for s in STOCKS]


if __name__ == "__main__":
    result = fetch_all()
    print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
