#!/usr/bin/env node
import fs from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";

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
    screenshotDir: path.join(os.tmpdir(), "google-trends-keyword-watch-chrome"),
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

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function withTimeout(promise, ms, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      setTimeout(() => reject(new Error(`${label} timed out after ${ms}ms`)), ms);
    }),
  ]);
}

function getFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = address.port;
      server.close(() => resolve(port));
    });
  });
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${url} returned HTTP ${response.status}`);
  }
  return response.json();
}

async function waitForChrome(port, timeoutMs) {
  const started = Date.now();
  let lastError = null;
  while (Date.now() - started < timeoutMs) {
    try {
      return await fetchJson(`http://127.0.0.1:${port}/json/version`);
    } catch (error) {
      lastError = error;
      await sleep(250);
    }
  }
  throw new Error(`Chrome DevTools did not start: ${lastError ? lastError.message : "timeout"}`);
}

function findChromeExecutable() {
  for (const candidate of DEFAULT_CHROME_PATHS) {
    if (candidate && fs.existsSync(candidate)) {
      return candidate;
    }
  }
  throw new Error("Chrome executable not found. Set CHROME_PATH to the Chrome/Chromium binary.");
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

class CdpSession {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.nextId = 1;
    this.pending = new Map();
    this.handlers = new Map();
  }

  async connect() {
    this.ws = new WebSocket(this.wsUrl);
    this.ws.addEventListener("message", (event) => this.onMessage(event.data));
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("CDP websocket connection timed out")), 10000);
      this.ws.addEventListener("open", () => {
        clearTimeout(timer);
        resolve();
      }, { once: true });
      this.ws.addEventListener("error", () => {
        clearTimeout(timer);
        reject(new Error("CDP websocket connection failed"));
      }, { once: true });
    });
  }

  on(method, handler) {
    if (!this.handlers.has(method)) {
      this.handlers.set(method, []);
    }
    this.handlers.get(method).push(handler);
  }

  onMessage(raw) {
    const message = JSON.parse(raw);
    if (message.id && this.pending.has(message.id)) {
      const { resolve, reject } = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) {
        reject(new Error(message.error.message || JSON.stringify(message.error)));
      } else {
        resolve(message.result || {});
      }
      return;
    }
    if (message.method && this.handlers.has(message.method)) {
      for (const handler of this.handlers.get(message.method)) {
        Promise.resolve(handler(message.params || {})).catch(() => {});
      }
    }
  }

  send(method, params = {}) {
    const id = this.nextId;
    this.nextId += 1;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });
  }

  close() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close();
    }
  }
}

async function getPageTarget(port) {
  let targets = await fetchJson(`http://127.0.0.1:${port}/json/list`);
  let page = targets.find((target) => target.type === "page" && target.webSocketDebuggerUrl);
  if (page) {
    return page;
  }
  const created = await fetchJson(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" });
  if (created.webSocketDebuggerUrl) {
    return created;
  }
  targets = await fetchJson(`http://127.0.0.1:${port}/json/list`);
  page = targets.find((target) => target.type === "page" && target.webSocketDebuggerUrl);
  if (!page) {
    throw new Error("No Chrome page target available");
  }
  return page;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const chromePath = findChromeExecutable();
  const port = await getFreePort();
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), "gt-keyword-chrome-"));
  const screenshotDir = path.resolve(args.screenshotDir);
  fs.mkdirSync(screenshotDir, { recursive: true });

  const chromeArgs = [
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-sync",
    "--window-size=1365,900",
    args.headless ? "--headless=new" : "",
    "about:blank",
  ].filter(Boolean);
  const chrome = spawn(chromePath, chromeArgs, { stdio: ["ignore", "ignore", "pipe"] });
  const chromeErrors = [];
  chrome.stderr.on("data", (chunk) => {
    const text = chunk.toString("utf8").trim();
    if (text) {
      chromeErrors.push(text);
    }
  });

  let cdp;
  const result = {
    keyword: args.keyword,
    source_url: args.sourceUrl,
    provider: "chrome",
    chrome_fetch_method: "screenshot_only",
    fetch_status: "manual_review_required",
    timeline_data: [],
    errors: [],
  };

  try {
    await waitForChrome(port, args.timeoutMs);
    const target = await getPageTarget(port);
    cdp = new CdpSession(target.webSocketDebuggerUrl);
    await cdp.connect();
    await cdp.send("Page.enable");
    await cdp.send("Network.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1365,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });

    const watchedRequests = new Map();
    let captureResolve;
    const capturePromise = new Promise((resolve) => {
      captureResolve = resolve;
    });

    cdp.on("Network.responseReceived", (params) => {
      const response = params.response || {};
      if (response.url && response.url.includes("/trends/api/widgetdata/multiline")) {
        watchedRequests.set(params.requestId, {
          url: response.url,
          status: response.status,
          mimeType: response.mimeType,
        });
      }
    });

    cdp.on("Network.loadingFinished", async (params) => {
      if (!watchedRequests.has(params.requestId) || result.timeline_data.length) {
        return;
      }
      const meta = watchedRequests.get(params.requestId);
      try {
        const body = await cdp.send("Network.getResponseBody", { requestId: params.requestId });
        const text = body.base64Encoded
          ? Buffer.from(body.body, "base64").toString("utf8")
          : body.body;
        const payload = parsePrefixedJson(text);
        const timeline = payload?.default?.timelineData || [];
        if (timeline.length) {
          result.fetch_status = "success";
          result.chrome_fetch_method = "network_json";
          result.response_url = meta.url;
          result.timeline_data = timeline;
        } else {
          result.errors.push("Chrome captured multiline response, but timelineData was empty");
        }
      } catch (error) {
        result.errors.push(`Chrome network parse failed: ${error.message}`);
      }
      captureResolve(result);
    });

    await cdp.send("Page.navigate", { url: args.sourceUrl });
    await Promise.race([capturePromise, sleep(args.timeoutMs)]);

    await cdp.send("Runtime.evaluate", {
      expression: `
        [...document.querySelectorAll('button')].find((button) =>
          /accept all|i agree|agree|接受|同意/i.test(button.innerText || '')
        )?.click()
      `,
      awaitPromise: false,
    }).catch(() => {});

    if (!result.timeline_data.length) {
      await Promise.race([capturePromise, sleep(8000)]);
    }

    const title = await withTimeout(cdp.send("Runtime.evaluate", {
      expression: "document.title",
      returnByValue: true,
    }), 5000, "Reading page title").catch(() => ({ result: { value: "" } }));
    result.page_title = title?.result?.value || "";
    if (/error 429|too many requests/i.test(result.page_title) && !result.timeline_data.length) {
      result.errors.push("Google Trends page returned Error 429 in Chrome");
    }

    const filename = `${sanitizeFilePart(args.keyword)}-${new Date().toISOString().replace(/[:.]/g, "-")}.png`;
    const screenshotPath = path.join(screenshotDir, filename);
    const screenshot = await withTimeout(cdp.send("Page.captureScreenshot", {
      format: "png",
      captureBeyondViewport: true,
    }), 8000, "Capturing screenshot").catch((error) => {
      result.errors.push(error.message);
      return null;
    });
    if (screenshot?.data) {
      fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
      result.screenshot_path = screenshotPath;
    }

    if (!result.timeline_data.length && !result.errors.length) {
      result.errors.push("Chrome did not capture Google Trends multiline data before timeout");
    }
  } catch (error) {
    result.errors.push(error.message);
  } finally {
    if (cdp) {
      cdp.close();
    }
    chrome.kill("SIGTERM");
    try {
      fs.rmSync(userDataDir, { recursive: true, force: true, maxRetries: 3, retryDelay: 200 });
    } catch {
      // Chrome may keep profile files open briefly after SIGTERM; this must not hide the fetch result.
    }
  }

  if (chromeErrors.length && result.fetch_status !== "success") {
    result.chrome_errors = chromeErrors.slice(-5);
  }
  process.stdout.write(JSON.stringify(result, null, 2));
}

main().catch((error) => {
  process.stdout.write(JSON.stringify({
    provider: "chrome",
    fetch_status: "manual_review_required",
    chrome_fetch_method: "screenshot_only",
    timeline_data: [],
    errors: [error.message],
  }, null, 2));
  process.exitCode = 0;
});
