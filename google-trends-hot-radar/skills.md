# Google Trends 热门词雷达执行规则

## 1. 任务边界

本 skill 的任务是从热门词中发现机会。它不负责验证固定关键词曲线。

正确问题：

- 今天 US/GB/JP 有哪些热词可能代表新品类或消费变化？
- 哪些热词适合做内容借势？
- 哪些热词只是噪声，不能行动？

错误问题：

- `Ray-Ban Meta accessories` 最近有没有上涨？
- `AI glasses` 和 `smart glasses` 谁搜索热度更高？

这类问题交给 `google-trends-keyword-watch`。

## 2. 执行流程

1. 读取 `config.yaml`。
2. 对启用的 monitor group，优先抓新版 Trending Now；失败时降级 RSS。
3. 先列出原始热词样本，再做机会筛选。
4. 按机会评分重新排序，不按 RSS rank 直接排序。
5. 输出机会表、噪声排除表、待复核词、业务动作、归档候选。
6. 如果用户要求 HTML / 可视化页面，先把筛选结果整理成结构化 report JSON，再用 `scripts/render-hot-radar-html.py` 渲染为本地 HTML。

推荐命令：

```bash
scripts/fetch-trending-now.py --geo US --hours 48 --category all --status all --sort relevance --limit 100 --format json
```

兼容旧 RSS 命令：

```bash
scripts/fetch-hot-trends.sh --geo US --limit 20 --format json
```

HTML 可视化命令：

```bash
scripts/render-hot-radar-html.py \
  --report-json /tmp/hot-radar-report.json \
  --output reports/hot-radar.html
```

新版 Trending Now 输出字段包括 `query`、`search_volume`、`increase_percentage`、`started_at`、`active`、`trend_breakdown`、`categories`、`source`。如果降级到 RSS，只能视为 `rss_limited` 的 Top 10 样本。

`render-hot-radar-html.py` 的输入不是原始 Trending Now JSON，而是已经完成机会判断后的 report JSON。字段模板见 `templates/hot_radar_report.template.json`。这样可以避免把原始热搜排名直接伪装成机会排名。

## 3. 机会评分

| 维度 | 权重 | 判断方式 |
|---|---:|---|
| business_relevance | 30 | 是否和跨境电商、消费产品、内容选题、品牌观察有关 |
| demand_migration_potential | 25 | 热点背后是否可能迁移为真实消费需求 |
| productization_potential | 20 | 是否能形成产品、配件、套装、耗材或解决方案 |
| content_leverage | 15 | 是否适合做文章、短视频、社媒、SEO 选题 |
| noise_risk_inverse | 10 | 新闻/娱乐/政治/体育噪声越低，分越高 |

判断门槛：

- `>= 80`：高价值机会，进入报告并建议复核或行动。
- `65-79`：观察机会，进入报告但不直接行动。
- `< 65`：通常进入噪声排除表或不展示。

## 4. 输出模板

```markdown
# Google Trends 热门词雷达 - <task_name_cn> - <date>

## 一句话结论
<今天是否有值得行动的热门词机会。>

## 热门词机会表
| 优先级 | 热词 | geo | 机会类型 | 为什么可能有价值 | 分数 | 建议动作 |
|---|---|---|---|---|---:|---|

## 噪声排除表
| 热词 | geo | 排除原因 |
|---|---|---|

## 待复核词
| 热词 | 复核方向 | 复核方式 |
|---|---|---|

## 业务动作
| 动作 | 对应热词 | 负责人 | 执行方式 |
|---|---|---|---|

## 归档候选
| hot_signal_key | 原因 | 状态 |
|---|---|---|
```

## 5. 质量规则

- 不要因为某个固定品类没有出现在 Trending Now/RSS，就写“该品类没有趋势”。
- 只能写“当前热门词雷达没有发现与该品类直接相关的热搜”。
- 当 `source=rss_limited` 时，必须说明 RSS 不是完整 Trending Now 列表。
- 对热点噪声明确说不行动。
- 产品机会必须说明迁移逻辑，例如“热点事件 -> 用户需求 -> 可产品化方向”。
- 若迁移链条说不清，归为内容机会或噪声，不归为产品机会。
- HTML 页面只做结果呈现，不替代机会评分；页面中的机会卡必须来自已筛选后的机会表。
