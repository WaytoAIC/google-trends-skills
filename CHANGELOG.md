# Changelog

## Unreleased

## v1.1.0 - 2026-06-30

- Made commercial APIs the stable primary path for `google-trends-keyword-watch`: `--provider auto` uses SerpApi/SearchApi when a key is present and **automatically falls back to the local browser path** if the API errors or returns no data (two-pronged reliability). A user-pinned `--provider` is never overridden.
- Added auto-loading of a gitignored `.env` at the skill root, so `SERPAPI_API_KEY` / `SEARCHAPI_API_KEY` persist across runs without touching the shell profile. `.env` is never committed.
- Hardened the local Chrome path against Google's cold-start `429`: a one-time session warm-up (homepage visit + consent) acquires cookies before the Explore fetch; `GOOGLE_TRENDS_CHROME_WARMUP=0` disables it.
- Chrome provider now defaults to **headed** (the `widgetdata/multiline` data XHR is `429`'d under `headless=new` even after warm-up); use `--chrome-headless` for unattended runs.
- Chrome provider now reuses **one warmed session for the whole keyword group** via `--batch-file` (~2+N page loads instead of ~3N), retries only the keywords that still have no curve (`--chrome-retries`), and spaces keywords with jitter (`--chrome-keyword-delay`) to respect Google's per-IP rate budget.
- `build_source_url` now pins `hl` for a clean locale; `.gitignore` now excludes `.env`, `snapshots/`, and `reports/`.
- Enhanced `google-trends-hot-radar` with a low-dependency Trending Now fetcher and RSS-limited fallback status.
- Enhanced `google-trends-keyword-watch` with related Top/Rising queries, full interest-over-time output, provider selection, and manual export links.
- Added Playwright/Chrome-based single-keyword fallback for `google-trends-keyword-watch`, including network JSON capture, screenshot evidence, and clear 429/manual-review status.
- Added a lightweight local HTML renderer for combined keyword-watch and Trending Now reports.
- Added `google-trends-keyword-watch/scripts/render-keyword-watch-html.py` for standalone keyword-watch HTML reports from automatic JSON or manually exported Google Trends CSV.
- Added `google-trends-hot-radar/scripts/render-hot-radar-html.py` and a report JSON template for standalone hot-radar dashboards.
- Reorganized README project section into separate Chinese-first and English sections.

## v1.0.0 - 2026-05-07

- First public release of the Google Trends skill suite.
- Added `google-trends-hot-radar` for hot/trending keyword opportunity discovery.
- Added `google-trends-keyword-watch` for fixed keyword curve monitoring.
- Added Google Trends subscription and Google Alerts setup links as auxiliary reminder layers.
- Added one-command installer for Codex and OpenClaw targets.
