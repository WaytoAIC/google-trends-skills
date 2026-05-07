## 🚀 Way to AIC | 通往 AI 电商之路
---
### 🌐 官网 Website
- https://waytoaic.com
- https://www.waytoaic.com
---

### 👥 社群招募 Community
`Way to AIC 社群招募 | WaytoAIC.com`

<p align="center">
  <img src="https://github.com/user-attachments/assets/d9f8bbf4-2056-4780-975d-86c885b52bab" width="70%">
</p>

---

### 📣 公众号 WeChat Official Account
`维正 WaytoAIC`

<p align="center">
  <img src="https://github.com/user-attachments/assets/71c71a5c-e68a-4f30-9afb-f2b056619991" width="300">
</p>

---

### 🧠 知识星球 Xiaozhixing
`AI电商之路 WaytoAIC`

<p align="center">
  <img src="https://github.com/user-attachments/assets/9eccef07-0e84-45a7-a415-affcb18c928d" width="200">
  <img src="https://github.com/user-attachments/assets/4e99fbc3-1981-4fee-b113-c9821141102d" width="400">
</p>

---

### 🧩 About Way to AIC

**AIC = AI Commerce**

在 AI 重塑商业的时代，我们希望和每一个拥抱 AI 的卖家：

- 找到场景
- 定义问题
- 积累能力
- 设计系统

共同通往 AI 电商之路。

> Way to AIC 不是教学，不是工具，
> 而是一条所有电商人共同走的进化之路。

### WaytoAIC 理念 | Principles

| 中文 | English |
|---|---|
| 场景先于方法 | Context before method |
| AI 的价值来自真实业务场景，而不是技术本身。 | AI creates value through real business contexts, not through technology alone. |
| 问题先于答案 | Problem before answer |
| 定义问题，比拥有工具更重要。 | Defining the problem matters more than collecting tools. |
| 系统胜过技巧 | System over tricks |
| 技巧是术，系统才是道，决定卖家的上限。 | Tricks are tactical; systems define long-term leverage and ceiling. |
| 共创优于独行 | Co-creation over solo progress |
| 我们相信，真正的进化发生在共同探索的过程中。 | Real evolution happens through shared exploration. |

---

# Google 趋势技能包

这是一组用于 Google Trends 工作流的 Codex/OpenClaw 技能，默认服务跨境电商、内容选题、品牌/竞品观察和关键词趋势监控。

这套技能把 Google Trends 拆成两个清晰任务：

- `google-trends-hot-radar`：**热门词雷达**。抓取 Google Trends Trending Now，发现新品类、新内容、新市场机会；失败时只把 RSS 当有限兜底。
- `google-trends-keyword-watch`：**关键词曲线监控**。监控已知关键词、品牌词、竞品词、品类词和配件词的 interest-over-time 曲线与 Top/Rising 相关查询。

## 快速安装

安装两个技能到 Codex：

```bash
curl -fsSL https://raw.githubusercontent.com/WaytoAIC/google-trends-skills/main/install.sh | bash
```

固定版本安装：

```bash
curl -fsSL https://raw.githubusercontent.com/WaytoAIC/google-trends-skills/v1.0.0/install.sh | bash -s -- --ref v1.0.0
```

安装到自定义目录：

```bash
bash install.sh --dest /tmp/google-trends-skills-smoke
```

## 技能 1：热门词雷达

当任务是下面这些场景时，使用 `google-trends-hot-radar`：

- 每日 Google Trends 热门词扫描
- 多国家 / 多市场热搜监控
- 从热搜中发现新品类、内容选题、季节性需求或广告角度
- 区分真正的机会信号和新闻 / 娱乐 / 体育噪声

它优先尝试 Google Trends 新版 Trending Now 内部数据，字段覆盖趋势词、搜索量标签、增长百分比、开始时间、活跃状态、趋势细分和分类。失败时降级 RSS，并明确标记 `fetch_status=rss_limited`。它适合“从外向内找机会”，不适合拿固定品类去验证曲线。

示例：

```bash
google-trends-hot-radar/scripts/fetch-trending-now.py \
  --geo US \
  --hours 48 \
  --category all \
  --status all \
  --sort relevance \
  --limit 100 \
  --format markdown
```

## 技能 2：关键词曲线监控

当任务是下面这些场景时，使用 `google-trends-keyword-watch`：

- 监控固定关键词的趋势变化
- 对比品牌词、竞品词、品类词或配件词
- 判断曲线上涨、下滑、异常波动、季节性和持续性
- 生成 Google Trends 订阅和 Google Alerts 设置链接

脚本会优先使用已配置的 `SERPAPI_API_KEY` / `SEARCHAPI_API_KEY`；没有商业 provider 时，默认检测本地 Playwright，能用就通过 Playwright 打开 Google Trends Explore 页面，不能用则回落到内置 Chrome CDP provider。浏览器模式按单关键词串行监控，并优先截获页面里的 `widgetdata/multiline` 网络 JSON。若页面返回 429、超时或未截获曲线，会降级为 `manual_review_required`，输出 Google Trends Explore 复核链接、手动导出链接和截图路径。同时，它会输出 Google Trends 订阅和 Google Alerts 设置链接，作为长期监控的辅助提醒层。

示例：

```bash
google-trends-keyword-watch/scripts/keyword-watch.py \
  --geo US \
  --time "today 12-m" \
  --keywords "smart glasses" "AI glasses" "Ray-Ban Meta" "Xreal Air" "Ray-Ban Meta accessories" \
  --format markdown
```

需要 Top/Rising 相关查询或多关键词相对强弱对比时，优先配置 `SERPAPI_API_KEY` 或 `SEARCHAPI_API_KEY` 后再启用 `--include-related`。Playwright / Chrome / Google 直连模式只适合判断单个词自身曲线的上涨、下滑和异常。

## 可视化 HTML 报告

`google-trends-keyword-watch` 内置了关键词监控 HTML 渲染器，可以把自动 JSON 或人工下载的 Google Trends CSV 转成可浏览决策报告。报告不依赖外部前端库。

关键词监控 HTML：

```bash
python3 google-trends-keyword-watch/scripts/keyword-watch.py \
  --geo US --time "today 12-m" --keywords "mother's day" "mother's day gifts" \
  --format json --no-save > /tmp/google-trends-keyword.json

python3 google-trends-keyword-watch/scripts/render-keyword-watch-html.py \
  --keyword-json /tmp/google-trends-keyword.json \
  --output reports/keyword-watch.html \
  --title "Google Trends 关键词曲线监控"
```

热门词雷达 HTML：

```bash
python3 google-trends-hot-radar/scripts/render-hot-radar-html.py \
  --report-json /tmp/hot-radar-report.json \
  --output reports/us-hot-radar.html
```

`/tmp/hot-radar-report.json` 需要先按 `google-trends-hot-radar/templates/hot_radar_report.template.json` 整理。这个步骤必须在机会评分之后执行，避免把原始热搜排名直接当成机会排名。

人工 CSV 复核转 HTML：

```bash
python3 google-trends-keyword-watch/scripts/render-keyword-watch-html.py \
  --manual-csv ~/Downloads/multiTimeline.csv \
  --geo US \
  --time-range "today 12-m" \
  --output reports/manual-keyword-watch.html \
  --title "Google Trends 人工复核报告"
```

如果还需要把 Keyword Watch 和 Trending Now 合并成一个总览页，可以使用仓库根目录的组合 renderer：

```bash
python3 google-trends-keyword-watch/scripts/keyword-watch.py \
  --geo US --time "today 1-m" --keywords "meta glasses" \
  --format json --no-save > /tmp/google-trends-keyword.json

python3 google-trends-hot-radar/scripts/fetch-trending-now.py \
  --geo US --hours 48 --category all --status all --sort relevance \
  --limit 100 --format json > /tmp/google-trends-trending.json

python3 scripts/render-google-trends-report.py \
  --keyword-json /tmp/google-trends-keyword.json \
  --trending-json /tmp/google-trends-trending.json \
  --output reports/google-trends-enhanced-report.html
```

## 重要边界

- Google Trends 的数值是 0-100 的相对热度，不是绝对搜索量。
- Trending Now 和 Explore 自动化都依赖 Google 非公开接口或真实 Chrome 页面，属于 best-effort，可能被限流或失败。
- Keyword Watch 默认浏览器 provider 只做单关键词自身曲线监控；不同关键词各自归一化后的 0-100 数值不能直接横向比较。
- Playwright provider 是可选增强层，需要 Node 能 `import('playwright')`；不可用时 `auto` 会回落到 Chrome CDP provider。
- Computer Use 只建议用于人工复核、登录/验证码处理、手动下载 CSV 或截图，不作为自动化曲线数据源。
- Google Trends RSS 只作为热门词兜底，通常只有有限条目，不可当完整 Trending Now 趋势池。
- Google Trends 订阅和 Google Alerts 是辅助提醒层，不是曲线数据源。
- Google Alerts 反映网页 / 新闻 / 内容更新，不等于搜索热度上涨。
- 可选 `--provider serpapi|searchapi` 只在用户自己配置 API key 时使用；`--provider auto` 在没有 key 时优先使用 Playwright，否则使用 Chrome provider。

## 仓库结构

```text
google-trends-hot-radar/
  SKILL.md
  config.yaml
  skills.md
  scripts/fetch-trending-now.py
  scripts/fetch-hot-trends.sh
  scripts/render-hot-radar-html.py
  templates/hot_radar_task.template.yaml
  templates/hot_radar_report.template.json

google-trends-keyword-watch/
  SKILL.md
  config.yaml
  skills.md
  scripts/keyword-watch.py
  scripts/render-keyword-watch-html.py
  templates/keyword_watch_task.template.yaml

install.sh
scripts/quick_validate.py
scripts/render-google-trends-report.py
reports/
```

## 验证

```bash
python3 scripts/quick_validate.py .
bash -n google-trends-hot-radar/scripts/fetch-hot-trends.sh
PYTHONPYCACHEPREFIX=/tmp/google-trends-pycache python3 -m py_compile \
  google-trends-keyword-watch/scripts/keyword-watch.py \
  google-trends-keyword-watch/scripts/render-keyword-watch-html.py \
  google-trends-hot-radar/scripts/fetch-trending-now.py \
  google-trends-hot-radar/scripts/render-hot-radar-html.py \
  scripts/render-google-trends-report.py
```

## 许可证

MIT。详见 [LICENSE.md](LICENSE.md)。

---

# Google Trends Skills

This is a Codex/OpenClaw skill suite for Google Trends workflows, designed for AI commerce, content planning, brand/competitor tracking, and keyword trend monitoring.

The two skills map to two different Google Trends jobs:

- `google-trends-hot-radar`: fetches Google Trends Trending Now to discover product, content, and market opportunities, with RSS as a limited fallback.
- `google-trends-keyword-watch`: monitors known keywords, brands, competitors, categories, and accessory terms with interest-over-time and Top/Rising related queries.

## Quick Install

Install both skills into Codex:

```bash
curl -fsSL https://raw.githubusercontent.com/WaytoAIC/google-trends-skills/main/install.sh | bash
```

Version-pinned install:

```bash
curl -fsSL https://raw.githubusercontent.com/WaytoAIC/google-trends-skills/v1.0.0/install.sh | bash -s -- --ref v1.0.0
```

Install to a custom destination:

```bash
bash install.sh --dest /tmp/google-trends-skills-smoke
```

## Skill 1: Hot Radar

Use `google-trends-hot-radar` when the task is:

- daily Google Trends hot-word scanning
- cross-market trending search monitoring
- finding new product, content, seasonal, or advertising opportunities
- separating opportunity signals from noise

It first tries the newer Google Trends Trending Now internal data path, including trend term, search-volume label, increase percentage, start time, active status, breakdown, and categories. If that fails, it falls back to RSS and marks the result as `fetch_status=rss_limited`. It discovers opportunities from the outside in and should not be used to validate whether a fixed product category is trending.

Example:

```bash
google-trends-hot-radar/scripts/fetch-trending-now.py \
  --geo US \
  --hours 48 \
  --category all \
  --status all \
  --sort relevance \
  --limit 100 \
  --format markdown
```

## Skill 2: Keyword Watch

Use `google-trends-keyword-watch` when the task is:

- monitoring specific keywords over time
- comparing brand, competitor, category, or accessory terms
- checking curve changes, anomalies, seasonality, and continuity
- generating Google Trends subscription and Google Alerts setup links

The script tries to fetch complete Google Trends Explore interest-over-time points and can fetch Related Queries Top / Rising. If Google blocks, rate-limits, or returns partial widgets, it marks the output as `partial` or `manual_review_required` with Google Trends review and manual export links. It also outputs Google Trends subscription and Google Alerts setup links as auxiliary reminder layers.

Example:

```bash
google-trends-keyword-watch/scripts/keyword-watch.py \
  --geo US \
  --time "today 12-m" \
  --keywords "smart glasses" "AI glasses" "Ray-Ban Meta" "Xreal Air" "Ray-Ban Meta accessories" \
  --include-related \
  --related-limit 50 \
  --format markdown
```

## HTML Report

`google-trends-keyword-watch` now includes a standalone keyword-watch HTML renderer. It can render either automatic JSON output or a manually downloaded Google Trends CSV into a local decision report. The report uses no external frontend library.

Keyword Watch HTML:

```bash
python3 google-trends-keyword-watch/scripts/keyword-watch.py \
  --geo US --time "today 12-m" --keywords "mother's day" "mother's day gifts" \
  --format json --no-save > /tmp/google-trends-keyword.json

python3 google-trends-keyword-watch/scripts/render-keyword-watch-html.py \
  --keyword-json /tmp/google-trends-keyword.json \
  --output reports/keyword-watch.html \
  --title "Google Trends Keyword Watch"
```

Hot Radar HTML:

```bash
python3 google-trends-hot-radar/scripts/render-hot-radar-html.py \
  --report-json /tmp/hot-radar-report.json \
  --output reports/us-hot-radar.html
```

Prepare `/tmp/hot-radar-report.json` from `google-trends-hot-radar/templates/hot_radar_report.template.json` after the opportunity scoring step. Raw Trending Now rank should not be treated as opportunity rank.

Manual CSV review to HTML:

```bash
python3 google-trends-keyword-watch/scripts/render-keyword-watch-html.py \
  --manual-csv ~/Downloads/multiTimeline.csv \
  --geo US \
  --time-range "today 12-m" \
  --output reports/manual-keyword-watch.html \
  --title "Google Trends Manual Review"
```

For a combined Keyword Watch + Trending Now overview, use the root renderer:

```bash
python3 google-trends-keyword-watch/scripts/keyword-watch.py \
  --geo US --time "today 1-m" --keywords "meta glasses" \
  --include-related --related-limit 50 --format json --no-save > /tmp/google-trends-keyword.json

python3 google-trends-hot-radar/scripts/fetch-trending-now.py \
  --geo US --hours 48 --category all --status all --sort relevance \
  --limit 100 --format json > /tmp/google-trends-trending.json

python3 scripts/render-google-trends-report.py \
  --keyword-json /tmp/google-trends-keyword.json \
  --trending-json /tmp/google-trends-trending.json \
  --output reports/google-trends-enhanced-report.html
```

## Important Boundaries

- Google Trends values are relative 0-100 interest scores, not absolute search volume.
- Trending Now and Explore automation use non-public Google endpoints on a best-effort basis and may fail with rate limits.
- Google Trends RSS is only a limited hot-term fallback, not a full Trending Now pool.
- Google Trends subscriptions and Google Alerts are auxiliary reminder layers, not curve data sources.
- Google Alerts reflects web/news/content updates, not search-interest growth.
- Optional `--provider serpapi|searchapi` works only when users configure their own API keys; commercial APIs are not default dependencies.

## Repository Structure

```text
google-trends-hot-radar/
  SKILL.md
  config.yaml
  skills.md
  scripts/fetch-trending-now.py
  scripts/fetch-hot-trends.sh
  scripts/render-hot-radar-html.py
  templates/hot_radar_task.template.yaml
  templates/hot_radar_report.template.json

google-trends-keyword-watch/
  SKILL.md
  config.yaml
  skills.md
  scripts/keyword-watch.py
  scripts/render-keyword-watch-html.py
  templates/keyword_watch_task.template.yaml

install.sh
scripts/quick_validate.py
scripts/render-google-trends-report.py
reports/
```

## Validation

```bash
python3 scripts/quick_validate.py .
bash -n google-trends-hot-radar/scripts/fetch-hot-trends.sh
PYTHONPYCACHEPREFIX=/tmp/google-trends-pycache python3 -m py_compile \
  google-trends-keyword-watch/scripts/keyword-watch.py \
  google-trends-keyword-watch/scripts/render-keyword-watch-html.py \
  google-trends-hot-radar/scripts/fetch-trending-now.py \
  google-trends-hot-radar/scripts/render-hot-radar-html.py \
  scripts/render-google-trends-report.py
```

## License

MIT. See [LICENSE.md](LICENSE.md).
