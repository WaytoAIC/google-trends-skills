---
name: google-trends-keyword-watch
version: 1.1.0
description: "Use when the user wants to monitor specific Google Trends keywords, brands, competitors, categories, ASIN-adjacent demand terms, or accessory terms over time. Tracks known keywords with Explore-style interest-over-time logic, saves snapshots, compares changes, falls back to manual review links when automated curve fetching fails, and provides Google Trends subscription plus Google Alerts setup links as auxiliary reminder layers."
license: MIT
tags:
  - google-trends
  - keyword-monitoring
  - brand-watch
  - competitor-watch
  - ecommerce
metadata:
  openclaw:
    emoji: "📈"
---

# Google Trends 关键词曲线监控

本 skill 只解决一类任务：监控已知关键词、品牌词、竞品词、品类词、配件词的 Google Trends 曲线变化。

它是“从内向外验证趋势”，不是从每日热门词里找机会。如果用户问“今天有哪些热搜可能有产品机会”，要改用 `google-trends-hot-radar`。

## 何时使用

使用本 skill：

- 监控特定关键词曲线
- 比较品类词、品牌词、竞品词、配件词
- 判断上涨、下滑、异常波动、季节性
- 跟踪 `smart glasses`、`AI glasses`、`Ray-Ban Meta`、`Xreal Air` 这类固定词
- 为固定关键词生成 Google Trends 订阅和 Google Alerts 设置链接
- 每日 / 每周关键词变化报告

不要使用本 skill：

- 从 Google 热搜里寻找未知新品类
- 每日热门词雷达
- 纯热点内容扫榜

这些属于 `google-trends-hot-radar`。

## 必读资源

执行时先读取同目录：

- `config.yaml`
- `skills.md`

按需读取：

- `templates/keyword_watch_task.template.yaml`
- `snapshots/keyword_watch_snapshots.jsonl`

## 工具

优先使用：

```bash
python3 scripts/keyword-watch.py --geo US --time "today 12-m" --keywords "smart glasses" "AI glasses" "Ray-Ban Meta" "Xreal Air"
```

脚本能力：

- 每组最多 5 个关键词
- `--provider auto` 会优先使用 `SERPAPI_API_KEY` / `SEARCHAPI_API_KEY`；没有 key 时检测本地 Playwright，能用就走 `playwright`，否则走真实 Chrome 单关键词监控
- Playwright provider 需要 Node 能 `import('playwright')`；不可用时不要报错阻塞，自动回落到 Chrome provider
- Chrome provider 会打开 Google Trends Explore 页面，优先截获 `widgetdata/multiline` 网络 JSON；失败时保存截图和复核链接
- Google Trends 直连 `--provider google` 只作为低频备用，不作为默认路径
- 无商业 provider 时，只做单词自身曲线监控
- 尝试自动抓 Google Trends Explore interest-over-time 数据
- Related Queries Top / Rising 只建议在 `serpapi` / `searchapi` provider 下启用
- 输出 `interest_over_time` 完整点位
- 输出 latest_value、avg_value、peak_value、trend_direction、change_vs_previous、fetch_status、source_url
- 输出 `manual_export_url`，用于自动抓取失败时人工下载 CSV 复核
- 输出 `subscription_url` 和每个关键词的 `google_alerts_url`
- 默认追加快照；自动抓取失败时也记录 `fetch_status=manual_review_required`
- 失败时输出 `fetch_status=manual_review_required` 和 Google Trends 复核链接
- 输出 `provider`、`chrome_fetch_method=network_json|screenshot_only`、`screenshot_path`，用于区分拿到结构化曲线还是仅截图留证

## 核心规则

1. 每次监控必须围绕固定关键词组，不要混入今日热搜。
2. 关键词组最多 5 个词。
3. 必须有 geo 和 time range。
4. 自动抓取失败不能编造曲线结论。
5. Google Trends 订阅和 Google Alerts 只是辅助提醒层，不替代曲线数据。
6. 报告必须区分：已自动确认、待人工复核、证据不足、订阅/Alerts 待用户设置。
7. Playwright / Chrome / Google 直连不要并发请求；多关键词输入必须按单词串行监控，数值不能做横向大小比较。
8. 多词相对强弱对比和 Related Queries 如果需要稳定输出，必须切换 provider 或人工 CSV 复核。
9. 浏览器页面如果返回 429，只能输出截图、复核链接和 `manual_review_required`，不得推断曲线。
10. Computer Use 只作为人工复核工作法，不作为自动化数据源写入脚本主流程。

## 输出要求

- 中文为主
- 表格优先
- 必须包含：曲线变化摘要、关键词对比、异常提醒、季节性/持续性判断、下一步动作
- 当用户需要长期提醒时，必须给出 Google Trends 订阅和 Google Alerts 设置入口
- 如果自动抓取失败，直接给复核链接，并写明“未自动确认曲线”

## 自检

交付前确认：

- 是否没有调用热门词 RSS 来验证固定关键词？
- 是否没有把 Google Trends 相对值写成绝对搜索量？
- 是否保存或引用了快照？
- 自动抓取失败时是否明确降级，而不是硬推断？
- 是否把 Trends 订阅 / Google Alerts 标成辅助提醒，而不是曲线数据源？
