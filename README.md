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

# Google Trends Skills

Two Codex/OpenClaw skills for Google Trends workflows:

- `google-trends-hot-radar`: discover product, content, and market opportunities from Google Trends hot/trending terms.
- `google-trends-keyword-watch`: monitor known keywords, brands, competitors, categories, and accessory terms over time.

这套技能把 Google Trends 拆成两个清晰任务：

- **热门词雷达**：从外向内找机会，看今天/最近哪些热词可能代表新品类、新内容、新市场机会。
- **关键词曲线监控**：从内向外验证趋势，看固定关键词、品牌词、竞品词、配件词是否上涨、下滑、异常波动或需要复核。

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

It uses Google Trends RSS / Trending Now style data. It should not be used to validate whether a fixed product category is trending.

Example:

```bash
google-trends-hot-radar/scripts/fetch-hot-trends.sh --geo US --limit 20 --format markdown
```

## Skill 2: Keyword Watch

Use `google-trends-keyword-watch` when the task is:

- monitoring specific keywords over time
- comparing brand, competitor, category, or accessory terms
- checking curve changes, anomalies, seasonality, and continuity
- generating Google Trends subscription and Google Alerts setup links

The script tries to fetch Google Trends Explore interest-over-time data automatically. If Google blocks or rate-limits the request, it falls back to `manual_review_required` with a Google Trends Explore link. It also outputs Google Trends subscription and Google Alerts setup links as auxiliary reminder layers.

Example:

```bash
google-trends-keyword-watch/scripts/keyword-watch.py \
  --geo US \
  --time "today 12-m" \
  --keywords "smart glasses" "AI glasses" "Ray-Ban Meta" "Xreal Air" "Ray-Ban Meta accessories" \
  --format markdown
```

## Important Boundaries

- Google Trends values are relative 0-100 interest scores, not absolute search volume.
- Google Trends RSS is for hot/trending term discovery, not fixed keyword curve monitoring.
- Google Trends Explore automation uses non-public endpoints and may fail with rate limits.
- Google Trends subscriptions and Google Alerts are auxiliary reminder layers, not curve data sources.
- Google Alerts reflects web/news/content updates, not search-interest growth.

## Repository Structure

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

## Validation

```bash
python3 scripts/quick_validate.py .
bash -n google-trends-hot-radar/scripts/fetch-hot-trends.sh
PYTHONPYCACHEPREFIX=/tmp/google-trends-pycache python3 -m py_compile google-trends-keyword-watch/scripts/keyword-watch.py
```

## License

MIT. See [LICENSE.md](LICENSE.md).
