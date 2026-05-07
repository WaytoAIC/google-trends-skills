#!/usr/bin/env python3
import argparse
import datetime as dt
import html
import json
from pathlib import Path


TYPE_LABELS = {
    "product_opportunity": "产品机会",
    "content_opportunity": "内容机会",
    "seasonal_opportunity": "季节性机会",
    "ad_angle": "广告角度",
    "market_watch": "市场观察",
    "noise": "噪声",
}

TYPE_CLASSES = {
    "product_opportunity": "product",
    "content_opportunity": "content",
    "seasonal_opportunity": "seasonal",
    "ad_angle": "ad",
    "market_watch": "watch",
    "noise": "noise",
}


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def load_report(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def score_width(score):
    try:
        return max(0, min(100, int(score)))
    except Exception:
        return 0


def opportunity_cards(opportunities):
    if not opportunities:
        return '<div class="panel empty">暂无进入机会池的热词。</div>'
    cards = []
    for idx, item in enumerate(opportunities, 1):
        rank = item.get("rank") or idx
        types = as_list(item.get("opportunity_type") or item.get("types"))
        type_attr = " ".join(TYPE_CLASSES.get(t, "watch") for t in types) or "watch"
        type_tags = "".join(
            f'<span class="tag {esc(TYPE_CLASSES.get(t, "watch"))}">{esc(TYPE_LABELS.get(t, t))}</span>'
            for t in types
        )
        extra_tags = "".join(f'<span class="tag">{esc(tag)}</span>' for tag in as_list(item.get("tags")))
        score = item.get("score", "-")
        cards.append(
            f"""
        <article class="panel opportunity" data-type="{esc(type_attr)}">
          <div class="card-head">
            <div>
              <h3>{esc(item.get("term") or item.get("hot_term"))}</h3>
              <div class="tag-row">{type_tags}{extra_tags}</div>
            </div>
            <div class="rank">{esc(rank)}</div>
          </div>
          <p class="muted">{esc(item.get("why") or item.get("rationale") or item.get("migration_logic"))}</p>
          <div class="score-wrap">
            <div class="score">{esc(score)}</div>
            <div class="bar"><i style="width: {score_width(score)}%"></i></div>
          </div>
          <div class="action"><strong>建议动作:</strong> {esc(item.get("action") or item.get("recommended_action"))}</div>
        </article>
            """
        )
    return "\n".join(cards)


def noise_rows(items):
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('term') or item.get('hot_term'))}</td>"
            f"<td>{esc(item.get('geo') or '-')}</td>"
            f"<td>{esc(item.get('reason'))}</td>"
            "</tr>"
        )
    return "\n".join(rows) or '<tr><td colspan="3">暂无噪声排除项。</td></tr>'


def review_rows(items):
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('term') or item.get('hot_term'))}</td>"
            f"<td>{esc(item.get('review_focus') or item.get('focus'))}</td>"
            f"<td>{esc(item.get('review_method') or item.get('method'))}</td>"
            "</tr>"
        )
    return "\n".join(rows) or '<tr><td colspan="3">暂无待复核词。</td></tr>'


def action_rows(items):
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('action'))}</td>"
            f"<td>{esc(item.get('terms') or item.get('term'))}</td>"
            f"<td>{esc(item.get('owner') or '-')}</td>"
            f"<td>{esc(item.get('execution') or item.get('method'))}</td>"
            "</tr>"
        )
    return "\n".join(rows) or '<tr><td colspan="4">暂无业务动作。</td></tr>'


def archive_rows(items):
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('hot_signal_key'))}</td>"
            f"<td>{esc(item.get('reason'))}</td>"
            f"<td>{esc(item.get('status') or 'watching')}</td>"
            "</tr>"
        )
    return "\n".join(rows) or '<tr><td colspan="3">暂无归档候选。</td></tr>'


def metric_value(report, key, fallback):
    summary = report.get("summary", {})
    return summary.get(key, fallback)


def render(report):
    title = report.get("title") or "Google Trends 热门词机会雷达"
    generated_at = report.get("generated_at") or dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    opportunities = report.get("opportunities", [])
    high_value = len([item for item in opportunities if score_width(item.get("score")) >= 80])
    source_url = report.get("source_url") or "https://trends.google.com/trending"
    source_link = f'<a href="{esc(source_url)}" target="_blank">打开 Google Trends Trending Now</a>' if source_url else "-"
    raw_count = metric_value(report, "raw_count", report.get("raw_count", "-"))
    opportunity_count = metric_value(report, "opportunity_count", len(opportunities))
    archive_count = metric_value(report, "archive_candidate_count", len(report.get("archive_candidates", [])))

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>{esc(title)}</title>
  <style>
    :root {{
      --bg: #f7f8fb;
      --surface: #ffffff;
      --soft: #f1f5f4;
      --ink: #182033;
      --muted: #667085;
      --line: #d9dee9;
      --green: #0f766e;
      --blue: #2563eb;
      --amber: #b45309;
      --purple: #7c3aed;
      --red: #b42318;
      --shadow: 0 10px 24px rgba(16, 24, 40, .06);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      line-height: 1.5;
    }}
    a {{ color: var(--blue); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .wrap {{ width: min(1200px, calc(100vw - 32px)); margin: 0 auto; }}
    header {{ background: var(--surface); border-bottom: 1px solid var(--line); padding: 26px 0 20px; }}
    h1 {{ margin: 0; font-size: 30px; line-height: 1.2; letter-spacing: 0; }}
    h2 {{ margin: 0 0 14px; font-size: 20px; line-height: 1.3; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; font-size: 16px; line-height: 1.35; letter-spacing: 0; }}
    p {{ margin: 0; }}
    .muted {{ color: var(--muted); }}
    .eyebrow {{ margin: 0 0 8px; color: var(--green); font-size: 13px; font-weight: 700; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }}
    .pill {{ display: inline-flex; align-items: center; min-height: 28px; padding: 4px 10px; border: 1px solid var(--line); border-radius: 999px; background: #fff; color: #344054; font-size: 12px; white-space: nowrap; }}
    main {{ padding-bottom: 40px; }}
    section {{ margin: 18px 0; }}
    .summary {{ display: grid; grid-template-columns: 1.45fr .55fr; gap: 16px; margin: 18px 0 16px; }}
    .panel {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; box-shadow: var(--shadow); padding: 18px; }}
    .verdict {{ min-height: 138px; display: flex; flex-direction: column; justify-content: space-between; border-left: 4px solid var(--green); }}
    .verdict strong {{ display: block; margin-bottom: 8px; font-size: 22px; line-height: 1.28; }}
    .metrics {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .metric {{ min-height: 63px; padding: 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--soft); }}
    .metric span {{ display: block; color: var(--muted); font-size: 12px; }}
    .metric b {{ display: block; margin-top: 4px; font-size: 24px; line-height: 1.1; }}
    .toolbar {{ position: sticky; top: 0; z-index: 3; background: rgba(247, 248, 251, .92); backdrop-filter: blur(10px); border-bottom: 1px solid var(--line); padding: 12px 0; }}
    .controls {{ display: flex; gap: 8px; overflow-x: auto; padding-bottom: 2px; }}
    button {{ border: 1px solid #cfd6e4; background: #fff; color: #344054; min-height: 34px; padding: 7px 12px; border-radius: 8px; cursor: pointer; font: inherit; font-size: 13px; white-space: nowrap; }}
    button.active {{ background: #e8f4f2; border-color: var(--green); color: var(--green); font-weight: 700; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
    .opportunity {{ display: flex; flex-direction: column; gap: 14px; min-height: 300px; }}
    .card-head {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }}
    .rank {{ flex: 0 0 auto; width: 34px; height: 34px; display: grid; place-items: center; border-radius: 8px; background: #e8f4f2; color: var(--green); font-weight: 800; }}
    .tag-row {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .tag {{ display: inline-flex; align-items: center; min-height: 24px; padding: 2px 8px; border-radius: 999px; background: #f2f4f7; color: #344054; font-size: 12px; }}
    .tag.product {{ background: #e8f4f2; color: var(--green); }}
    .tag.content {{ background: #eff6ff; color: var(--blue); }}
    .tag.seasonal {{ background: #fff7ed; color: var(--amber); }}
    .tag.ad {{ background: #fef3f2; color: var(--red); }}
    .tag.watch {{ background: #f5f3ff; color: var(--purple); }}
    .score-wrap {{ display: grid; grid-template-columns: 44px 1fr; gap: 10px; align-items: center; }}
    .score {{ font-size: 24px; font-weight: 800; line-height: 1; }}
    .bar {{ height: 10px; border-radius: 999px; background: #edf0f5; overflow: hidden; }}
    .bar i {{ display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--green), #4f8fdf); }}
    .action {{ margin-top: auto; padding: 12px; border-radius: 8px; background: #f8fafc; border: 1px solid #e3e8ef; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; background: #fff; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 760px; font-size: 13px; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ background: #f2f4f7; color: #344054; font-weight: 700; white-space: nowrap; }}
    tr:last-child td {{ border-bottom: 0; }}
    .hidden {{ display: none; }}
    .empty {{ color: var(--muted); }}
    @media (max-width: 980px) {{ .summary, .grid {{ grid-template-columns: 1fr; }} .toolbar {{ position: static; }} }}
    @media (max-width: 560px) {{ .wrap {{ width: min(100vw - 20px, 1200px); }} header {{ padding-top: 20px; }} h1 {{ font-size: 24px; }} .metrics {{ grid-template-columns: 1fr; }} .panel {{ padding: 14px; }} .opportunity {{ min-height: auto; }} }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <p class="eyebrow">Google Trends Hot Radar</p>
      <h1>{esc(title)}</h1>
      <div class="meta">
        <span class="pill">Geo: {esc(report.get("geo") or "-")}</span>
        <span class="pill">窗口: {esc(report.get("hours") or "-")} 小时</span>
        <span class="pill">数据源: {esc(report.get("source") or "-")}</span>
        <span class="pill">抓取状态: {esc(report.get("fetch_status") or "-")}</span>
        <span class="pill">生成时间: {esc(generated_at)}</span>
      </div>
    </div>
  </header>
  <main class="wrap">
    <section class="summary">
      <div class="panel verdict">
        <div>
          <strong>{esc(report.get("summary", {}).get("verdict") or report.get("verdict") or "请先完成机会筛选。")}</strong>
          <p class="muted">{esc(report.get("summary", {}).get("detail") or report.get("detail") or "本页按机会评分重排，不按热搜排名直接排序。")}</p>
        </div>
        <p>{source_link}</p>
      </div>
      <div class="metrics">
        <div class="metric"><span>原始热词样本</span><b>{esc(raw_count)}</b></div>
        <div class="metric"><span>进入机会池</span><b>{esc(opportunity_count)}</b></div>
        <div class="metric"><span>高价值候选</span><b>{esc(metric_value(report, "high_value_count", high_value))}</b></div>
        <div class="metric"><span>归档候选</span><b>{esc(archive_count)}</b></div>
      </div>
    </section>
    <div class="toolbar">
      <div class="wrap">
        <div class="controls" aria-label="机会类型筛选">
          <button class="active" data-filter="all">全部机会</button>
          <button data-filter="product">产品机会</button>
          <button data-filter="seasonal">季节性机会</button>
          <button data-filter="content">内容机会</button>
          <button data-filter="ad">广告角度</button>
          <button data-filter="watch">市场观察</button>
        </div>
      </div>
    </div>
    <section>
      <h2>机会评分卡</h2>
      <div class="grid" id="opportunityGrid">{opportunity_cards(opportunities)}</div>
    </section>
    <section>
      <h2>噪声排除表</h2>
      <div class="table-wrap"><table><thead><tr><th>热词</th><th>geo</th><th>排除原因</th></tr></thead><tbody>{noise_rows(report.get("noise_exclusions", []))}</tbody></table></div>
    </section>
    <section>
      <h2>待复核词</h2>
      <div class="table-wrap"><table><thead><tr><th>热词</th><th>复核方向</th><th>复核方式</th></tr></thead><tbody>{review_rows(report.get("manual_review_terms", []))}</tbody></table></div>
    </section>
    <section>
      <h2>业务动作</h2>
      <div class="table-wrap"><table><thead><tr><th>动作</th><th>对应热词</th><th>负责人</th><th>执行方式</th></tr></thead><tbody>{action_rows(report.get("business_actions", []))}</tbody></table></div>
    </section>
    <section>
      <h2>归档候选</h2>
      <div class="table-wrap"><table><thead><tr><th>hot_signal_key</th><th>原因</th><th>状态</th></tr></thead><tbody>{archive_rows(report.get("archive_candidates", []))}</tbody></table></div>
    </section>
  </main>
  <script>
    const buttons = document.querySelectorAll("[data-filter]");
    const cards = document.querySelectorAll(".opportunity");
    buttons.forEach((button) => {{
      button.addEventListener("click", () => {{
        const filter = button.dataset.filter;
        buttons.forEach((node) => node.classList.remove("active"));
        button.classList.add("active");
        cards.forEach((card) => {{
          const types = card.dataset.type.split(" ");
          card.classList.toggle("hidden", filter !== "all" && !types.includes(filter));
        }});
      }});
    }});
  </script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Render a curated Google Trends hot-radar report as a standalone HTML page.")
    parser.add_argument("--report-json", required=True, help="Curated hot-radar report JSON. See templates/hot_radar_report.template.json.")
    parser.add_argument("--output", required=True, help="Output HTML path.")
    args = parser.parse_args()

    report = load_report(args.report_json)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(report), encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
