#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信群机器人推送
完全免费，无条数限制，支持文字/图片/Markdown

使用方法：
  python push_wechat.py <WEBHOOK_URL> <标题> <内容>
  python push_wechat.py <WEBHOOK_URL> image <图片路径>
  # 环境变量方式（推荐）：
  #   set WECOM_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
  #   python push_wechat.py
"""

import urllib.request
import json
import os
import sys
import hashlib
import base64

# ─────────────────────────────────────────────
# 推送文本消息
# ─────────────────────────────────────────────
def push_text(webhook_url, content):
    """
    发送文本消息到企业微信群
    content: str, 消息内容（支持 @成员，但需指定 userid）
    """
    data = {
        "msgtype": "text",
        "text": {
            "content": content,
            # "mentioned_list": ["userid1", "userid2"],  # 可选，@指定成员
        }
    }
    _send(webhook_url, data)


def push_markdown(webhook_url, content):
    """
    发送 Markdown 消息到企业微信群
    content: Markdown 格式字符串
    支持的 Markdown：标题、加粗、链接、列表、引用、代码块（需在企业微信后台开启机器人支持）
    """
    data = {
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    }
    _send(webhook_url, data)


def push_image(webhook_url, image_path):
    """
    发送图片到企业微信群
    图片需 < 2MB，支持 jpg/png/gif
    """
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    # 企业微信要求图片 md5 校验
    md5_hash = hashlib.md5(img_bytes).hexdigest()
    b64_str  = base64.b64encode(img_bytes).decode("utf-8")

    data = {
        "msgtype": "image",
        "image": {
            "base64": b64_str,
            "md5":    md5_hash
        }
    }
    _send(webhook_url, data)


def push_news_card(webhook_url, title, desc, url, picurl=""):
    """
    发送图文消息卡片（包含可点击链接）
    """
    articles = [{
        "title":       title,
        "description": desc,
        "url":         url,
        "picurl":      picurl,
    }]
    data = {
        "msgtype": "news",
        "news": {"articles": articles}
    }
    _send(webhook_url, data)


# ─────────────────────────────────────────────
# 内部方法
# ─────────────────────────────────────────────
def _send(webhook_url, data):
    """发送请求到企业微信 webhook"""
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            errcode = result.get("errcode", 0)
            if errcode == 0:
                print("✅ 推送成功")
            else:
                print(f"❌ 推送失败: errcode={errcode}, errmsg={result.get('errmsg','未知错误')}")
                sys.exit(1)
            return result
    except Exception as e:
        print(f"❌ 网络错误: {e}")
        sys.exit(1)


def _get_webhook():
    """从环境变量或命令行参数获取 webhook URL"""
    url = os.environ.get("WECOM_WEBHOOK", "")
    if url:
        return url
    if len(sys.argv) >= 2:
        return sys.argv[1]
    print("❌ 请提供 Webhook URL：")
    print("   python push_wechat.py <WEBHOOK_URL> <标题> <内容>")
    print("   或设置环境变量 WECOM_WEBHOOK")
    sys.exit(1)


# ─────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    webhook = _get_webhook()
    mode    = sys.argv[2].lower() if len(sys.argv) > 2 else "text"

    if mode == "image":
        image_path = sys.argv[3] if len(sys.argv) > 3 else "dashboard.png"
        print(f"[图片模式] {image_path}")
        push_image(webhook, image_path)

    elif mode == "markdown":
        content = sys.argv[3] if len(sys.argv) > 3 else ""
        push_markdown(webhook, content)

    elif mode == "news":
        title = sys.argv[3] if len(sys.argv) > 3 else "股票仪表盘"
        desc  = sys.argv[4] if len(sys.argv) > 4 else ""
        url   = sys.argv[5] if len(sys.argv) > 5 else ""
        push_news_card(webhook, title, desc, url)

    else:
        title   = sys.argv[2] if len(sys.argv) > 2 else "📊 股票驾驶舱"
        content = sys.argv[3] if len(sys.argv) > 3 else ""
        # 合并标题+内容
        full = f"{title}\n\n{content}"
        push_text(webhook, full)
