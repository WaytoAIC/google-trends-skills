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

# Google Trends Skills | Google 趋势技能包

这是一组用于 Google Trends 工作流的 Codex/OpenClaw 技能，默认服务跨境电商、内容选题、品牌/竞品观察和关键词趋势监控。

This is a Codex/OpenClaw skill suite for Google Trends workflows, designed for AI commerce, content planning, brand/competitor tracking, and keyword trend monitoring.

这套技能把 Google Trends 拆成两个清晰任务：

- `google-trends-hot-radar`：**热门词雷达**。从 Google Trends 热门词 / Trending Now 中发现新品类、新内容、新市场机会。
- `google-trends-keyword-watch`：**关键词曲线监控**。监控已知关键词、品牌词、竞品词、品类词和配件词的趋势变化。

The two skills map to two different Google Trends jobs:

- `google-trends-hot-radar`: discovers product, content, and market opportunities from Google Trends hot/trending terms.
- `google-trends-keyword-watch`: monitors known keywords, brands, competitors, categories, and accessory terms over time.

## 快速安装 | Quick Install

安装两个技能到 Codex：

Install both skills into Codex:

```bash
curl -fsSL https://raw.githubusercontent.com/WaytoAIC/google-trends-skills/main/install.sh | bash
```

固定版本安装：

Version-pinned install:

```bash
curl -fsSL https://raw.githubusercontent.com/WaytoAIC/google-trends-skills/v1.0.0/install.sh | bash -s -- --ref v1.0.0
```

安装到自定义目录：

Install to a custom destination:

```bash
bash install.sh --dest /tmp/google-trends-skills-smoke
```

## 技能 1：热门词雷达 | Skill 1: Hot Radar

当任务是下面这些场景时，使用 `google-trends-hot-radar`：

- 每日 Google Trends 热门词扫描
- 多国家 / 多市场热搜监控
- 从热搜中发现新品类、内容选题、季节性需求或广告角度
- 区分真正的机会信号和新闻/娱乐/体育噪声

Use `google-trends-hot-radar` when the task is:

- daily Google Trends hot-word scanning
- cross-market trending search monitoring
- finding new product, content, seasonal, or advertising opportunities
- separating opportunity signals from noise

它使用 Google Trends RSS / Trending Now 风格的数据。它适合“从外向内找机会”，不适合拿固定品类去验证曲线。

It uses Google Trends RSS / Trending Now style data. It discovers opportunities from the outside in and should not be used to validate whether a fixed product category is trending.

示例：

Example:

```bash
google-trends-hot-radar/scripts/fetch-hot-trends.sh --geo US --limit 20 --format markdown
```

## 技能 2：关键词曲线监控 | Skill 2: Keyword Watch

当任务是下面这些场景时，使用 `google-trends-keyword-watch`：

- 监控固定关键词的趋势变化
- 对比品牌词、竞品词、品类词或配件词
- 判断曲线上涨、下滑、异常波动、季节性和持续性
- 生成 Google Trends 订阅和 Google Alerts 设置链接

Use `google-trends-keyword-watch` when the task is:

- monitoring specific keywords over time
- comparing brand, competitor, category, or accessory terms
- checking curve changes, anomalies, seasonality, and continuity
- generating Google Trends subscription and Google Alerts setup links

脚本会优先尝试自动抓取 Google Trends Explore 的 interest-over-time 曲线数据。如果被 Google 限制或拦截，会降级为 `manual_review_required`，并输出 Google Trends Explore 复核链接。同时，它会输出 Google Trends 订阅和 Google Alerts 设置链接，作为长期监控的辅助提醒层。

The script tries to fetch Google Trends Explore interest-over-time data automatically. If Google blocks or rate-limits the request, it falls back to `manual_review_required` with a Google Trends Explore link. It also outputs Google Trends subscription and Google Alerts setup links as auxiliary reminder layers.

示例：

Example:

```bash
google-trends-keyword-watch/scripts/keyword-watch.py \
  --geo US \
  --time "today 12-m" \
  --keywords "smart glasses" "AI glasses" "Ray-Ban Meta" "Xreal Air" "Ray-Ban Meta accessories" \
  --format markdown
```

## 重要边界 | Important Boundaries

- Google Trends 的数值是 0-100 的相对热度，不是绝对搜索量。
- Google Trends RSS 用于发现热门词，不用于监控固定关键词曲线。
- Google Trends Explore 自动化依赖非公开接口，可能被限流或失败。
- Google Trends 订阅和 Google Alerts 是辅助提醒层，不是曲线数据源。
- Google Alerts 反映网页 / 新闻 / 内容更新，不等于搜索热度上涨。

English:

- Google Trends values are relative 0-100 interest scores, not absolute search volume.
- Google Trends RSS is for hot/trending term discovery, not fixed keyword curve monitoring.
- Google Trends Explore automation uses non-public endpoints and may fail with rate limits.
- Google Trends subscriptions and Google Alerts are auxiliary reminder layers, not curve data sources.
- Google Alerts reflects web/news/content updates, not search-interest growth.

## 仓库结构 | Repository Structure

```text
google-trends-hot-radar/
  SKILL.md
  config.yaml
  skills.md
  scripts/fetch-hot-trends.sh
  templates/hot_radar_task.template.yaml

google-trends-keyword-watch/
  SKILL.md
  config.yaml
  skills.md
  scripts/keyword-watch.py
  templates/keyword_watch_task.template.yaml

install.sh
scripts/quick_validate.py
```

## 验证 | Validation

```bash
python3 scripts/quick_validate.py .
bash -n google-trends-hot-radar/scripts/fetch-hot-trends.sh
PYTHONPYCACHEPREFIX=/tmp/google-trends-pycache python3 -m py_compile google-trends-keyword-watch/scripts/keyword-watch.py
```

## 许可证 | License

MIT。详见 [LICENSE.md](LICENSE.md)。

MIT. See [LICENSE.md](LICENSE.md).
