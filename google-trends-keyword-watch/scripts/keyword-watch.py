#!/usr/bin/env python3
import argparse
import datetime as dt
import http.cookiejar
import json
import os
import random
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


EXPLORE_URL = "https://trends.google.com/trends/api/explore"
MULTILINE_URL = "https://trends.google.com/trends/api/widgetdata/multiline"
RELATED_URL = "https://trends.google.com/trends/api/widgetdata/relatedsearches"
TRENDS_SUBSCRIPTION_URL = "https://trends.google.com/trends/subscriptions"
GOOGLE_ALERTS_URL = "https://www.google.com/alerts"
SERPAPI_URL = "https://serpapi.com/search.json"
SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"
GOOGLE_DIRECT_COOLDOWN_SECONDS = int(os.environ.get("GOOGLE_TRENDS_DIRECT_COOLDOWN_SECONDS", "1800"))
COOKIE_JAR = http.cookiejar.CookieJar()
HTTP_OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))


def normalize_property(value):
    value = (value or "").strip().lower()
    aliases = {
        "": "",
        "web": "",
        "web search": "",
        "images": "images",
        "image": "images",
        "image search": "images",
        "news": "news",
        "news search": "news",
        "shopping": "froogle",
        "google shopping": "froogle",
        "froogle": "froogle",
        "youtube": "youtube",
        "youtube search": "youtube",
    }
    return aliases.get(value, value)


def build_source_url(keywords, geo, time_range, trend_property="", hl="en-US"):
    params = {
        "date": time_range,
        "geo": geo,
        "q": ",".join(keywords),
        "hl": hl,
    }
    if trend_property:
        params["gprop"] = trend_property
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


def http_get(url, headers=None, timeout=30, retries=1, retry_delay=2):
    merged_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://trends.google.com/",
        "X-Requested-With": "XMLHttpRequest",
        **(headers or {}),
    }
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, headers=merged_headers)
        try:
            with HTTP_OPENER.open(request, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            if error.code == 429 or error.code not in {500, 502, 503, 504} or attempt >= retries:
                raise
            retry_after = error.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else retry_delay * (attempt + 1)
            time.sleep(delay)


def prime_google_trends_session(source_url):
    request = urllib.request.Request(
        source_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with HTTP_OPENER.open(request, timeout=20) as response:
            response.read(512)
    except urllib.error.HTTPError as error:
        if error.code not in {403, 429}:
            raise


def parse_prefixed_json(text):
    text = text.strip()
    if text.startswith(")]}',"):
        text = text[5:].strip()
    elif text.startswith(")]}'"):
        text = text.split("\n", 1)[1].strip() if "\n" in text else text[4:].strip()
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


def build_manual_export_instruction(source_url):
    return {
        "url": source_url,
        "instruction": "Open the Google Trends Explore link, use the download icon on the Interest over time and Related queries cards, then rerun/report with exported CSV if automation is blocked.",
    }


def fetch_explore_widgets(keywords, geo, time_range, category, trend_property, tz, hl):
    source_url = build_source_url(keywords, geo, time_range, trend_property)
    prime_google_trends_session(source_url)
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
            "hl": hl,
            "tz": str(tz),
            "req": json.dumps(explore_req, separators=(",", ":")),
        }
    )
    explore = parse_prefixed_json(http_get(f"{EXPLORE_URL}?{query}", headers={"Referer": source_url}))
    return explore.get("widgets", [])


def find_widget(widgets, wanted_id, title_fragment=None):
    title_fragment = (title_fragment or "").lower()
    for widget in widgets:
        widget_id = str(widget.get("id", ""))
        title = str(widget.get("title", "")).lower()
        if widget_id == wanted_id or (title_fragment and title_fragment in title):
            return widget
    return None


def is_related_widget(widget):
    widget_id = str(widget.get("id", "")).upper()
    title = str(widget.get("title", "")).lower()
    return "RELATED_QUERIES" in widget_id or "related queries" in title


def widget_keyword(widget):
    request = widget.get("request", {})
    restriction = request.get("restriction", {})
    complex_restriction = restriction.get("complexKeywordsRestriction", {})
    keywords = complex_restriction.get("keyword", [])
    if keywords and isinstance(keywords[0], dict):
        return keywords[0].get("value")
    return None


def fetch_interest_over_time_from_widget(widget, hl, tz, referer=None):
    multiline_req = json.dumps(widget["request"], separators=(",", ":"))
    query = urllib.parse.urlencode(
        {
            "hl": hl,
            "tz": str(tz),
            "req": multiline_req,
            "token": widget["token"],
        }
    )
    headers = {"Referer": referer} if referer else None
    data = parse_prefixed_json(http_get(f"{MULTILINE_URL}?{query}", headers=headers))
    return data.get("default", {}).get("timelineData", [])


def parse_related_ranked_list(data, related_limit):
    ranked = data.get("default", {}).get("rankedList", [])
    top = []
    rising = []
    if ranked:
        top = ranked[0].get("rankedKeyword", []) if isinstance(ranked[0], dict) else []
    if len(ranked) > 1:
        rising = ranked[1].get("rankedKeyword", []) if isinstance(ranked[1], dict) else []

    def clean(items):
        cleaned = []
        for item in items[:related_limit]:
            cleaned.append(
                {
                    "query": item.get("query", ""),
                    "value": item.get("value"),
                    "formatted_value": item.get("formattedValue"),
                    "link": item.get("link"),
                }
            )
        return cleaned

    return {"top": clean(top), "rising": clean(rising)}


def fetch_related_queries_from_widgets(widgets, keywords, related_limit, hl, tz, referer=None):
    related = {keyword: {"top": [], "rising": []} for keyword in keywords}
    errors = []
    related_widgets = [widget for widget in widgets if is_related_widget(widget)]
    if not related_widgets:
        return related, ["Google Trends did not return related query widgets"]

    fallback_index = 0
    for widget in related_widgets:
        keyword = widget_keyword(widget)
        if keyword not in related:
            if fallback_index < len(keywords):
                keyword = keywords[fallback_index]
                fallback_index += 1
            else:
                continue
        try:
            related_req = json.dumps(widget["request"], separators=(",", ":"))
            query = urllib.parse.urlencode(
                {
                    "hl": hl,
                    "tz": str(tz),
                    "req": related_req,
                    "token": widget["token"],
                }
            )
            headers = {"Referer": referer} if referer else None
            data = parse_prefixed_json(http_get(f"{RELATED_URL}?{query}", headers=headers))
            related[keyword] = parse_related_ranked_list(data, related_limit)
        except Exception as error:
            errors.append(f"{keyword}: {error}")
    return related, errors


def build_interest_points(keywords, timeline):
    points = []
    for point in timeline:
        values = {}
        raw_values = point.get("value", [])
        for idx, keyword in enumerate(keywords):
            value = raw_values[idx] if idx < len(raw_values) else None
            values[keyword] = value if isinstance(value, (int, float)) else None
        points.append(
            {
                "time": point.get("time"),
                "formatted_time": point.get("formattedTime") or point.get("formattedAxisTime"),
                "values": values,
                "is_partial": bool(point.get("isPartial")),
            }
        )
    return points


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
            latest_time = point.get("formattedTime") or point.get("formattedAxisTime") or point.get("time")

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


def google_direct_cooldown_file(snapshot_file):
    return snapshot_file.parent / "google_direct_cooldown.json"


def read_google_direct_cooldown(snapshot_file):
    path = google_direct_cooldown_file(snapshot_file)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    cooldown_until = payload.get("cooldown_until")
    if not cooldown_until:
        return None
    try:
        until = dt.datetime.fromisoformat(cooldown_until)
    except ValueError:
        return None
    if until.tzinfo is None:
        until = until.replace(tzinfo=dt.timezone.utc)
    if dt.datetime.now(dt.timezone.utc) >= until:
        return None
    return payload


def write_google_direct_cooldown(snapshot_file, keyword, error):
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "observed_at": now.isoformat(),
        "cooldown_until": (now + dt.timedelta(seconds=GOOGLE_DIRECT_COOLDOWN_SECONDS)).isoformat(),
        "cooldown_seconds": GOOGLE_DIRECT_COOLDOWN_SECONDS,
        "keyword": keyword,
        "reason": "google_direct_rate_limited",
        "detail": str(error),
    }
    path = google_direct_cooldown_file(snapshot_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def is_google_direct_rate_limit(error):
    return isinstance(error, urllib.error.HTTPError) and error.code == 429


def cooldown_error(cooldown):
    return (
        "google_direct_cooldown_active; skipped live Google Trends request after recent rate limit; "
        f"retry_after={cooldown.get('cooldown_until')}"
    )


def fetch_single_google_keyword(keyword, args, snapshot_file):
    source_url = build_source_url([keyword], args.geo, args.time_range, args.property)
    widgets = fetch_explore_widgets([keyword], args.geo, args.time_range, args.category, args.property, args.tz, args.hl)
    timeseries = find_widget(widgets, "TIMESERIES", "interest over time")
    if not timeseries:
        raise RuntimeError("Google Trends did not return a TIMESERIES widget")

    timeline = fetch_interest_over_time_from_widget(timeseries, args.hl, args.tz, source_url)
    record = summarize_keyword(keyword, 0, timeline, args.geo, args.time_range, source_url, snapshot_file)
    record["normalization_scope"] = "single_keyword"
    interest_points = build_interest_points([keyword], timeline)
    for point in interest_points:
        point["normalization_scope"] = "single_keyword"
    return record, interest_points


def merge_single_keyword_interest_points(merged, keyword, points):
    for point in points:
        key = (point.get("time"), point.get("formatted_time"))
        if key not in merged:
            merged[key] = {
                "time": point.get("time"),
                "formatted_time": point.get("formatted_time"),
                "values": {},
                "is_partial": point.get("is_partial", False),
                "normalization_scope": "single_keyword_per_term",
            }
        merged[key]["values"][keyword] = point.get("values", {}).get(keyword)
        merged[key]["is_partial"] = merged[key]["is_partial"] or point.get("is_partial", False)


def fetch_google_keyword_data(args, source_url, snapshot_file):
    cooldown = read_google_direct_cooldown(snapshot_file)
    if cooldown:
        return {
            "fetch_status": "manual_review_required",
            "records": manual_review_records(
                args.keywords,
                args.geo,
                args.time_range,
                source_url,
                cooldown_error(cooldown),
            ),
            "interest_over_time": [],
            "related_queries": {keyword: {"top": [], "rising": []} for keyword in args.keywords},
            "errors": [cooldown_error(cooldown)],
            "provider": "google",
            "normalization_scope": "single_keyword_per_term",
            "comparison_status": "not_cross_keyword_comparable_without_provider",
        }

    records = []
    merged_points = {}
    errors = []
    for idx, keyword in enumerate(args.keywords):
        try:
            record, keyword_points = fetch_single_google_keyword(keyword, args, snapshot_file)
            records.append(record)
            merge_single_keyword_interest_points(merged_points, keyword, keyword_points)
        except Exception as error:
            keyword_source_url = build_source_url([keyword], args.geo, args.time_range, args.property)
            if is_google_direct_rate_limit(error):
                cooldown = write_google_direct_cooldown(snapshot_file, keyword, error)
                message = cooldown_error(cooldown)
            else:
                message = str(error)
            records.extend(manual_review_records([keyword], args.geo, args.time_range, keyword_source_url, message))
            errors.append(f"{keyword}: {message}")
        if idx < len(args.keywords) - 1:
            time.sleep(2)

    interest_points = [
        merged_points[key]
        for key in sorted(merged_points, key=lambda item: int(item[0] or 0))
    ]

    related = {keyword: {"top": [], "rising": []} for keyword in args.keywords}
    fetch_status = "success" if not errors else "partial"
    if records and all(record.get("fetch_status") == "manual_review_required" for record in records):
        fetch_status = "manual_review_required"
    if args.include_related:
        errors.append(
            "related queries skipped in google direct mode to avoid Google Trends 429; use --provider serpapi or --provider searchapi for related queries"
        )
        if fetch_status == "success":
            fetch_status = "partial"

    return {
        "fetch_status": fetch_status,
        "records": records,
        "interest_over_time": interest_points,
        "related_queries": related,
        "errors": errors,
        "provider": "google",
        "normalization_scope": "single_keyword_per_term",
        "comparison_status": "not_cross_keyword_comparable_without_provider",
    }


def serpapi_request(params, api_key):
    params = {**params, "api_key": api_key}
    url = SERPAPI_URL + "?" + urllib.parse.urlencode(params)
    return json.loads(http_get(url))


def searchapi_request(params, api_key):
    params = {**params, "api_key": api_key}
    url = SEARCHAPI_URL + "?" + urllib.parse.urlencode(params)
    return json.loads(http_get(url))


def parse_commercial_timeseries(payload, keywords):
    timeline = payload.get("interest_over_time", {}).get("timeline_data") or payload.get("interest_over_time", [])
    points = []
    for point in timeline:
        values = {}
        point_values = point.get("values", [])
        if isinstance(point_values, list):
            for idx, keyword in enumerate(keywords):
                raw = point_values[idx] if idx < len(point_values) else {}
                if isinstance(raw, dict):
                    values[keyword] = raw.get("extracted_value", raw.get("value"))
                else:
                    values[keyword] = raw if isinstance(raw, (int, float)) else None
        elif isinstance(point_values, dict):
            values = {keyword: point_values.get(keyword) for keyword in keywords}
        points.append(
            {
                "time": point.get("timestamp") or point.get("time"),
                "formatted_time": point.get("date") or point.get("formatted_time"),
                "values": values,
                "is_partial": False,
            }
        )
    return points


def records_from_interest_points(keywords, geo, time_range, source_url, snapshot_file, points):
    timeline = []
    for point in points:
        timeline.append(
            {
                "time": point.get("time"),
                "formattedTime": point.get("formatted_time"),
                "value": [point.get("values", {}).get(keyword) for keyword in keywords],
            }
        )
    return [
        summarize_keyword(keyword, idx, timeline, geo, time_range, source_url, snapshot_file)
        for idx, keyword in enumerate(keywords)
    ]


def parse_commercial_related(payload, keyword):
    related = {keyword: {"top": [], "rising": []}}
    raw = payload.get("related_queries", {})
    top = raw.get("top") or raw.get("top_queries") or []
    rising = raw.get("rising") or raw.get("rising_queries") or []

    def clean(items):
        cleaned = []
        for item in items:
            if isinstance(item, str):
                cleaned.append({"query": item, "value": None, "formatted_value": None})
            elif isinstance(item, dict):
                cleaned.append(
                    {
                        "query": item.get("query", item.get("title", "")),
                        "value": item.get("value", item.get("extracted_value")),
                        "formatted_value": item.get("formatted_value", item.get("formattedValue")),
                        "link": item.get("link"),
                    }
                )
        return cleaned

    related[keyword]["top"] = clean(top)
    related[keyword]["rising"] = clean(rising)
    return related[keyword]


def fetch_commercial_keyword_data(args, source_url, snapshot_file, provider):
    if provider == "serpapi":
        api_key = os.environ.get("SERPAPI_API_KEY")
        if not api_key:
            raise RuntimeError("SERPAPI_API_KEY is not set")
        payload = serpapi_request(
            {
                "engine": "google_trends",
                "q": ",".join(args.keywords),
                "geo": args.geo,
                "date": args.time_range,
                "data_type": "TIMESERIES",
                "hl": args.hl.split("-", 1)[0],
                "tz": args.tz,
                "gprop": args.property,
            },
            api_key,
        )
        request_related = lambda keyword: serpapi_request(
            {
                "engine": "google_trends",
                "q": keyword,
                "geo": args.geo,
                "date": args.time_range,
                "data_type": "RELATED_QUERIES",
                "hl": args.hl.split("-", 1)[0],
                "tz": args.tz,
                "gprop": args.property,
            },
            api_key,
        )
    else:
        api_key = os.environ.get("SEARCHAPI_API_KEY")
        if not api_key:
            raise RuntimeError("SEARCHAPI_API_KEY is not set")
        payload = searchapi_request(
            {
                "engine": "google_trends",
                "q": ",".join(args.keywords),
                "geo": args.geo,
                "date": args.time_range,
            },
            api_key,
        )
        request_related = lambda keyword: searchapi_request(
            {
                "engine": "google_trends",
                "q": keyword,
                "geo": args.geo,
                "date": args.time_range,
                "data_type": "RELATED_QUERIES",
            },
            api_key,
        )

    interest_points = parse_commercial_timeseries(payload, args.keywords)
    records = records_from_interest_points(args.keywords, args.geo, args.time_range, source_url, snapshot_file, interest_points)
    related = {keyword: {"top": [], "rising": []} for keyword in args.keywords}
    errors = []
    if args.include_related:
        for keyword in args.keywords:
            try:
                related_payload = request_related(keyword)
                related[keyword] = parse_commercial_related(related_payload, keyword)
                related[keyword]["top"] = related[keyword]["top"][: args.related_limit]
                related[keyword]["rising"] = related[keyword]["rising"][: args.related_limit]
            except Exception as error:
                errors.append(f"{keyword}: {error}")

    fetch_status = "success" if interest_points else "manual_review_required"
    if errors and fetch_status == "success":
        fetch_status = "partial"
    for record in records:
        record["fetch_status"] = fetch_status
    return {
        "fetch_status": fetch_status,
        "records": records,
        "interest_over_time": interest_points,
        "related_queries": related,
        "errors": errors,
        "provider": provider,
    }


def chrome_screenshot_dir(snapshot_file):
    return snapshot_file.parent / "chrome"


def playwright_screenshot_dir(snapshot_file):
    return snapshot_file.parent / "playwright"


def run_chrome_fetch(keyword, args, source_url, snapshot_file):
    script = Path(__file__).resolve().parent / "chrome-trends-fetch.mjs"
    if not script.exists():
        raise RuntimeError(f"Chrome fallback script not found: {script}")
    cmd = [
        "node",
        str(script),
        "--keyword",
        keyword,
        "--source-url",
        source_url,
        "--screenshot-dir",
        str(chrome_screenshot_dir(snapshot_file)),
        "--timeout-ms",
        str(args.chrome_timeout_ms),
    ]
    if args.chrome_headed:
        cmd.append("--headed")
    try:
        completed = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=(args.chrome_timeout_ms / 1000) + 45,
            check=False,
        )
    except FileNotFoundError as error:
        raise RuntimeError("Node.js is required for --provider chrome") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Chrome fallback timed out after {error.timeout} seconds") from error

    if not completed.stdout.strip():
        detail = completed.stderr.strip() or f"chrome fetch exited with code {completed.returncode}"
        raise RuntimeError(detail)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        detail = completed.stdout[:500]
        raise RuntimeError(f"Chrome fallback returned non-JSON output: {detail}") from error
    if completed.stderr.strip():
        payload.setdefault("stderr", completed.stderr.strip())
    return payload


def run_chrome_batch(jobs, args, snapshot_file):
    """Run every keyword in one warmed Chrome session (warm-up once, reuse cookies).

    jobs: [{"keyword": ..., "sourceUrl": ...}]. Returns {keyword: payload}. This is the
    rate-limit-friendly path: ~2+N page loads instead of ~3N from relaunching Chrome
    per keyword, so Google's per-IP budget lasts much longer.
    """
    script = Path(__file__).resolve().parent / "chrome-trends-fetch.mjs"
    if not script.exists():
        raise RuntimeError(f"Chrome fallback script not found: {script}")
    batch_dir = chrome_screenshot_dir(snapshot_file)
    batch_dir.mkdir(parents=True, exist_ok=True)
    batch_path = batch_dir / "batch-jobs.json"
    batch_path.write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
    cmd = [
        "node",
        str(script),
        "--batch-file",
        str(batch_path),
        "--screenshot-dir",
        str(batch_dir),
        "--timeout-ms",
        str(args.chrome_timeout_ms),
        "--keyword-delay-ms",
        str(int(args.chrome_keyword_delay * 1000)),
    ]
    if args.chrome_headed:
        cmd.append("--headed")
    per_keyword = args.chrome_timeout_ms / 1000 + args.chrome_keyword_delay + 20
    overall_timeout = per_keyword * max(1, len(jobs)) + 60
    try:
        completed = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=overall_timeout,
            check=False,
        )
    except FileNotFoundError as error:
        raise RuntimeError("Node.js is required for --provider chrome") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Chrome batch timed out after {error.timeout} seconds") from error

    if not completed.stdout.strip():
        detail = completed.stderr.strip() or f"chrome batch exited with code {completed.returncode}"
        raise RuntimeError(detail)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        detail = completed.stdout[:500]
        raise RuntimeError(f"Chrome batch returned non-JSON output: {detail}") from error
    results = payload.get("results") if isinstance(payload, dict) else None
    if results is None:
        results = [payload]
    return {item.get("keyword"): item for item in results if item.get("keyword")}


def run_playwright_fetch(keyword, args, source_url, snapshot_file):
    script = Path(__file__).resolve().parent / "playwright-trends-fetch.mjs"
    if not script.exists():
        raise RuntimeError(f"Playwright fallback script not found: {script}")
    cmd = [
        "node",
        str(script),
        "--keyword",
        keyword,
        "--source-url",
        source_url,
        "--screenshot-dir",
        str(playwright_screenshot_dir(snapshot_file)),
        "--timeout-ms",
        str(args.chrome_timeout_ms),
    ]
    if args.chrome_headed:
        cmd.append("--headed")
    try:
        completed = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=(args.chrome_timeout_ms / 1000) + 45,
            check=False,
        )
    except FileNotFoundError as error:
        raise RuntimeError("Node.js is required for --provider playwright") from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Playwright fallback timed out after {error.timeout} seconds") from error

    if not completed.stdout.strip():
        detail = completed.stderr.strip() or f"playwright fetch exited with code {completed.returncode}"
        raise RuntimeError(detail)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        detail = completed.stdout[:500]
        raise RuntimeError(f"Playwright fallback returned non-JSON output: {detail}") from error
    if completed.stderr.strip():
        payload.setdefault("stderr", completed.stderr.strip())
    return payload


def build_chrome_record(keyword, source_url, payload, args, snapshot_file):
    """Turn a single keyword's chrome payload into (record, points, errors, artifact)."""
    payload = payload or {}
    timeline = payload.get("timeline_data") or []
    errors = payload.get("errors") or []
    artifact = {
        "keyword": keyword,
        "source_url": source_url,
        "screenshot_path": payload.get("screenshot_path"),
        "chrome_fetch_method": payload.get("chrome_fetch_method"),
        "page_title": payload.get("page_title"),
    }

    if timeline:
        record = summarize_keyword(keyword, 0, timeline, args.geo, args.time_range, source_url, snapshot_file)
        record["provider"] = "chrome"
        record["normalization_scope"] = "single_keyword"
        record["chrome_fetch_method"] = payload.get("chrome_fetch_method", "network_json")
        record["screenshot_path"] = payload.get("screenshot_path")
        interest_points = build_interest_points([keyword], timeline)
        for point in interest_points:
            point["normalization_scope"] = "single_keyword"
        return record, interest_points, errors, artifact

    message = "; ".join(errors) if errors else "Chrome did not capture Google Trends curve data"
    record = manual_review_records([keyword], args.geo, args.time_range, source_url, message)[0]
    record["provider"] = "chrome"
    record["chrome_fetch_method"] = payload.get("chrome_fetch_method", "screenshot_only")
    record["screenshot_path"] = payload.get("screenshot_path")
    return record, [], [message], artifact


def fetch_single_playwright_keyword(keyword, args, snapshot_file):
    source_url = build_source_url([keyword], args.geo, args.time_range, args.property)
    payload = run_playwright_fetch(keyword, args, source_url, snapshot_file)
    timeline = payload.get("timeline_data") or []
    errors = payload.get("errors") or []
    artifact = {
        "keyword": keyword,
        "source_url": source_url,
        "screenshot_path": payload.get("screenshot_path"),
        "chrome_fetch_method": payload.get("chrome_fetch_method"),
        "page_title": payload.get("page_title"),
        "playwright_available": payload.get("playwright_available"),
    }

    if timeline:
        record = summarize_keyword(keyword, 0, timeline, args.geo, args.time_range, source_url, snapshot_file)
        record["provider"] = "playwright"
        record["normalization_scope"] = "single_keyword"
        record["chrome_fetch_method"] = payload.get("chrome_fetch_method", "network_json")
        record["screenshot_path"] = payload.get("screenshot_path")
        record["playwright_available"] = payload.get("playwright_available")
        interest_points = build_interest_points([keyword], timeline)
        for point in interest_points:
            point["normalization_scope"] = "single_keyword"
        return record, interest_points, errors, artifact

    message = "; ".join(errors) if errors else "Playwright did not capture Google Trends curve data"
    record = manual_review_records([keyword], args.geo, args.time_range, source_url, message)[0]
    record["provider"] = "playwright"
    record["chrome_fetch_method"] = payload.get("chrome_fetch_method", "screenshot_only")
    record["screenshot_path"] = payload.get("screenshot_path")
    record["playwright_available"] = payload.get("playwright_available")
    return record, [], [message], artifact


def fetch_chrome_keyword_data(args, source_url, snapshot_file):
    keywords = list(args.keywords)
    source_urls = {
        kw: build_source_url([kw], args.geo, args.time_range, args.property)
        for kw in keywords
    }
    payloads = {}  # keyword -> latest payload

    # One warmed session serves the whole batch. Retry only the keywords that still
    # have no curve, on a fresh session with a long backoff. Aggressive retries burn
    # Google's per-IP budget and trigger a longer cooldown, so keep them few and spaced.
    attempts = max(1, getattr(args, "chrome_retries", 2))
    for attempt in range(attempts):
        pending = [kw for kw in keywords if not (payloads.get(kw) or {}).get("timeline_data")]
        if not pending:
            break
        jobs = [{"keyword": kw, "sourceUrl": source_urls[kw]} for kw in pending]
        try:
            batch = run_chrome_batch(jobs, args, snapshot_file)
        except Exception as error:
            for kw in pending:
                payloads.setdefault(kw, {"errors": [str(error)]})
            batch = {}
        for kw in pending:
            if kw in batch:
                payloads[kw] = batch[kw]
        still_pending = [kw for kw in keywords if not (payloads.get(kw) or {}).get("timeline_data")]
        if not still_pending or attempt >= attempts - 1:
            break
        time.sleep(25 + attempt * 20 + random.uniform(0, 6))

    records = []
    merged_points = {}
    errors = []
    artifacts = []
    for keyword in keywords:
        record, keyword_points, keyword_errors, artifact = build_chrome_record(
            keyword, source_urls[keyword], payloads.get(keyword), args, snapshot_file
        )
        records.append(record)
        artifacts.append(artifact)
        for error in keyword_errors:
            errors.append(f"{keyword}: {error}")
        merge_single_keyword_interest_points(merged_points, keyword, keyword_points)

    interest_points = [
        merged_points[key]
        for key in sorted(merged_points, key=lambda item: int(item[0] or 0))
    ]
    fetch_status = "success" if not errors else "partial"
    if records and all(record.get("fetch_status") == "manual_review_required" for record in records):
        fetch_status = "manual_review_required"
    if args.include_related:
        errors.append(
            "related queries skipped in chrome mode; use --provider serpapi or --provider searchapi for related queries"
        )
        if fetch_status == "success":
            fetch_status = "partial"

    return {
        "fetch_status": fetch_status,
        "records": records,
        "interest_over_time": interest_points,
        "related_queries": {keyword: {"top": [], "rising": []} for keyword in args.keywords},
        "errors": errors,
        "provider": "chrome",
        "normalization_scope": "single_keyword_per_term",
        "comparison_status": "not_cross_keyword_comparable_without_provider",
        "chrome_fetch_method": "network_json" if any(record.get("chrome_fetch_method") == "network_json" for record in records) else "screenshot_only",
        "artifacts": artifacts,
    }


def fetch_playwright_keyword_data(args, source_url, snapshot_file):
    records = []
    merged_points = {}
    errors = []
    artifacts = []
    for idx, keyword in enumerate(args.keywords):
        try:
            record, keyword_points, keyword_errors, artifact = fetch_single_playwright_keyword(keyword, args, snapshot_file)
            records.append(record)
            artifacts.append(artifact)
            for error in keyword_errors:
                errors.append(f"{keyword}: {error}")
            merge_single_keyword_interest_points(merged_points, keyword, keyword_points)
        except Exception as error:
            keyword_source_url = build_source_url([keyword], args.geo, args.time_range, args.property)
            records.extend(manual_review_records([keyword], args.geo, args.time_range, keyword_source_url, error))
            errors.append(f"{keyword}: {error}")
        if idx < len(args.keywords) - 1:
            # Google Trends rate-limits per IP/session on a time window. Each keyword
            # relaunches Chrome and re-warms, so back-to-back fetches exhaust the budget
            # and randomly 429 some terms. Space them out (with jitter) to stay reliable.
            time.sleep(args.chrome_keyword_delay + random.uniform(0, 6))

    interest_points = [
        merged_points[key]
        for key in sorted(merged_points, key=lambda item: int(item[0] or 0))
    ]
    fetch_status = "success" if not errors else "partial"
    if records and all(record.get("fetch_status") == "manual_review_required" for record in records):
        fetch_status = "manual_review_required"
    if args.include_related:
        errors.append(
            "related queries skipped in playwright mode; use --provider serpapi or --provider searchapi for related queries"
        )
        if fetch_status == "success":
            fetch_status = "partial"

    return {
        "fetch_status": fetch_status,
        "records": records,
        "interest_over_time": interest_points,
        "related_queries": {keyword: {"top": [], "rising": []} for keyword in args.keywords},
        "errors": errors,
        "provider": "playwright",
        "normalization_scope": "single_keyword_per_term",
        "comparison_status": "not_cross_keyword_comparable_without_provider",
        "chrome_fetch_method": "network_json" if any(record.get("chrome_fetch_method") == "network_json" for record in records) else "screenshot_only",
        "artifacts": artifacts,
        "playwright_available": any(record.get("playwright_available") for record in records),
    }


def is_playwright_available():
    try:
        result = subprocess.run(
            ["node", "-e", "import('playwright').then(()=>process.exit(0)).catch(()=>process.exit(1))"],
            text=True,
            capture_output=True,
            timeout=8,
            check=False,
        )
    except Exception:
        return False
    return result.returncode == 0


def resolve_provider(provider):
    if provider != "auto":
        return provider
    if os.environ.get("SERPAPI_API_KEY"):
        return "serpapi"
    if os.environ.get("SEARCHAPI_API_KEY"):
        return "searchapi"
    if is_playwright_available():
        return "playwright"
    return "chrome"


def save_snapshots(snapshot_file, records, observed_at):
    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    with snapshot_file.open("a", encoding="utf-8") as handle:
        for record in records:
            payload = {"observed_at": observed_at, **record}
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def print_markdown(output):
    print(f"# Google Trends Keyword Watch - {output['observed_at'][:10]}")
    print()
    print(f"Fetch status: `{output['fetch_status']}`  Provider: `{output['provider']}`")
    if output.get("error"):
        print(f"Error: `{output['error']}`")
    print()
    print("| Keyword | Geo | Latest | Avg | Peak | Direction | Change vs previous | Status |")
    print("|---|---|---:|---:|---:|---|---:|---|")
    for record in output["records"]:
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
    print(f"Source: {output['source_url']}")
    print(f"Manual export: {output['manual_export_url']}")
    if output.get("related_queries"):
        print()
        print("## Related Queries")
        for keyword, related in output["related_queries"].items():
            top = ", ".join(item["query"] for item in related.get("top", [])[:5] if item.get("query")) or "-"
            rising = ", ".join(item["query"] for item in related.get("rising", [])[:5] if item.get("query")) or "-"
            print(f"- **{keyword}** Top: {top}")
            print(f"- **{keyword}** Rising: {rising}")
    print()
    print("Google Trends subscriptions and Google Alerts are auxiliary reminder layers, not curve data sources.")


def parse_args():
    parser = argparse.ArgumentParser(description="Monitor Google Trends keyword curves and related queries.")
    parser.add_argument("--geo", default="US")
    parser.add_argument("--time", dest="time_range", default="today 12-m")
    parser.add_argument("--category", type=int, default=0)
    parser.add_argument("--property", default="")
    parser.add_argument("--tz", type=int, default=360)
    parser.add_argument("--hl", default="en-US")
    parser.add_argument("--keywords", nargs="+", required=True)
    parser.add_argument("--snapshot-file", default=None)
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--alerts-frequency", default="daily")
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--include-related", action="store_true")
    parser.add_argument("--related-limit", type=int, default=50)
    parser.add_argument("--mode", choices=["monitor"], default="monitor")
    parser.add_argument("--provider", choices=["auto", "playwright", "chrome", "google", "serpapi", "searchapi"], default="auto")
    parser.add_argument("--chrome-timeout-ms", type=int, default=45000)
    # Headed is the default: Google 429s the widgetdata XHR under headless=new even
    # after session warm-up, but lets it through in a visible window. --chrome-headless
    # forces headless for unattended runs (expect more manual_review_required results).
    parser.add_argument("--chrome-headed", action="store_true", default=True)
    parser.add_argument("--chrome-headless", action="store_true")
    parser.add_argument("--chrome-retries", type=int, default=2)
    parser.add_argument("--chrome-keyword-delay", type=float, default=12.0)
    return parser.parse_args()


def load_local_env():
    """Load KEY=VALUE pairs from a gitignored `.env` at the skill root into the
    environment (without overriding values already set). Lets the SerpApi/SearchApi key
    persist for every run without writing the secret into the shell profile."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        pass


def fetch_with_provider(provider, args, source_url, snapshot_file):
    if provider in {"serpapi", "searchapi"}:
        return fetch_commercial_keyword_data(args, source_url, snapshot_file, provider)
    if provider == "playwright":
        return fetch_playwright_keyword_data(args, source_url, snapshot_file)
    if provider == "chrome":
        return fetch_chrome_keyword_data(args, source_url, snapshot_file)
    return fetch_google_keyword_data(args, source_url, snapshot_file)


def fetch_keyword_data(provider, requested, args, source_url, snapshot_file):
    """Run the resolved provider; if a commercial provider was auto-selected and it
    errors or returns no curve (quota exhausted, outage, bad key), fall back to the local
    browser path so the user is never left with zero data. This is the two-pronged setup:
    API primary, local browser backup. A user-pinned --provider is never overridden."""
    try:
        result = fetch_with_provider(provider, args, source_url, snapshot_file)
        error = None
    except Exception as exc:
        result, error = None, str(exc)

    commercial = provider in {"serpapi", "searchapi"}
    empty = result is not None and result.get("fetch_status") == "manual_review_required"
    if commercial and requested == "auto" and (error or empty):
        note = (
            f"commercial provider {provider} "
            f"{'errored: ' + error if error else 'returned no data'}; fell back to local browser"
        )
        try:
            fallback = fetch_chrome_keyword_data(args, source_url, snapshot_file)
            fallback.setdefault("errors", []).insert(0, note)
            fallback["primary_provider"] = provider
            return fallback
        except Exception as exc2:
            error = f"{note}; chrome fallback also failed: {exc2}"
            result = None

    if result is None:
        raise RuntimeError(error or "fetch failed")
    return result


def main():
    load_local_env()
    args = parse_args()
    if args.chrome_headless:
        args.chrome_headed = False
    args.property = normalize_property(args.property)
    if args.related_limit <= 0:
        print("--related-limit must be a positive integer", file=sys.stderr)
        return 2
    if len(args.keywords) > 5:
        print("A Google Trends comparison group supports at most 5 keywords. Split this task into multiple groups.", file=sys.stderr)
        return 2

    base_dir = Path(__file__).resolve().parents[1]
    snapshot_file = Path(args.snapshot_file) if args.snapshot_file else base_dir / "snapshots" / "keyword_watch_snapshots.jsonl"
    source_url = build_source_url(args.keywords, args.geo, args.time_range, args.property)
    auxiliary_setup = build_auxiliary_setup(args.keywords, args.geo, args.time_range, args.alerts_frequency)
    observed_at = dt.datetime.now(dt.timezone.utc).isoformat()
    manual_export = build_manual_export_instruction(source_url)

    provider = resolve_provider(args.provider)
    try:
        result = fetch_keyword_data(provider, args.provider, args, source_url, snapshot_file)
    except Exception as error:
        result = {
            "fetch_status": "manual_review_required",
            "records": manual_review_records(args.keywords, args.geo, args.time_range, source_url, error),
            "interest_over_time": [],
            "related_queries": {keyword: {"top": [], "rising": []} for keyword in args.keywords},
            "errors": [str(error)],
            "provider": provider,
            "error": str(error),
        }

    if not args.no_save:
        save_snapshots(snapshot_file, result["records"], observed_at)

    output = {
        "observed_at": observed_at,
        "geo": args.geo,
        "time_range": args.time_range,
        "category": args.category,
        "property": args.property,
        "mode": args.mode,
        "provider": result.get("provider", provider),
        "fetch_status": result["fetch_status"],
        "source_url": source_url,
        "manual_export_url": manual_export["url"],
        "manual_export_instruction": manual_export["instruction"],
        "subscription_url": TRENDS_SUBSCRIPTION_URL,
        "auxiliary_setup": auxiliary_setup,
        "records": result["records"],
        "interest_over_time": result["interest_over_time"],
        "related_queries": result["related_queries"],
        "errors": result.get("errors", []),
    }
    if result.get("error"):
        output["error"] = result["error"]
    if result.get("normalization_scope"):
        output["normalization_scope"] = result["normalization_scope"]
    if result.get("comparison_status"):
        output["comparison_status"] = result["comparison_status"]
    if result.get("chrome_fetch_method"):
        output["chrome_fetch_method"] = result["chrome_fetch_method"]
    if result.get("artifacts"):
        output["artifacts"] = result["artifacts"]
    if "playwright_available" in result:
        output["playwright_available"] = result["playwright_available"]

    if args.format == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print_markdown(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
