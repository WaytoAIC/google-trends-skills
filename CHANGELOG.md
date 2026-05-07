# Changelog

## Unreleased

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
