#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import statistics
import sys
import urllib.parse
import urllib.request
from pathlib import Path


EXPLORE_URL = "https://trends.google.com/trends/api/explore"
MULTILINE_URL = "https://trends.google.com/trends/api/widgetdata/multiline"
TRENDS_SUBSCRIPTION_URL = "https://trends.google.com/trends/subscriptions"
GOOGLE_ALERTS_URL = "https://www.google.com/alerts"


def build_source_url(keywords, geo, time_range):
    params = {
        "date": time_range,
        "geo": geo,
        "q": ",".join(keywords),
    }
    return "https://trends.google.com/trends/explore?" + urllib.parse.urlencode(params)


def build_google_alerts_url(keyword, hl="en"):
    params = {
        "q": keyword,
        "hl": hl,
    }
    return GOOGLE_ALERTS_URL + "?" + urllib.parse.urlencode(params)


def build_auxiliary_setup(keywords, geo, time_range, alerts_frequency):
    return {
        "google_trends_subscription": {
            "status": "manual_setup_required",
            "url": TRENDS_SUBSCRIPTION_URL,
            "purpose": "Use a Google account to subscribe to keyword or topic trend updates as a low-frequency reminder layer.",
            "recommended_geo": geo,
            "recommended_time_range": time_range,
            "recommended_frequency": "weekly",
            "setup_steps": [
                "Open the subscription URL and sign in to a Google account.",
                "Click Add subscription.",
                "Add the monitored keyword or topic.",
                "Choose the region and notification frequency.",
                "Treat notifications as reminders, not as complete trend-curve data.",
            ],
        },
        "google_alerts": {
            "status": "manual_setup_required",
            "purpose": "Track keyword-related web, news, product, and discussion updates as context around trend movement.",
            "recommended_frequency": alerts_frequency,
            "delivery_options": ["email", "rss"],
            "alerts": [
                {
                    "keyword": keyword,
                    "url": build_google_alerts_url(keyword),
                    "setup_note": "Choose frequency and delivery mode in Google Alerts. RSS is useful for automation; email is useful for manual monitoring.",
                }
                for keyword in keywords
            ],
            "limitation": "Google Alerts is not Google Trends data and must not be used as proof of search-interest growth.",
        },
    }


def http_get(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def parse_prefixed_json(text):
    text = text.strip()
    if text.startswith(")]}',"):
        text = text[5:].strip()
    return json.loads(text)


def classify_direction(latest, previous):
    if latest is None or previous is None:
        return "unknown"
    delta = latest - previous
    if delta >= 5:
        return "up"
    if delta <= -5:
        return "down"
    return "flat"


def find_previous_snapshot(snapshot_file, keyword, geo, time_range):
    if not snapshot_file.exists():
        return None
    previous = None
    try:
        with snapshot_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                if (
                    record.get("keyword") == keyword
                    and record.get("geo") == geo
                    and record.get("time_range") == time_range
                    and record.get("fetch_status") == "success"
                ):
                    previous = record
    except Exception:
        return None
    return previous


def fetch_interest_over_time(keywords, geo, time_range, category, trend_property, tz):
    explore_req = {
        "comparisonItem": [
            {"keyword": keyword, "geo": geo, "time": time_range}
            for keyword in keywords
        ],
        "category": category,
        "property": trend_property,
    }
    query = urllib.parse.urlencode(
        {
            "hl": "en-US",
            "tz": str(tz),
            "req": json.dumps(explore_req, separators=(",", ":")),
        }
    )
    explore = parse_prefixed_json(http_get(f"{EXPLORE_URL}?{query}"))
    widgets = explore.get("widgets", [])
    timeseries = None
    for widget in widgets:
        if widget.get("id") == "TIMESERIES" or "Interest over time" in widget.get("title", ""):
            timeseries = widget
            break
    if not timeseries:
        raise RuntimeError("Google Trends did not return a TIMESERIES widget")

    multiline_req = json.dumps(timeseries["request"], separators=(",", ":"))
    query = urllib.parse.urlencode(
        {
            "hl": "en-US",
            "tz": str(tz),
            "req": multiline_req,
            "token": timeseries["token"],
        }
    )
    data = parse_prefixed_json(http_get(f"{MULTILINE_URL}?{query}"))
    return data.get("default", {}).get("timelineData", [])


def summarize_keyword(keyword, idx, timeline, geo, time_range, source_url, snapshot_file):
    values = []
    latest_time = None
    for point in timeline:
        point_values = point.get("value", [])
        if idx >= len(point_values):
            continue
        value = point_values[idx]
        if isinstance(value, (int, float)):
            values.append(value)
            latest_time = point.get("formattedTime") or point.get("time")

    latest = values[-1] if values else None
    previous = values[-2] if len(values) >= 2 else None
    avg_value = round(statistics.mean(values), 2) if values else None
    peak_value = max(values) if values else None
    previous_snapshot = find_previous_snapshot(snapshot_file, keyword, geo, time_range)
    change_vs_last_snapshot = None
    if previous_snapshot and latest is not None and previous_snapshot.get("latest_value") is not None:
        change_vs_last_snapshot = latest - previous_snapshot["latest_value"]

    return {
        "keyword": keyword,
        "geo": geo,
        "time_range": time_range,
        "latest_value": latest,
        "avg_value": avg_value,
        "peak_value": peak_value,
        "trend_direction": classify_direction(latest, previous),
        "change_vs_previous": latest - previous if latest is not None and previous is not None else None,
        "change_vs_last_snapshot": change_vs_last_snapshot,
        "latest_time": latest_time,
        "fetch_status": "success",
        "source_url": source_url,
    }


def manual_review_records(keywords, geo, time_range, source_url, error):
    return [
        {
            "keyword": keyword,
            "geo": geo,
            "time_range": time_range,
            "latest_value": None,
            "avg_value": None,
            "peak_value": None,
            "trend_direction": "unknown",
            "change_vs_previous": None,
            "change_vs_last_snapshot": None,
            "latest_time": None,
            "fetch_status": "manual_review_required",
            "source_url": source_url,
            "error": str(error),
        }
        for keyword in keywords
    ]


def save_snapshots(snapshot_file, records, observed_at):
    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    with snapshot_file.open("a", encoding="utf-8") as handle:
        for record in records:
            payload = {"observed_at": observed_at, **record}
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def print_markdown(records, observed_at, auxiliary_setup):
    print(f"# Google Trends Keyword Watch - {observed_at[:10]}")
    print()
    print("| Keyword | Geo | Latest | Avg | Peak | Direction | Change vs previous | Status |")
    print("|---|---|---:|---:|---:|---|---:|---|")
    for record in records:
        print(
            "| {keyword} | {geo} | {latest} | {avg} | {peak} | {direction} | {change} | {status} |".format(
                keyword=record["keyword"].replace("|", "\\|"),
                geo=record["geo"],
                latest=record["latest_value"] if record["latest_value"] is not None else "-",
                avg=record["avg_value"] if record["avg_value"] is not None else "-",
                peak=record["peak_value"] if record["peak_value"] is not None else "-",
                direction=record["trend_direction"],
                change=record["change_vs_previous"] if record["change_vs_previous"] is not None else "-",
                status=record["fetch_status"],
            )
        )
    print()
    if records:
        print(f"Source: {records[0]['source_url']}")
    print()
    print("## Subscription And Alerts Setup")
    print()
    subscription = auxiliary_setup["google_trends_subscription"]
    print("| Entry | URL | Purpose | Status |")
    print("|---|---|---|---|")
    print(f"| Google Trends subscription | {subscription['url']} | Keyword trend update reminders | {subscription['status']} |")
    for alert in auxiliary_setup["google_alerts"]["alerts"]:
        keyword = alert["keyword"].replace("|", "\\|")
        print(f"| Google Alerts: {keyword} | {alert['url']} | News/web/RSS context updates | manual_setup_required |")
    print()
    print("Google Trends subscriptions and Google Alerts are auxiliary reminder layers, not curve data sources.")


def main():
    parser = argparse.ArgumentParser(description="Monitor Google Trends keyword curves.")
    parser.add_argument("--geo", default="US")
    parser.add_argument("--time", dest="time_range", default="today 12-m")
    parser.add_argument("--category", type=int, default=0)
    parser.add_argument("--property", default="")
    parser.add_argument("--tz", type=int, default=360)
    parser.add_argument("--keywords", nargs="+", required=True)
    parser.add_argument("--snapshot-file", default=None)
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--alerts-frequency", default="daily")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()

    keywords = args.keywords
    if len(keywords) > 5:
        print("A Google Trends comparison group supports at most 5 keywords. Split this task into multiple groups.", file=sys.stderr)
        return 2

    base_dir = Path(__file__).resolve().parents[1]
    snapshot_file = Path(args.snapshot_file) if args.snapshot_file else base_dir / "snapshots" / "keyword_watch_snapshots.jsonl"
    source_url = build_source_url(keywords, args.geo, args.time_range)
    auxiliary_setup = build_auxiliary_setup(keywords, args.geo, args.time_range, args.alerts_frequency)
    observed_at = dt.datetime.now(dt.timezone.utc).isoformat()

    try:
        timeline = fetch_interest_over_time(keywords, args.geo, args.time_range, args.category, args.property, args.tz)
        records = [
            summarize_keyword(keyword, idx, timeline, args.geo, args.time_range, source_url, snapshot_file)
            for idx, keyword in enumerate(keywords)
        ]
    except Exception as error:
        records = manual_review_records(keywords, args.geo, args.time_range, source_url, error)

    if not args.no_save:
        save_snapshots(snapshot_file, records, observed_at)

    output = {
        "observed_at": observed_at,
        "geo": args.geo,
        "time_range": args.time_range,
        "source_url": source_url,
        "subscription_url": TRENDS_SUBSCRIPTION_URL,
        "auxiliary_setup": auxiliary_setup,
        "records": records,
    }
    if args.format == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print_markdown(records, observed_at, auxiliary_setup)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
