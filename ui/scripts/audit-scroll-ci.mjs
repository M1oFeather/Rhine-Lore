/**
 * CI 滚动审计：本地起 Chromium（Playwright），对桌面与手机视口
 * 逐页执行滚动审计（复用 scripts/audit-scroll-core.mjs）。
 *
 * 用法：
 *   node scripts/audit-scroll-ci.mjs http://127.0.0.1:8786 [--dark]
 */

import {chromium} from "playwright";

import {auditAll, formatReport} from "../../scripts/audit-scroll-core.mjs";

const baseUrl = process.argv[2] || "http://127.0.0.1:8786";
const darkMode = process.argv.includes("--dark");
const viewports = [
  {label: "desktop-1280", width: 1280, height: 800},
  {label: "mobile-390", width: 390, height: 844, isMobile: true, hasTouch: true},
];

function launchBrowser() {
  if (process.env.PLAYWRIGHT_CHANNEL) {
    return chromium.launch({channel: process.env.PLAYWRIGHT_CHANNEL});
  }
  return chromium.launch().catch(async (error) => {
    console.warn(`Playwright 自带 Chromium 不可用，回退到 Edge: ${error.message}`);
    return chromium.launch({channel: "msedge"});
  });
}

const browser = await launchBrowser();
let failed = false;

try {
  for (const vp of viewports) {
    const context = await browser.newContext({
      viewport: {width: vp.width, height: vp.height},
      isMobile: vp.isMobile || false,
      hasTouch: vp.hasTouch || false,
      deviceScaleFactor: vp.isMobile ? 3 : 1,
    });
    const page = await context.newPage();
    page.on("console", (msg) => {
      if (msg.type() === "error") console.error(`[console:error] ${msg.text()}`);
    });
    await page.goto(baseUrl, {waitUntil: "domcontentloaded"});
    if (darkMode) {
      await page.evaluate(() => localStorage.setItem("rhine-lore-theme", "dark"));
      await page.goto(baseUrl, {waitUntil: "domcontentloaded"});
    }
    await page.waitForTimeout(1400);
    const session = await context.newCDPSession(page);
    const send = (method, params = {}) => session.send(method, params);
    const report = await auditAll(send, {label: darkMode ? `${vp.label}-dark` : vp.label});
    console.log(formatReport(report));
    console.log(`\n${vp.label}: ${report.failures.length} 个失败 / ${report.results.length} 个页面`);
    if (report.failures.length > 0) failed = true;
    await context.close();
  }
} finally {
  await browser.close();
}

process.exit(failed ? 1 : 0);
