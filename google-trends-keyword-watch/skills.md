# Google Trends 关键词曲线监控执行规则

## 1. 任务边界

本 skill 的任务是跟踪已知关键词曲线。它不负责从每日热搜里找未知机会。

正确问题：

- `smart glasses` 最近 12 个月是否上涨？
- `Ray-Ban Meta` 和 `Xreal Air` 哪个趋势更强？
- `Ray-Ban Meta accessories` 是否有可观察到的搜索兴趣？

错误问题：

- 今天 Google 热搜有什么新品机会？
- US/GB/JP 今日热搜能不能找到 AI 眼镜配件？

这类问题交给 `google-trends-hot-radar`。

## 2. 执行流程

1. 读取 `config.yaml`。
2. 对启用的 watch group 执行关键词曲线抓取。
3. 每组关键词最多 5 个，超过必须拆组。
4. 无 provider key 时，优先检测本地 Playwright；可用则用 Playwright 打开 Google Trends 页面做单关键词串行监控，否则回落到 Chrome CDP。
5. 成功抓取时输出曲线统计、完整 `interest_over_time` 点位，并保存快照。
6. Playwright/Chrome provider 优先截获 `widgetdata/multiline` 网络 JSON；如果页面返回 429 或超时，只保存截图和复核链接。
7. 多词输入会自动拆开，不能把不同词的 0-100 值做横向大小比较。
8. Related Queries 和多词相对强弱对比优先使用 `--provider serpapi` 或 `--provider searchapi`；浏览器/Google 直连下不要为了相关查询反复打接口。
9. 失败时输出 `manual_review_required`，保留 Google Trends 链接、`manual_export_url`、`screenshot_path`，并把失败状态也写入快照用于排查。
10. 同时生成 Google Trends 订阅入口和 Google Alerts 设置链接，作为辅助提醒层。
11. 报告只基于成功抓取的数据判断上涨/下滑；失败项只写“待复核”。
12. Computer Use 只用于人工复核：打开页面、处理登录/验证码、手动下载 CSV 或截图，不作为自动化曲线数据源。

推荐命令：

```bash
python3 scripts/keyword-watch.py --geo US --time "today 12-m" --keywords "smart glasses" "AI glasses" "Ray-Ban Meta" "Xreal Air" "Ray-Ban Meta accessories"
```

## 3. 字段解释

| 字段 | 说明 |
|---|---|
| latest_value | 最近一个时间点的相对热度 |
| avg_value | 时间窗口内平均相对热度 |
| peak_value | 时间窗口内峰值 |
| trend_direction | up / down / flat / unknown |
| change_vs_previous | 最近值与上一时间点差值；若有历史快照，也可用于快照对比 |
| interest_over_time | 完整曲线点位，含 time、formatted_time、values、is_partial |
| related_queries | 每个关键词的 Top / Rising 相关查询 |
| fetch_status | success / partial / manual_review_required |
| source_url | Google Trends Explore 链接 |
| manual_export_url | 自动抓取失败时用于人工 CSV 下载复核的 Explore 链接 |
| subscription_url | Google Trends 订阅入口，需要用户登录 Google 账号手动添加 |
| google_alerts_url | 单个关键词的 Google Alerts 设置链接，可选择邮件或 RSS |

## 4. 辅助提醒层

Google Trends 订阅和 Google Alerts 可以提高长期监控稳定性，但它们不是曲线数据源。

| 辅助层 | 用途 | 边界 |
|---|---|---|
| Google Trends 订阅 | 让 Google 账号按关键词/主题推送趋势变化提醒 | 需要手动登录设置；频率和内容由 Google 控制 |
| Google Alerts | 获取关键词相关新闻、网页、新品和讨论动态 | 不是搜索热度数据，只能解释“发生了什么内容变化” |

使用规则：

- 自动曲线抓取成功时，订阅/Alerts 只作为补充提醒。
- 自动曲线抓取失败时，订阅/Alerts 可作为低频兜底，但报告必须写“未自动确认曲线”。
- Google Alerts 的结果不能直接写成“热度上涨”，只能写成“内容/新闻动态增加”。

## 5. 报告模板

```markdown
# Google Trends 关键词曲线监控 - <task_name_cn> - <date>

## 一句话结论
<哪些关键词已自动确认上涨/下滑/稳定；哪些只生成了复核链接。>

## 曲线变化摘要
| 关键词 | geo | latest | avg | peak | 方向 | 变化 | fetch_status |
|---|---|---:|---:|---:|---|---:|---|

## 关键词对比
| 关键词 | 相对表现 | 业务含义 | 建议动作 |
|---|---|---|---|

## 异常提醒
| 关键词 | 异常类型 | 判断依据 | 动作 |
|---|---|---|---|

## 季节性/持续性判断
| 关键词 | 判断 | 证据 | 下一次复核 |
|---|---|---|---|

## 手动复核链接
| 主题 | 链接 | 原因 |
|---|---|---|

## 订阅与 Alerts 设置
| 关键词/入口 | 链接 | 用途 | 状态 |
|---|---|---|---|
```

## 6. 质量规则

- 自动抓取失败时，不输出 `up/down/flat`。
- 如果曲线成功但相关查询失败，标记 `partial`，不要把相关查询缺失当成曲线失败。
- 不使用热门词 RSS 作为曲线证据。
- 关键词曲线只能说明搜索兴趣，不直接等于销量、转化率或利润。
- Google Trends 订阅和 Google Alerts 必须标注为辅助提醒，不得写成曲线数据源。
- 若配件词长期低值，不等于没有需求；需要结合 Reddit VOC、Amazon 评论、SIF/卖家精灵等验证。
- 对跨境选品，Google Trends 是需求雷达，不是最终立项依据。
