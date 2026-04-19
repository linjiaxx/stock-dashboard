#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PushPlus 微信推送"""

import urllib.request
import urllib.parse
import json
import sys

# PushPlus Token 配置（从环境变量读取，GitHub Secrets 用）
PUSHPLUS_TOKEN = "YOUR_PUSHPLUS_TOKEN"


def push_text(token, title, content):
    """推送文本/HTML内容到微信"""
    url = "http://www.pushplus.plus/send"
    data = {
        "token": token,
        "title": title,
        "content": content,
        "type": "html"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print(result)
        return result


def push_image(token, title, image_path):
    """推送图片到微信（图片转base64嵌入HTML）"""
    import base64
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    url = "http://www.pushplus.plus/send"
    img_tag = '<img src="data:image/png;base64,' + b64 + '" style="max-width:100%;" />'
    data = {
        "token": token,
        "title": title,
        "content": img_tag,
        "type": "html"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print(result)
        return result


if __name__ == "__main__":
    token = sys.argv[1] if len(sys.argv) > 1 else PUSHPLUS_TOKEN
    title = sys.argv[2] if len(sys.argv) > 2 else "股票仪表盘"
    content = sys.argv[3] if len(sys.argv) > 3 else "<p>无内容</p>"
    push_text(token, title, content)
