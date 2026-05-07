#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import html
import io
import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


GOOGLE_TRENDING_BATCH_URL = "https://trends.google.com/_/TrendsUi/data/batchexecute"
RSS_URL = "https://trends.google.com/trending/rss"
SERPAPI_URL = "https://serpapi.com/search.json"
SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"

CATEGORY_IDS = {
    "all": 0,
    "business_and_finance": 3,
    "entertainment": 4,
    "food_and_drink": 5,
    "games": 6,
    "health": 7,
    "hobbies_and_leisure": 8,
    "jobs_and_education": 9,
    "law_and_government": 10,
    "other": 11,
    "pets_and_animals": 13,
    "politics": 14,
    "science": 15,
    "shopping": 16,
    "sports": 17,
    "technology": 18,
    "travel_and_transportation": 19,
    "climate": 20,
}

CATEGORY_NAMES = {
    0: "All",
    2: "Beauty and Fashion",
    3: "Business and Finance",
    4: "Entertainment",
    5: "Food and Drink",
    6: "Games",
    7: "Health",
    8: "Hobbies and Leisure",
    9: "Jobs and Education",
    10: "Law and Government",
    11: "Other",
    13: "Pets and Animals",
    14: "Politics",
    15: "Science",
    16: "Shopping",
    17: "Sports",
    18: "Technology",
    19: "Travel and Transportation",
    20: "Climate",
}

SORT_KEYS = {
    "relevance": 1,
    "volume": 2,
    "recency": 3,
    "title": 4,
}


def http_get(url, headers=None, timeout=30):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json,text/plain,*/*",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def http_post(url, data, headers=None, timeout=30):
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": "https://trends.google.com",
            "Referer": "https://trends.google.com/trending",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def parse_batchexecute(text, rpcid):
    text = text.strip()
    if text.startswith(")]}'"):
        text = text.split("\n", 1)[1].strip()
    payload = json.loads(text)
    for entry in payload:
        if len(entry) >= 3 and entry[0] == "wrb.fr" and entry[1] == rpcid:
            return json.loads(entry[2])
    raise RuntimeError(f"Google Trends batchexecute response did not include {rpcid}")


def category_id(value):
    raw = str(value or "all").strip().lower()
    if raw.isdigit():
        return int(raw)
    return CATEGORY_IDS.get(raw, 0)


def timestamp_from_list(value):
    if isinstance(value, list) and value:
        try:
            return int(value[0])
        except Exception:
            return None
    if isinstance(value, (int, float)):
        return int(value)
    return None


def iso_from_timestamp(value):
    if value is None:
        return None
    return dt.datetime.fromtimestamp(value, dt.timezone.utc).isoformat()


def search_volume_label(value):
    if value is None:
        return None
    try:
        value = int(value)
    except Exception:
        return str(value)
    return f"{value}+"


def build_explore_url(query, geo, hours):
    params = {
        "date": f"now {hours}-H" if int(hours) < 168 else "now 7-d",
        "geo": geo,
        "q": query,
    }
    return "https://trends.google.com/trends/explore?" + urllib.parse.urlencode(params)


def normalize_google_row(row, position, hours):
    query = row[0] if len(row) > 0 else ""
    geo = row[2] if len(row) > 2 else None
    start_timestamp = timestamp_from_list(row[3] if len(row) > 3 else None)
    end_timestamp = timestamp_from_list(row[4] if len(row) > 4 else None)
    search_volume = row[6] if len(row) > 6 else None
    increase_percentage = row[8] if len(row) > 8 else None
    trend_breakdown = row[9] if len(row) > 9 and isinstance(row[9], list) else []
    categories = row[10] if len(row) > 10 and isinstance(row[10], list) else []
    normalized_query = row[12] if len(row) > 12 and isinstance(row[12], str) else query
    return {
        "position": position,
        "query": query,
        "normalized_query": normalized_query,
        "search_volume": search_volume,
        "search_volume_label": search_volume_label(search_volume),
        "increase_percentage": increase_percentage,
        "started_at": iso_from_timestamp(start_timestamp),
        "ended_at": iso_from_timestamp(end_timestamp),
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "active": end_timestamp is None,
        "trend_breakdown": trend_breakdown,
        "categories": [{"id": item, "name": CATEGORY_NAMES.get(item, str(item))} for item in categories],
        "sparkline_values": [],
        "news_titles": [],
        "explore_url": build_explore_url(normalized_query or query, geo or "", hours),
        "source": "google_trending_now",
    }


def fetch_google_trending_now(args):
    cat = category_id(args.category)
    sort_key = SORT_KEYS.get(args.sort, 1)
    rpc_payload = [None, None, args.geo, cat, args.hl, int(args.hours), sort_key]
    f_req = json.dumps([[["i0OFE", json.dumps(rpc_payload, separators=(",", ":")), None, "generic"]]], separators=(",", ":"))
    query = urllib.parse.urlencode(
        {
            "rpcids": "i0OFE",
            "source-path": "/trending",
            "hl": args.hl,
        }
    )
    body = urllib.parse.urlencode({"f.req": f_req}).encode("utf-8")
    text = http_post(f"{GOOGLE_TRENDING_BATCH_URL}?{query}", body)
    parsed = parse_batchexecute(text, "i0OFE")
    rows = parsed[1] if isinstance(parsed, list) and len(parsed) > 1 and isinstance(parsed[1], list) else []
    items = [normalize_google_row(row, idx + 1, args.hours) for idx, row in enumerate(rows)]
    return apply_filters_and_sort(items, args)


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


def fetch_rss_fallback(args, error):
    url = RSS_URL + "?" + urllib.parse.urlencode({"geo": args.geo})
    data = http_get(url, {"Accept": "application/rss+xml,text/xml,*/*"})
    root = ET.fromstring(data)
    items = []
    for position, item in enumerate([node for node in root.iter() if local_name(node.tag) == "item"][: args.limit], start=1):
        query = child_text(item, "title")
        items.append(
            {
                "position": position,
                "query": query,
                "normalized_query": query,
                "search_volume": None,
                "search_volume_label": child_text(item, "approx_traffic"),
                "increase_percentage": None,
                "started_at": None,
                "ended_at": None,
                "start_timestamp": None,
                "end_timestamp": None,
                "active": None,
                "trend_breakdown": [],
                "categories": [],
                "sparkline_values": [],
                "news_titles": all_child_text(item, "news_item_title")[:3],
                "explore_url": build_explore_url(query, args.geo, args.hours),
                "source": "rss_limited",
                "rss_pub_date": child_text(item, "pubDate"),
            }
        )
    return items, str(error)


def serpapi_request(args):
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_API_KEY is not set")
    params = {
        "engine": "google_trends_trending_now",
        "geo": args.geo,
        "hl": args.hl.split("-", 1)[0],
        "hours": args.hours,
        "api_key": api_key,
    }
    if category_id(args.category) != 0:
        params["category_id"] = category_id(args.category)
    if args.status == "active":
        params["only_active"] = "true"
    url = SERPAPI_URL + "?" + urllib.parse.urlencode(params)
    payload = json.loads(http_get(url))
    items = []
    for idx, item in enumerate(payload.get("trending_searches", []), start=1):
        items.append(
            {
                "position": idx,
                "query": item.get("query", ""),
                "normalized_query": item.get("query", ""),
                "search_volume": item.get("search_volume"),
                "search_volume_label": search_volume_label(item.get("search_volume")),
                "increase_percentage": item.get("increase_percentage"),
                "started_at": iso_from_timestamp(item.get("start_timestamp")),
                "ended_at": iso_from_timestamp(item.get("end_timestamp")),
                "start_timestamp": item.get("start_timestamp"),
                "end_timestamp": item.get("end_timestamp"),
                "active": item.get("active"),
                "trend_breakdown": item.get("trend_breakdown", []),
                "categories": item.get("categories", []),
                "sparkline_values": [],
                "news_titles": [],
                "explore_url": item.get("serpapi_google_trends_link") or build_explore_url(item.get("query", ""), args.geo, args.hours),
                "source": "serpapi",
            }
        )
    return apply_filters_and_sort(items, args)


def searchapi_request(args):
    api_key = os.environ.get("SEARCHAPI_API_KEY")
    if not api_key:
        raise RuntimeError("SEARCHAPI_API_KEY is not set")
    time_map = {4: "past_4_hours", 24: "past_24_hours", 48: "past_48_hours", 168: "past_7_days"}
    params = {
        "engine": "google_trends_trending_now",
        "geo": args.geo,
        "time": time_map.get(int(args.hours), "past_24_hours"),
        "api_key": api_key,
    }
    url = SEARCHAPI_URL + "?" + urllib.parse.urlencode(params)
    payload = json.loads(http_get(url))
    items = []
    for idx, item in enumerate(payload.get("trends", []), start=1):
        items.append(
            {
                "position": idx,
                "query": item.get("query", ""),
                "normalized_query": item.get("query", ""),
                "search_volume": item.get("search_volume"),
                "search_volume_label": search_volume_label(item.get("search_volume")),
                "increase_percentage": item.get("percentage_increase"),
                "started_at": item.get("start_date"),
                "ended_at": item.get("end_date"),
                "start_timestamp": None,
                "end_timestamp": None,
                "active": item.get("is_active"),
                "trend_breakdown": item.get("keywords", []),
                "categories": [{"name": value} for value in item.get("categories", [])],
                "sparkline_values": [],
                "news_titles": [],
                "explore_url": build_explore_url(item.get("query", ""), args.geo, args.hours),
                "source": "searchapi",
            }
        )
    return apply_filters_and_sort(items, args)


def apply_filters_and_sort(items, args):
    if args.status == "active":
        items = [item for item in items if item.get("active") is True]
    elif args.status == "ended":
        items = [item for item in items if item.get("active") is False]

    if args.sort == "volume":
        items.sort(key=lambda item: item.get("search_volume") or 0, reverse=True)
    elif args.sort == "recency":
        items.sort(key=lambda item: item.get("start_timestamp") or 0, reverse=True)
    elif args.sort == "title":
        items.sort(key=lambda item: item.get("query", "").lower())

    for position, item in enumerate(items[: args.limit], start=1):
        item["position"] = position
    return items[: args.limit]


def print_markdown(output):
    print(f"# Google Trends Trending Now - {output['geo']} - {output['observed_at'][:10]}")
    print()
    print(f"Fetch status: `{output['fetch_status']}`  Source: `{output['source']}`")
    if output.get("error"):
        print(f"Error: `{output['error']}`")
    print()
    print("| # | Query | Volume | Growth | Started | Active | Breakdown |")
    print("|---:|---|---:|---:|---|---|---|")
    for item in output["items"]:
        breakdown = ", ".join(item.get("trend_breakdown", [])[:5]).replace("|", "\\|") or "-"
        query = str(item.get("query", "")).replace("|", "\\|")
        print(
            f"| {item['position']} | {query} | {item.get('search_volume_label') or '-'} | {item.get('increase_percentage') if item.get('increase_percentage') is not None else '-'} | {item.get('started_at') or '-'} | {item.get('active')} | {breakdown} |"
        )


def print_csv(output):
    fields = [
        "position",
        "query",
        "search_volume",
        "search_volume_label",
        "increase_percentage",
        "started_at",
        "ended_at",
        "active",
        "trend_breakdown",
        "categories",
        "source",
        "explore_url",
    ]
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    for item in output["items"]:
        row = {field: item.get(field) for field in fields}
        row["trend_breakdown"] = "; ".join(item.get("trend_breakdown", []))
        row["categories"] = "; ".join(category.get("name", str(category)) for category in item.get("categories", []))
        writer.writerow(row)
    print(handle.getvalue(), end="")


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch Google Trends Trending Now data with RSS fallback.")
    parser.add_argument("--geo", default="US")
    parser.add_argument("--hours", type=int, choices=[4, 24, 48, 168], default=48)
    parser.add_argument("--category", default="all")
    parser.add_argument("--status", choices=["all", "active", "ended"], default="all")
    parser.add_argument("--sort", choices=["relevance", "volume", "recency", "title"], default="relevance")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--format", choices=["json", "markdown", "csv"], default="json")
    parser.add_argument("--hl", default="en")
    parser.add_argument("--provider", choices=["auto", "google", "serpapi", "searchapi"], default="auto")
    return parser.parse_args()


def main():
    args = parse_args()
    observed_at = dt.datetime.now(dt.timezone.utc).isoformat()
    source = "google_trending_now"
    error = None

    try:
        if args.provider == "serpapi":
            items = serpapi_request(args)
            source = "serpapi"
            fetch_status = "success"
        elif args.provider == "searchapi":
            items = searchapi_request(args)
            source = "searchapi"
            fetch_status = "success"
        else:
            items = fetch_google_trending_now(args)
            fetch_status = "success"
    except Exception as google_error:
        try:
            items, error = fetch_rss_fallback(args, google_error)
            source = "rss_limited"
            fetch_status = "rss_limited"
        except Exception as rss_error:
            items = []
            source = "manual_review_required"
            fetch_status = "manual_review_required"
            error = f"Google Trending Now failed: {google_error}; RSS fallback failed: {rss_error}"

    output = {
        "observed_at": observed_at,
        "geo": args.geo,
        "hours": args.hours,
        "category": args.category,
        "status": args.status,
        "sort": args.sort,
        "provider": args.provider,
        "source": source,
        "fetch_status": fetch_status,
        "items": items,
        "source_url": f"https://trends.google.com/trending?{urllib.parse.urlencode({'geo': args.geo, 'hl': args.hl, 'hours': args.hours})}",
    }
    if error:
        output["error"] = error

    if args.format == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    elif args.format == "markdown":
        print_markdown(output)
    else:
        print_csv(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
