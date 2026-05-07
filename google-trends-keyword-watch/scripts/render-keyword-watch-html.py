#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import html
import json
from pathlib import Path


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def trend_value(raw):
    text = str(raw).strip()
    if text == "<1":
        return 0.5
    if text in {"", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def display_value(value, original=None):
    if original == "<1":
        return "<1"
    if value is None:
        return "-"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def clean_keyword(label):
    label = label.strip()
    if ":" in label:
        return label.split(":", 1)[0].strip()
    return label


def load_manual_csv(path):
    rows = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if row and any(cell.strip() for cell in row):
                rows.append(row)
    header_index = None
    for index, row in enumerate(rows):
        first = row[0].strip().lower()
        if first in {"week", "周", "date", "日期"}:
            header_index = index
            break
    if header_index is None:
        raise ValueError("Could not find Google Trends CSV header row. Expected first column to be Week/周.")

    header = rows[header_index]
    data_rows = [row for row in rows[header_index + 1 :] if len(row) >= len(header)]
    keywords = [clean_keyword(item) for item in header[1:]]
    timeline = []
    for row in data_rows:
        values = {}
        raw_values = {}
        for idx, keyword in enumerate(keywords, start=1):
            raw = row[idx].strip() if idx < len(row) else ""
            raw_values[keyword] = raw
            values[keyword] = trend_value(raw)
        timeline.append({"date": row[0].strip(), "values": values, "raw_values": raw_values})
    return keywords, timeline


def stats_from_timeline(keywords, timeline):
    records = []
    if not timeline:
        return records
    latest_point = timeline[-1]
    previous_point = timeline[-2] if len(timeline) >= 2 else None
    for keyword in keywords:
        series = [point["values"].get(keyword) for point in timeline]
        numeric = [value for value in series if value is not None]
        latest = latest_point["values"].get(keyword)
        previous = previous_point["values"].get(keyword) if previous_point else None
        change = latest - previous if latest is not None and previous is not None else None
        avg = sum(numeric) / len(numeric) if numeric else None
        peak = max(numeric) if numeric else None
        peak_date = "-"
        if peak is not None:
            for point in timeline:
                if point["values"].get(keyword) == peak:
                    peak_date = point["date"]
                    break
        records.append(
            {
                "keyword": keyword,
                "latest_week": latest_point["date"],
                "latest_value": latest,
                "latest_raw": latest_point["raw_values"].get(keyword),
                "previous_value": previous,
                "previous_raw": previous_point["raw_values"].get(keyword) if previous_point else None,
                "change_vs_previous": change,
                "avg_value": avg,
                "peak_value": peak,
                "peak_week": peak_date,
                "direction": classify_direction(latest, previous),
            }
        )
    return records


def load_keyword_json(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    records = []
    for record in data.get("records", []):
        records.append(
            {
                "keyword": record.get("keyword"),
                "latest_week": record.get("latest_time") or "-",
                "latest_value": record.get("latest_value"),
                "latest_raw": None,
                "previous_value": None,
                "previous_raw": None,
                "change_vs_previous": record.get("change_vs_previous"),
                "avg_value": record.get("avg_value"),
                "peak_value": record.get("peak_value"),
                "peak_week": "-",
                "direction": record.get("trend_direction") or "unknown",
            }
        )
    timeline = []
    for point in data.get("interest_over_time", []):
        timeline.append(
            {
                "date": point.get("formatted_time") or point.get("time"),
                "values": point.get("values", {}),
                "raw_values": {key: display_value(value) for key, value in point.get("values", {}).items()},
            }
        )
    return {
        "records": records,
        "timeline": timeline,
        "geo": data.get("geo", "-"),
        "time_range": data.get("time_range", "-"),
        "source_label": "keyword-watch JSON",
        "source_url": data.get("source_url", ""),
    }


def classify_direction(latest, previous):
    if latest is None or previous is None:
        return "unknown"
    delta = latest - previous
    if delta >= 5:
        return "up"
    if delta <= -5:
        return "down"
    if delta > 0:
        return "low_base_up"
    if delta < 0:
        return "low_base_down"
    return "flat"


def direction_cn(direction):
    return {
        "up": "明显上行",
        "down": "明显下滑",
        "flat": "平稳",
        "low_base_up": "低基数上行",
        "low_base_down": "低基数下滑",
        "unknown": "未知",
    }.get(direction, direction or "未知")


def decision_label(record, index):
    if index == 0 and record.get("direction") in {"up", "low_base_up"}:
        return "主需求升温"
    if record.get("direction") == "up":
        return "可优先验证"
    if record.get("direction") == "low_base_up":
        return "低基数跟踪"
    if record.get("direction") == "flat":
        return "低优先级"
    if record.get("direction") == "down":
        return "谨慎"
    return "待复核"


def key_findings(records):
    if not records:
        return ["没有可用曲线数据，先完成 CSV 或 JSON 导出。"]
    primary = records[0]
    findings = []
    latest = display_value(primary.get("latest_value"), primary.get("latest_raw"))
    previous = display_value(primary.get("previous_value"), primary.get("previous_raw"))
    change = primary.get("change_vs_previous")
    change_text = display_value(change)
    findings.append(
        f"{primary['keyword']} 最新周为 {latest}，上周为 {previous}，周变化 {change_text}，判断为{direction_cn(primary.get('direction'))}。"
    )
    up_terms = [record["keyword"] for record in records[1:] if record.get("direction") in {"up", "low_base_up"}]
    if up_terms:
        findings.append("可继续拆解的商业/细分词：" + "、".join(up_terms[:4]) + "。")
    low_terms = [record["keyword"] for record in records if (record.get("latest_value") or 0) <= 1]
    if low_terms:
        findings.append("低值词不要直接判定为无需求，应结合 Related Queries、Amazon/SIF/SellerSprite 复核：" + "、".join(low_terms[:4]) + "。")
    return findings


def records_table(records):
    rows = []
    for idx, record in enumerate(records):
        change = record.get("change_vs_previous")
        change_text = "-" if change is None else ("+" if change > 0 else "") + display_value(change)
        avg = record.get("avg_value")
        rows.append(
            "<tr>"
            f"<td><strong>{esc(record.get('keyword'))}</strong></td>"
            f"<td>{esc(record.get('latest_week') or '-')}</td>"
            f"<td class=\"num\">{esc(display_value(record.get('latest_value'), record.get('latest_raw')))}</td>"
            f"<td class=\"num\">{esc(display_value(record.get('previous_value'), record.get('previous_raw')))}</td>"
            f"<td class=\"num\">{esc(change_text)}</td>"
            f"<td class=\"num\">{esc('-' if avg is None else f'{avg:.2f}')}</td>"
            f"<td class=\"num\">{esc(display_value(record.get('peak_value')))}</td>"
            f"<td>{esc(record.get('peak_week') or '-')}</td>"
            f"<td><span class=\"badge\">{esc(decision_label(record, idx))}</span></td>"
            "</tr>"
        )
    return "\n".join(rows) or "<tr><td colspan=\"9\">No records.</td></tr>"


def chart_bars(records):
    if not records:
        return "<p class=\"muted\">No chart data.</p>"
    max_value = max((record.get("latest_value") or 0 for record in records), default=1) or 1
    bars = []
    for record in records:
        value = record.get("latest_value") or 0
        width = max(2, min(100, value / max_value * 100))
        bars.append(
            f"""
            <div class="bar-row">
              <div class="bar-label">{esc(record.get('keyword'))}</div>
              <div class="bar-track"><div class="bar" style="width:{width:.1f}%"></div></div>
              <div class="bar-value">{esc(display_value(record.get('latest_value'), record.get('latest_raw')))}</div>
            </div>
            """
        )
    return "\n".join(bars)


def render_html(data, title, summary, output_path):
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records = data["records"]
    findings = key_findings(records)
    summary_html = f"<p>{esc(summary)}</p>" if summary else "".join(f"<p>{esc(item)}</p>" for item in findings)
    source_url = data.get("source_url") or ""
    source_link = f'<a href="{esc(source_url)}" target="_blank">{esc(source_url)}</a>' if source_url else "-"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>{esc(title)}</title>
  <style>
    body {{ margin:0; background:#f5f7fb; color:#172033; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; line-height:1.58; }}
    .wrap {{ width:min(1120px, calc(100vw - 32px)); margin:0 auto; }}
    header {{ background:#fff; border-bottom:1px solid #d9dee9; padding:26px 0 20px; }}
    h1 {{ margin:0 0 8px; font-size:28px; line-height:1.25; }}
    h2 {{ margin:0 0 14px; font-size:20px; }}
    p {{ margin:0 0 10px; }}
    main {{ padding:20px 0 34px; }}
    .muted {{ color:#667085; }}
    .panel, .card {{ background:#fff; border:1px solid #d9dee9; border-radius:8px; box-shadow:0 8px 20px rgba(16,24,40,.05); }}
    .panel {{ padding:18px; margin:16px 0; }}
    .cards {{ display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:14px; margin:16px 0; }}
    .card {{ padding:15px; }}
    .card span {{ display:block; color:#667085; font-size:13px; }}
    .card strong {{ display:block; margin-top:7px; font-size:24px; }}
    .verdict {{ border-left:5px solid #067647; background:linear-gradient(90deg,#ecfdf3,#fff 58%); }}
    .table-wrap {{ overflow-x:auto; border:1px solid #d9dee9; border-radius:8px; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; background:#fff; }}
    th, td {{ padding:10px 11px; border-bottom:1px solid #d9dee9; text-align:left; vertical-align:top; }}
    th {{ background:#f2f4f7; color:#344054; white-space:nowrap; }}
    tr:last-child td {{ border-bottom:0; }}
    .num {{ text-align:right; font-variant-numeric:tabular-nums; }}
    .badge {{ display:inline-block; padding:2px 8px; border-radius:999px; background:#eff6ff; color:#2563eb; font-weight:700; font-size:12px; white-space:nowrap; }}
    .bar-row {{ display:grid; grid-template-columns:220px 1fr 56px; gap:10px; align-items:center; margin:10px 0; }}
    .bar-label {{ color:#344054; font-size:13px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    .bar-track {{ height:12px; background:#eef2f7; border-radius:999px; overflow:hidden; }}
    .bar {{ height:100%; background:#4f7df3; border-radius:999px; }}
    .bar-value {{ text-align:right; font-variant-numeric:tabular-nums; color:#344054; }}
    .steps li {{ margin:7px 0; }}
    code {{ background:#eef2f7; padding:1px 5px; border-radius:4px; }}
    @media (max-width:850px) {{ .cards {{ grid-template-columns:1fr; }} .bar-row {{ grid-template-columns:1fr; gap:5px; }} .bar-value {{ text-align:left; }} }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <h1>{esc(title)}</h1>
      <p class="muted">Generated at {esc(generated_at)} · Source: {esc(data.get('source_label'))} · Geo: {esc(data.get('geo'))} · Time: {esc(data.get('time_range'))}</p>
    </div>
  </header>
  <main class="wrap">
    <section class="cards">
      <div class="card"><span>关键词数量</span><strong>{len(records)}</strong></div>
      <div class="card"><span>最新周</span><strong>{esc(records[0].get('latest_week') if records else '-')}</strong></div>
      <div class="card"><span>主词最新值</span><strong>{esc(display_value(records[0].get('latest_value'), records[0].get('latest_raw')) if records else '-')}</strong></div>
    </section>
    <section class="panel verdict">
      <h2>结论</h2>
      {summary_html}
    </section>
    <section class="panel">
      <h2>最新热度对比</h2>
      {chart_bars(records)}
    </section>
    <section class="panel">
      <h2>数据摘要</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>关键词</th><th>最新周</th><th class="num">latest</th><th class="num">上周</th><th class="num">周变化</th><th class="num">均值</th><th class="num">峰值</th><th>峰值周</th><th>判断</th></tr></thead>
          <tbody>{records_table(records)}</tbody>
        </table>
      </div>
    </section>
    <section class="panel">
      <h2>下一步</h2>
      <ol class="steps">
        <li>优先拆解上行词的 Related Queries，尤其是商业意图更强的词。</li>
        <li>把候选词接入 Amazon / SIF / SellerSprite 验证搜索、广告和类目可行性。</li>
        <li>如果是节日词，区分“已有产品收口”和“新品立项”，不要把临近节日的上涨误判为长期机会。</li>
      </ol>
    </section>
    <section class="panel">
      <h2>数据边界</h2>
      <p>Google Trends 是 0-100 相对热度，不是绝对搜索量。&lt;1 表示相对热度低于 1，不代表完全没有需求。</p>
      <p>Source URL: {source_link}</p>
      <p>Output file: {esc(output_path)}</p>
    </section>
  </main>
</body>
</html>
"""


def parse_args():
    parser = argparse.ArgumentParser(description="Render a decision-oriented HTML report for google-trends-keyword-watch.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--keyword-json", help="JSON output from scripts/keyword-watch.py --format json")
    source.add_argument("--manual-csv", help="Google Trends Interest over time CSV manually downloaded from Explore")
    parser.add_argument("--output", required=True)
    parser.add_argument("--title", default="Google Trends 关键词曲线监控报告")
    parser.add_argument("--summary", default="", help="Optional one-paragraph executive summary. If omitted, the script generates a compact summary from the data.")
    parser.add_argument("--geo", default="US")
    parser.add_argument("--time-range", default="today 12-m")
    parser.add_argument("--source-url", default="")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.keyword_json:
        data = load_keyword_json(args.keyword_json)
    else:
        keywords, timeline = load_manual_csv(args.manual_csv)
        data = {
            "records": stats_from_timeline(keywords, timeline),
            "timeline": timeline,
            "geo": args.geo,
            "time_range": args.time_range,
            "source_label": "manual Google Trends CSV",
            "source_url": args.source_url,
        }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(data, args.title, args.summary, output), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
