#!/usr/bin/env python3
import argparse
import datetime as dt
import html
import json
from pathlib import Path


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def trend_rows(items):
    rows = []
    for item in items:
        breakdown = ", ".join(item.get("trend_breakdown", [])[:8])
        categories = ", ".join(category.get("name", str(category)) for category in item.get("categories", []))
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('position'))}</td>"
            f"<td><strong>{esc(item.get('query'))}</strong></td>"
            f"<td>{esc(item.get('search_volume_label') or item.get('search_volume') or '-')}</td>"
            f"<td>{esc(item.get('increase_percentage') if item.get('increase_percentage') is not None else '-')}</td>"
            f"<td>{esc(item.get('started_at') or '-')}</td>"
            f"<td>{esc(item.get('active'))}</td>"
            f"<td>{esc(categories or '-')}</td>"
            f"<td>{esc(breakdown or '-')}</td>"
            f"<td><a href=\"{esc(item.get('explore_url'))}\" target=\"_blank\">Explore</a></td>"
            "</tr>"
        )
    return "\n".join(rows) or "<tr><td colspan=\"9\">No trending data.</td></tr>"


def keyword_rows(records):
    rows = []
    for record in records:
        rows.append(
            "<tr>"
            f"<td><strong>{esc(record.get('keyword'))}</strong></td>"
            f"<td>{esc(record.get('latest_value') if record.get('latest_value') is not None else '-')}</td>"
            f"<td>{esc(record.get('avg_value') if record.get('avg_value') is not None else '-')}</td>"
            f"<td>{esc(record.get('peak_value') if record.get('peak_value') is not None else '-')}</td>"
            f"<td>{esc(record.get('trend_direction'))}</td>"
            f"<td>{esc(record.get('change_vs_previous') if record.get('change_vs_previous') is not None else '-')}</td>"
            f"<td><span class=\"badge {esc(record.get('fetch_status'))}\">{esc(record.get('fetch_status'))}</span></td>"
            "</tr>"
        )
    return "\n".join(rows) or "<tr><td colspan=\"7\">No keyword records.</td></tr>"


def related_blocks(related_queries):
    blocks = []
    for keyword, related in related_queries.items():
        top = related.get("top", [])
        rising = related.get("rising", [])
        top_rows = "".join(
            f"<tr><td>{idx}</td><td>{esc(item.get('query'))}</td><td>{esc(item.get('formatted_value') or item.get('value') or '-')}</td></tr>"
            for idx, item in enumerate(top[:50], 1)
        ) or "<tr><td colspan=\"3\">No top queries.</td></tr>"
        rising_rows = "".join(
            f"<tr><td>{idx}</td><td>{esc(item.get('query'))}</td><td>{esc(item.get('formatted_value') or item.get('value') or '-')}</td></tr>"
            for idx, item in enumerate(rising[:50], 1)
        ) or "<tr><td colspan=\"3\">No rising queries.</td></tr>"
        blocks.append(
            f"""
            <section class="related-card">
              <h3>{esc(keyword)}</h3>
              <div class="related-grid">
                <div>
                  <h4>Top Queries</h4>
                  <table><thead><tr><th>#</th><th>Query</th><th>Value</th></tr></thead><tbody>{top_rows}</tbody></table>
                </div>
                <div>
                  <h4>Rising Queries</h4>
                  <table><thead><tr><th>#</th><th>Query</th><th>Change</th></tr></thead><tbody>{rising_rows}</tbody></table>
                </div>
              </div>
            </section>
            """
        )
    return "\n".join(blocks) or "<p>No related query data.</p>"


def chart_data(keyword_data):
    points = keyword_data.get("interest_over_time", [])
    records = keyword_data.get("records", [])
    first_keyword = records[0]["keyword"] if records else None
    if not first_keyword:
        return "[]"
    values = []
    for point in points:
        value = point.get("values", {}).get(first_keyword)
        if value is not None:
            values.append({"label": point.get("formatted_time") or point.get("time"), "value": value})
    return json.dumps(values, ensure_ascii=False)


def render(keyword_data, trending_data, title):
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trend_count = len(trending_data.get("items", []))
    keyword_count = len(keyword_data.get("records", []))
    chart_json = chart_data(keyword_data)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>{esc(title)}</title>
  <style>
    body {{ margin: 0; background: #f6f8fb; color: #182033; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .wrap {{ width: min(1180px, calc(100vw - 32px)); margin: 0 auto; }}
    header {{ background: #fff; border-bottom: 1px solid #d9dee9; padding: 24px 0; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    h2 {{ margin: 0 0 14px; font-size: 20px; }}
    h3 {{ margin: 0 0 12px; font-size: 16px; }}
    h4 {{ margin: 12px 0 8px; font-size: 14px; color: #475467; }}
    .muted {{ color: #667085; }}
    .tabs {{ display: flex; gap: 8px; margin: 18px 0; }}
    button {{ border: 1px solid #cfd6e4; background: #fff; padding: 9px 14px; border-radius: 8px; cursor: pointer; }}
    button.active {{ background: #e8f4f2; border-color: #0f766e; color: #0f766e; font-weight: 700; }}
    .panel {{ background: #fff; border: 1px solid #d9dee9; border-radius: 8px; padding: 18px; margin: 16px 0; box-shadow: 0 8px 20px rgba(16,24,40,.06); }}
    .cards {{ display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 14px; margin: 16px 0; }}
    .card {{ background: #fff; border: 1px solid #d9dee9; border-radius: 8px; padding: 16px; }}
    .value {{ display: block; font-size: 28px; font-weight: 800; margin-top: 6px; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid #d9dee9; border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; background: #fff; }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid #d9dee9; text-align: left; vertical-align: top; }}
    th {{ background: #f2f4f7; color: #344054; white-space: nowrap; }}
    tr:last-child td {{ border-bottom: 0; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; background: #f2f4f7; }}
    .success {{ color: #067647; background: #ecfdf3; }}
    .partial, .rss_limited {{ color: #b45309; background: #fff7ed; }}
    .manual_review_required {{ color: #b42318; background: #fef3f2; }}
    .tab-panel {{ display: none; }}
    .tab-panel.active {{ display: block; }}
    .related-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .related-card {{ border: 1px solid #d9dee9; border-radius: 8px; padding: 14px; margin: 12px 0; }}
    svg {{ width: 100%; height: 260px; background: #fff; border: 1px solid #d9dee9; border-radius: 8px; }}
    @media (max-width: 900px) {{ .cards, .related-grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <h1>{esc(title)}</h1>
      <p class="muted">Generated at {esc(generated_at)}. Google Trends values are sampled and normalized signals, not absolute sales or search volume.</p>
    </div>
  </header>
  <main class="wrap">
    <section class="cards">
      <div class="card">keyword fetch_status<span class="value">{esc(keyword_data.get("fetch_status"))}</span></div>
      <div class="card">Keywords<span class="value">{keyword_count}</span></div>
      <div class="card">trending fetch_status<span class="value">{esc(trending_data.get("fetch_status"))}</span></div>
      <div class="card">Trending items<span class="value">{trend_count}</span></div>
    </section>

    <nav class="tabs">
      <button class="active" data-tab="monitor">监控</button>
      <button data-tab="trending">趋势</button>
      <button data-tab="diagnostics">诊断</button>
    </nav>

    <section id="monitor" class="tab-panel active">
      <div class="panel">
        <h2>关键词曲线监控</h2>
        <p class="muted">Geo: {esc(keyword_data.get("geo"))} · Time: {esc(keyword_data.get("time_range"))} · Provider: {esc(keyword_data.get("provider"))}</p>
        <svg id="chart" role="img" aria-label="interest over time chart"></svg>
      </div>
      <div class="panel table-wrap">
        <table><thead><tr><th>Keyword</th><th>Latest</th><th>Avg</th><th>Peak</th><th>Direction</th><th>Change</th><th>Status</th></tr></thead><tbody>{keyword_rows(keyword_data.get("records", []))}</tbody></table>
      </div>
      <div class="panel">
        <h2>相关查询 Top / Rising</h2>
        {related_blocks(keyword_data.get("related_queries", {}))}
      </div>
    </section>

    <section id="trending" class="tab-panel">
      <div class="panel">
        <h2>Trending Now</h2>
        <p class="muted">Geo: {esc(trending_data.get("geo"))} · Hours: {esc(trending_data.get("hours"))} · Source: {esc(trending_data.get("source"))}</p>
      </div>
      <div class="panel table-wrap">
        <table><thead><tr><th>#</th><th>Trend</th><th>Volume</th><th>Growth</th><th>Started</th><th>Active</th><th>Category</th><th>Breakdown</th><th>Link</th></tr></thead><tbody>{trend_rows(trending_data.get("items", []))}</tbody></table>
      </div>
    </section>

    <section id="diagnostics" class="tab-panel">
      <div class="panel">
        <h2>抓取状态</h2>
        <p><strong>Keyword fetch_status:</strong> {esc(keyword_data.get("fetch_status"))} · <strong>provider:</strong> {esc(keyword_data.get("provider"))}</p>
        <p><strong>Trending fetch_status:</strong> {esc(trending_data.get("fetch_status"))} · <strong>source:</strong> {esc(trending_data.get("source"))}</p>
        <p><strong>Keyword errors:</strong> {esc("; ".join(keyword_data.get("errors", [])) or keyword_data.get("error") or "-")}</p>
        <p><strong>Trending error:</strong> {esc(trending_data.get("error") or "-")}</p>
        <p><strong>Trending source_url:</strong> <a href="{esc(trending_data.get("source_url"))}" target="_blank">{esc(trending_data.get("source_url"))}</a></p>
        <p><strong>manual_export_url:</strong> <a href="{esc(keyword_data.get("manual_export_url"))}" target="_blank">{esc(keyword_data.get("manual_export_url"))}</a></p>
      </div>
    </section>
  </main>
  <script>
    const chartData = {chart_json};
    document.querySelectorAll("[data-tab]").forEach(button => {{
      button.addEventListener("click", () => {{
        document.querySelectorAll("[data-tab]").forEach(node => node.classList.remove("active"));
        document.querySelectorAll(".tab-panel").forEach(node => node.classList.remove("active"));
        button.classList.add("active");
        document.getElementById(button.dataset.tab).classList.add("active");
      }});
    }});
    function renderChart() {{
      const svg = document.getElementById("chart");
      const width = svg.clientWidth || 900;
      const height = svg.clientHeight || 260;
      svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);
      svg.innerHTML = "";
      if (!chartData.length) {{
        svg.innerHTML = `<text x="24" y="48" fill="#667085">No automatic curve data. Use manual export link in diagnostics.</text>`;
        return;
      }}
      const pad = 34;
      const max = Math.max(100, ...chartData.map(d => Number(d.value) || 0));
      const pts = chartData.map((d, i) => {{
        const x = pad + (width - pad * 2) * (i / Math.max(chartData.length - 1, 1));
        const y = height - pad - ((Number(d.value) || 0) / max) * (height - pad * 2);
        return [x, y];
      }});
      for (let i = 0; i <= 5; i++) {{
        const y = pad + (height - pad * 2) * (i / 5);
        svg.innerHTML += `<line x1="${{pad}}" y1="${{y}}" x2="${{width - pad}}" y2="${{y}}" stroke="#eef2f6"/>`;
      }}
      const d = pts.map((p, i) => `${{i ? "L" : "M"}}${{p[0]}},${{p[1]}}`).join(" ");
      svg.innerHTML += `<path d="${{d}}" fill="none" stroke="#2563eb" stroke-width="3"/>`;
    }}
    renderChart();
    window.addEventListener("resize", renderChart);
  </script>
</body>
</html>
"""


def parse_args():
    parser = argparse.ArgumentParser(description="Render a local HTML report from Google Trends skill JSON outputs.")
    parser.add_argument("--keyword-json", required=True)
    parser.add_argument("--trending-json", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--title", default="Google Trends Skills Enhanced Report")
    return parser.parse_args()


def main():
    args = parse_args()
    keyword_data = load_json(args.keyword_json)
    trending_data = load_json(args.trending_json)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(keyword_data, trending_data, args.title), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
