#!/usr/bin/env bash
set -euo pipefail

GEO="${GOOGLE_TRENDS_GEO:-US}"
LIMIT="${GOOGLE_TRENDS_LIMIT:-20}"
FORMAT="${GOOGLE_TRENDS_FORMAT:-table}"

usage() {
  cat <<'EOF'
Usage:
  fetch-hot-trends.sh [--geo US] [--limit 20] [--format table|markdown|json]

Examples:
  fetch-hot-trends.sh --geo US --limit 20 --format json
  fetch-hot-trends.sh --geo GB --limit 10 --format markdown
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --geo)
      GEO="${2:-}"
      shift 2
      ;;
    --limit)
      LIMIT="${2:-}"
      shift 2
      ;;
    --format)
      FORMAT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$GEO" ]]; then
  GEO="US"
fi

if ! [[ "$LIMIT" =~ ^[0-9]+$ ]]; then
  echo "--limit must be a positive integer" >&2
  exit 1
fi

case "$FORMAT" in
  table|markdown|json) ;;
  *)
    echo "--format must be table, markdown, or json" >&2
    exit 1
    ;;
esac

URL="https://trends.google.com/trending/rss?geo=${GEO}"
TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

curl -fsSL "$URL" -o "$TMP_FILE"

python3 - "$TMP_FILE" "$GEO" "$LIMIT" "$FORMAT" "$URL" <<'PY'
import datetime as dt
import html
import json
import sys
import xml.etree.ElementTree as ET

path, geo, limit_raw, output_format, source_url = sys.argv[1:6]
limit = int(limit_raw)


def local_name(tag):
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def child_text(node, wanted):
    for child in node.iter():
        if local_name(child.tag) == wanted and child.text:
            return html.unescape(child.text.strip())
    return ""


def all_child_text(node, wanted):
    values = []
    for child in node.iter():
        if local_name(child.tag) == wanted and child.text:
            value = html.unescape(child.text.strip())
            if value and value not in values:
                values.append(value)
    return values


tree = ET.parse(path)
root = tree.getroot()
items = [node for node in root.iter() if local_name(node.tag) == "item"]

records = []
for rank, item in enumerate(items[:limit], start=1):
    records.append(
        {
            "rank": rank,
            "geo": geo,
            "title": child_text(item, "title"),
            "approx_traffic": child_text(item, "approx_traffic"),
            "pub_date": child_text(item, "pubDate"),
            "link": child_text(item, "link") or source_url,
            "picture": child_text(item, "picture"),
            "news_titles": all_child_text(item, "news_item_title")[:3],
            "source_url": source_url,
        }
    )

today = dt.datetime.now().strftime("%Y-%m-%d")

if output_format == "json":
    print(json.dumps({"geo": geo, "date": today, "source_url": source_url, "items": records}, ensure_ascii=False, indent=2))
elif output_format == "markdown":
    print(f"# Google Trends Hot Radar - {geo} - {today}")
    print()
    print(f"Source: {source_url}")
    print()
    print("| Rank | Hot term | Approx traffic | Published | News sample |")
    print("|---:|---|---|---|---|")
    for record in records:
        title = record["title"].replace("|", "\\|")
        traffic = record["approx_traffic"].replace("|", "\\|") or "-"
        pub_date = record["pub_date"].replace("|", "\\|") or "-"
        news = " / ".join(record["news_titles"]).replace("|", "\\|") or "-"
        print(f"| {record['rank']} | {title} | {traffic} | {pub_date} | {news} |")
else:
    print(f"Google Trends Hot Radar - {geo} - {today}")
    print(f"Source: {source_url}")
    print("=" * 72)
    for record in records:
        traffic = f" [{record['approx_traffic']}]" if record["approx_traffic"] else ""
        print(f"{record['rank']:>2}. {record['title']}{traffic}")
        if record["pub_date"]:
            print(f"    Published: {record['pub_date']}")
        if record["news_titles"]:
            print("    News: " + " / ".join(record["news_titles"]))
PY
