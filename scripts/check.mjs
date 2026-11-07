// Open the site in Chromium, fail on console errors or HTTP 4xx/5xx,
// and save docs/screenshot.png (1200x900).
// Usage: node scripts/check.mjs [url]   (default: serves ./site on port 8080)
import { createRequire } from "node:module";
const { chromium } = createRequire(import.meta.url)("playwright");
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
let url = process.argv[2];
let server;
if (!url) {
  server = spawn("python3", ["-m", "http.server", "8080", "--directory", path.join(root, "site")], { stdio: "ignore" });
  await new Promise((r) => setTimeout(r, 1000));
  url = "http://localhost:8080/";
}

const problems = [];
const browser = await chromium.launch();
async function visit(target, viewport, shot, extra = {}) {
  const page = await browser.newPage({ viewport, ...extra });
  page.on("console", (m) => { if (m.type() === "error") problems.push(`console: ${m.text()}`); });
  page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
  page.on("response", (r) => { if (r.status() >= 400) problems.push(`${r.status()} ${r.url()}`); });
  await page.goto(target, { waitUntil: "networkidle" });
  await page.waitForSelector("#loading", { state: "hidden", timeout: 60000 });
  await page.waitForTimeout(2500);
  if (shot) await page.screenshot({ path: path.join(root, shot) });
  await page.close();
}

const sep = url.includes("?") ? "&" : "?";
await visit(`${url}${sep}frame=6`, { width: 1200, height: 900 }, "docs/screenshot.png");
await visit(`${url}${sep}frame=19&lang=ja`, { width: 390, height: 844 }, null, { isMobile: true, hasTouch: true, deviceScaleFactor: 1 });
await visit(url, { width: 1200, height: 900 }, null, { reducedMotion: "reduce" });
await browser.close();
if (server) server.kill();

if (problems.length) {
  console.error(problems.join("\n"));
  process.exit(1);
}
console.log("OK: no console errors, no 4xx/5xx responses");
