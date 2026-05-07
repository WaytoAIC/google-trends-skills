#!/usr/bin/env node
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const DEFAULT_CHROME_PATHS = [
  process.env.CHROME_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
].filter(Boolean);

function parseArgs(argv) {
  const args = {
    timeoutMs: 45000,
    screenshotDir: path.join(os.tmpdir(), "google-trends-keyword-watch-playwright"),
    headless: process.env.GOOGLE_TRENDS_CHROME_HEADLESS !== "0",
  };
  for (let idx = 0; idx < argv.length; idx += 1) {
    const key = argv[idx];
    const value = argv[idx + 1];
    if (key === "--keyword") {
      args.keyword = value;
      idx += 1;
    } else if (key === "--source-url") {
      args.sourceUrl = value;
      idx += 1;
    } else if (key === "--screenshot-dir") {
      args.screenshotDir = value;
      idx += 1;
    } else if (key === "--timeout-ms") {
      args.timeoutMs = Number(value);
      idx += 1;
    } else if (key === "--headed") {
      args.headless = false;
    }
  }
  if (!args.keyword || !args.sourceUrl) {
    throw new Error("--keyword and --source-url are required");
  }
  return args;
}

function parsePrefixedJson(text) {
  let body = text.trim();
  if (body.startsWith(")]}',")) {
    body = body.slice(5).trim();
  } else if (body.startsWith(")]}'")) {
    const newline = body.indexOf("\n");
    body = newline >= 0 ? body.slice(newline + 1).trim() : body.slice(4).trim();
  }
  return JSON.parse(body);
}

function sanitizeFilePart(value) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "keyword";
}

function findChromeExecutable() {
  for (const candidate of DEFAULT_CHROME_PATHS) {
    if (candidate && fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
}

async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch (error) {
    return {
      loadError: error,
    };
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const result = {
    keyword: args.keyword,
    source_url: args.sourceUrl,
    provider: "playwright",
    playwright_available: false,
    chrome_fetch_method: "screenshot_only",
    fetch_status: "manual_review_required",
    timeline_data: [],
    errors: [],
  };

  const loaded = await loadPlaywright();
  if (loaded.loadError) {
    result.errors.push(
      "Playwright package is not installed for Node import; install it locally or use --provider chrome"
    );
    result.playwright_error = loaded.loadError.message;
    process.stdout.write(JSON.stringify(result, null, 2));
    return;
  }
  result.playwright_available = true;

  const { chromium } = loaded;
  const screenshotDir = path.resolve(args.screenshotDir);
  fs.mkdirSync(screenshotDir, { recursive: true });

  let browser;
  let page;
  try {
    const launchOptions = {
      headless: args.headless,
      args: ["--no-first-run", "--no-default-browser-check", "--disable-sync"],
    };
    const chromePath = findChromeExecutable();
    if (chromePath) {
      launchOptions.executablePath = chromePath;
    } else {
      launchOptions.channel = "chrome";
    }
    browser = await chromium.launch(launchOptions);
    page = await browser.newPage({
      viewport: { width: 1365, height: 900 },
      locale: "en-US",
    });

    let captured = false;
    const responsePromise = new Promise((resolve) => {
      page.on("response", async (response) => {
        if (captured || !response.url().includes("/trends/api/widgetdata/multiline")) {
          return;
        }
        captured = true;
        try {
          const text = await response.text();
          const payload = parsePrefixedJson(text);
          const timeline = payload?.default?.timelineData || [];
          if (timeline.length) {
            result.fetch_status = "success";
            result.chrome_fetch_method = "network_json";
            result.response_url = response.url();
            result.timeline_data = timeline;
          } else {
            result.errors.push("Playwright captured multiline response, but timelineData was empty");
          }
        } catch (error) {
          result.errors.push(`Playwright network parse failed: ${error.message}`);
        }
        resolve(result);
      });
    });

    await page.goto(args.sourceUrl, {
      waitUntil: "domcontentloaded",
      timeout: args.timeoutMs,
    });
    await page.getByRole("button", { name: /accept all|i agree|agree|接受|同意/i }).click({ timeout: 3000 }).catch(() => {});
    await Promise.race([
      responsePromise,
      page.waitForTimeout(args.timeoutMs),
    ]);

    result.page_title = await page.title().catch(() => "");
    if (/error 429|too many requests/i.test(result.page_title) && !result.timeline_data.length) {
      result.errors.push("Google Trends page returned Error 429 in Playwright");
    }

    const filename = `${sanitizeFilePart(args.keyword)}-${new Date().toISOString().replace(/[:.]/g, "-")}.png`;
    const screenshotPath = path.join(screenshotDir, filename);
    await page.screenshot({ path: screenshotPath, fullPage: true, timeout: 8000 }).catch((error) => {
      result.errors.push(`Playwright screenshot failed: ${error.message}`);
    });
    if (fs.existsSync(screenshotPath)) {
      result.screenshot_path = screenshotPath;
    }

    if (!result.timeline_data.length && !result.errors.length) {
      result.errors.push("Playwright did not capture Google Trends multiline data before timeout");
    }
  } catch (error) {
    result.errors.push(error.message);
  } finally {
    if (browser) {
      await browser.close().catch(() => {});
    }
  }

  process.stdout.write(JSON.stringify(result, null, 2));
}

main().catch((error) => {
  process.stdout.write(JSON.stringify({
    provider: "playwright",
    playwright_available: false,
    fetch_status: "manual_review_required",
    chrome_fetch_method: "screenshot_only",
    timeline_data: [],
    errors: [error.message],
  }, null, 2));
  process.exitCode = 0;
});
