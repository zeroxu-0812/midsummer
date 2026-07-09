# Walmart 飞书爬虫

飞书群聊 `@机器人` 触发 Walmart 商品搜索爬取，结果写入飞书电子表格，并在群里回复带「打开表格」按钮的卡片。

从 `about-sif` 迁出并解耦：飞书写表能力由本目录的 `feishu_client.py`（最小飞书客户端）提供，不再依赖 about-sif 的任何模块。

## 文件说明

| 文件 | 职责 |
|------|------|
| `walmart_scraper.py` | 纯爬虫：curl_cffi 模拟 Chrome 指纹抓 Walmart 搜索结果，按 `usItemId` 去重，可 `import` 调用 |
| `walmart_config.py` | 配置：从 `.env` 读飞书凭据、输出表格、爬取默认参数 |
| `feishu_client.py` | 最小飞书客户端：token 管理 + 建表/建工作表/读写区域 + 矩阵覆写 |
| `walmart_report.py` | 结果发布：rows → 飞书新工作表 + 链接卡片 |
| `walmart_bot.py` | 飞书长连接机器人：解析群消息意图 → 爬取 → 写表 → 回卡片 |

## 安装

```bash
cd walmart-scraper
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 配置

```bash
cp .env.example .env
# 编辑 .env，填入飞书应用凭据和输出表格链接
```

飞书开放平台还需：应用勾选「机器人」→ 订阅方式「使用长连接接收事件」→ 添加 `im.message.receive_v1` → 权限 `im:message.group_at_msg:readonly`、`im:message:send_as_bot` → 发布版本 + 机器人加群。

## 运行

```bash
.venv/bin/python walmart_bot.py
# 看到 "connected to wss://..." 即长连接成功
```

在群里 `@机器人` 发：

- `查 walmart mechanical keyboard`
- `walmart airpods pro 价格从低到高 2页`
- `沃尔玛 wireless mouse 评分`

可选排序：价格从低到高 / 价格从高到低 / 评分 / 最新。

## 仅用爬虫（不走飞书）

```python
from walmart_scraper import scrape_walmart
rows = scrape_walmart("mechanical keyboard", pages=2, sort="price_low")
```
