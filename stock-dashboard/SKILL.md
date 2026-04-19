---
name: stock-dashboard
description: A股/港股实时监控驾驶舱技能。每日 9:30~16:10 交易时段每小时自动推送：分时图 + 日线K线图 + 同花顺资讯摘要 + 艾略特五浪理论分析 + 操作策略，以商业蓝色仪表盘图片推送到微信（PushPlus）。覆盖股票：603986（兆易创新）、1888.HK（中国铁建）、688146（诺唯赞）。当用户提到股票监控、股票报告、每日股票推送、五浪分析、股票驾驶舱时触发此技能。
---

# 📊 股票监控驾驶舱 (stock-dashboard)

## 功能概述

每个交易小时（9:30~16:10）自动生成并推送包含以下内容的仪表盘报告：
- **分时图** — 当天实时走势 + 均价线 + 成交量柱
- **日线K线图** — 近60日K线 + MA5/MA10/MA20 均线 + 成交量
- **资讯摘要** — 同花顺最新资讯（每只股票5条，AI摘要）
- **五浪分析** — 艾略特波浪自动识别 + 斐波那契回撤位 + 操作策略
- **推送微信** — 通过 **企业微信群机器人** 推送到群聊，完全免费，无条数限制，支持图片

## 股票标的

| 代码 | 名称 | 市场 |
|------|------|------|
| 603986 | 兆易创新 | 上证 A 股 |
| 1888 | 中国铁建 | 港交所 |
| 688146 | 诺唯赞 | 科创板 |

> 如需更换股票，修改 `scripts/fetch_stock.py` 中的 `STOCKS` 列表。

## 目录结构

```
stock-dashboard/
├── SKILL.md
├── scripts/
│   ├── fetch_stock.py        # 数据抓取（同花顺网页API）
│   ├── generate_chart.py     # 分时图 + 日线K线图生成
│   ├── wave_analysis.py      # 五浪理论分析 + 操作策略
│   ├── render_dashboard.py   # 仪表盘渲染（HTML→PNG）
│   └── push_pushplus.py      # PushPlus 微信推送
├── assets/
│   └── dashboard.html        # 蓝色商业仪表盘 HTML 模板
└── .github/workflows/
    └── stock_report.yml      # GitHub Actions 云端定时任务
```

## 工作流

### 本地运行

```bash
# 1. 安装依赖
pip install requests matplotlib pillow jinja2 weasyprint

# 2. 抓取数据
python scripts/fetch_stock.py > fetch_result.json

# 3. 五浪分析
python scripts/wave_analysis.py

# 4. 渲染仪表盘（生成 PNG）
python scripts/render_dashboard.py --input fetch_result.json --png dashboard.png

# 5. 推送到微信（企业微信群机器人）
python scripts/push_wechat.py <WEBHOOK_URL> image dashboard.png
python scripts/push_wechat.py <WEBHOOK_URL> markdown "### 📊 股票驾驶舱\n> 报告内容摘要"
```

### GitHub Actions 云端运行

1. 创建 GitHub 仓库，上传本技能全部文件
2. 在 GitHub 仓库 Settings → Secrets 添加：
   - `WECOM_WEBHOOK` — 企业微信群机器人 Webhook URL
3. Actions 会自动在每个交易日 9:25、10:25 ... 16:05 (UTC+8) 触发
4. 也可在 GitHub Actions 页面手动 `workflow_dispatch` 测试

## OpenClaw Cron 定时任务配置

```json
{
  "name": "股票驾驶舱",
  "schedule": {
    "kind": "cron",
    "expr": "5 1-8 * * 1-5",
    "tz": "Asia/Shanghai"
  },
  "payload": {
    "kind": "agentTurn",
    "message": "直接输出以下提醒内容，禁止调用message工具：【📊 股票驾驶舱】触发，请运行 stock-dashboard 技能生成仪表盘并推送微信。"
  },
  "sessionTarget": "isolated",
  "enabled": true
}
```

> Cron 表达式 `5 1-8 * * 1-5` 表示：周一至周五 UTC 1:05~8:05（即北京时间 9:05~16:05），每小时第5分钟触发。

## 脚本说明

### fetch_stock.py
- 同花顺网页数据抓取（无需 API Key）
- A股：`sh` 市场代码；港股：`hk` 市场代码
- 返回 `minute`（分时）、`daily`（日线K线）、`news`（资讯列表）

### generate_chart.py
- 使用 `matplotlib` 生成图片
- 配色：深蓝背景 `#0A1628` / 上涨 `#00D4AA` / 下跌 `#FF4D6A`
- 无需显示设备（`matplotlib.use("Agg")`）
- 同时生成分时图 + 日线图，返回 BytesIO buffer

### wave_analysis.py
- 自动检测局部极值点 → 标注第1~5浪
- 计算斐波那契回撤位（23.6% / 38.2% / 50% / 61.8% / 78.6%）
- 结合量价关系生成买入/卖出/观望策略

### render_dashboard.py
- 将多只股票数据渲染为一张 HTML 仪表盘
- 支持 `--png` 输出 PNG 图片（需要 weasyprint）
- 支持 `--html` 输出独立 HTML 文件

### push_wechat.py
- 企业微信群机器人 API 调用
- 支持文本/Markdown/图片/图文卡片等多种消息类型
- Webhook URL 从环境变量 `WECOM_WEBHOOK` 或命令行参数读取

## 数据来源

| 数据 | 来源 | 备注 |
|------|------|------|
| 分时数据 | 同花顺 `d.10jqka.com.cn` | 无需登录 |
| 日线数据 | 同花顺 `d.10jqka.com.cn` | 无需登录 |
| 资讯数据 | 同花顺 `news.10jqka.com.cn` | 无需登录 |

> 同花顺接口可能变动，如抓取失败请检查接口 URL 或切换备用数据源（如 Yahoo Finance、AkShare 等）。

## 常见问题

**Q: 港股 1888 没有数据？**
A: 同花顺港股接口格式略有不同，`fetch_stock.py` 中 `STOCKS` 列表已配置 `market: "hk"`，可正常获取。若返回空，检查 `fetch_minute_data` 中的 `market_map` 配置。

**Q: 企业微信机器人怎么创建？**
A: ① 打开企业微信，创建一个仅自己的群；② 点右上角「···」→「添加群机器人」→ 创建机器人；③ 复制 Webhook URL；④ 将 URL 添加到 GitHub Secrets（字段名：`WECOM_WEBHOOK`）。

**Q: 推送失败？**
A: 检查：① Webhook URL 是否正确（需包含 `key=` 参数）；② 图片是否 < 2MB；③ 网络能否访问 `qyapi.weixin.qq.com`；④ 群机器人是否未被删除。

**Q: 图表没有生成？**
A: 确保 `matplotlib` 已安装且 `import matplotlib.use("Agg")` 可用。在无显示环境（服务器/CI）下必须设置 Agg 后端。
