---
name: google-trends-hot-radar
version: 1.1.0
description: "Use when the user wants Google Trends hot/trending keyword monitoring, general market radar, daily trending searches, new product or content opportunity discovery, or cross-market hot-word scanning. This skill discovers opportunities from trending terms outward; do not use it to validate a fixed keyword curve."
license: MIT
tags:
  - google-trends
  - trending-now
  - market-radar
  - product-research
  - content
metadata:
  openclaw:
    emoji: "📡"
---

# Google Trends 热门词雷达

本 skill 只解决一类任务：从 Google Trends Trending Now / RSS 中发现新品类、新内容、新市场机会。

它是“从外向内找机会”，不是拿一个固定品类去问“今天热搜有没有命中它”。如果用户已经给出明确关键词、品牌、竞品或配件词，要改用 `google-trends-keyword-watch`。

## 何时使用

使用本 skill：

- 今日 / 最近 Google 热门词监控
- 多国家热搜扫描
- 从热搜里找新品类、内容选题、季节性需求、消费变化
- 每日 / 每周热门词机会报告
- 判断哪些热搜是产品机会、内容机会、广告角度或噪声

不要使用本 skill：

- 监控 `smart glasses`、`Ray-Ban Meta` 这类固定词的曲线变化
- 比较多个关键词谁更强
- 判断某个具体词是否上涨、下滑、季节性

这些属于 `google-trends-keyword-watch`。

## 必读资源

执行时先读取同目录：

- `config.yaml`
- `skills.md`

按需读取：

- `templates/hot_radar_task.template.yaml`
- `archives/hot_signal_archive.md`

## 工具

优先使用：

```bash
scripts/fetch-trending-now.py --geo US --hours 48 --category all --status all --sort relevance --limit 100 --format json
```

脚本能力：

- 优先抓取新版 Google Trends Trending Now 内部数据接口
- 支持 `--geo`、`--hours 4|24|48|168`、`--category`、`--status all|active|ended`、`--sort relevance|volume|recency|title`、`--limit`、`--format json|markdown|csv`
- 输出 query、search_volume、increase_percentage、started_at、active、trend_breakdown、categories、explore_url、source
- 如果新版接口失败，自动降级到 RSS，并标记 `fetch_status=rss_limited`

兼容旧 RSS 快速抓取：

```bash
scripts/fetch-hot-trends.sh --geo US --limit 20 --format json
```

## 核心规则

1. 先跑热门词，再判断业务意义。
2. 不要用行业固定词去要求 RSS 直接命中。
3. 热搜排名不是机会排名，必须按机会评分重新排序。
4. 噪声热点要明确排除，不能强行解释成产品机会。
5. 只有能转成选品、内容、广告、Listing、FAQ 或市场观察动作的热词，才进入高价值信号表。

## 输出要求

- 中文为主
- 表格优先
- 必须包含：机会表、噪声排除表、待复核词、业务动作、归档候选
- 明确区分：产品机会、内容机会、季节性机会、广告角度、噪声热点
- 如果没有高价值信号，要直接说“今天没有值得行动的热搜机会”

## 自检

交付前确认：

- 是否把热门词雷达和关键词曲线监控分开？
- 是否没有把无关热搜硬套到固定品类？
- 是否按机会评分排序，而不是按热搜排名照搬？
- 是否说明数据来自 Google Trends Trending Now 或 RSS 降级，而不是绝对搜索量？
