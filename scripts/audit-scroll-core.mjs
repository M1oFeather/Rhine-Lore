/**
 * Rhine-Lore 全页面滚动审计核心（CDP 通用）。
 *
 * 通过任意兼容 CDP 的 send(method, params) 接口驱动页面：
 * - 原生 WebSocket（模拟器 webview_devtools_remote / Chrome remote debugging）
 * - Playwright CDPSession
 *
 * 规则（docs/design/acceptance-standard.md）：
 * - 整页 outer=0（正文/小说阅读/书架阅读例外）；
 * - 无隐藏裁切：overflow:hidden 容器 scrollHeight <= clientHeight；
 * - 无横向溢出。
 */

const WHITELIST_OUTER = new Set(["正文", "小说阅读", "书架"]);

const MEASURE_EXPRESSION = `(() => {
  const doc = document.scrollingElement;
  const wrap = document.querySelector('.workspace-main .el-scrollbar__wrap');
  const hidden = [];
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.overflowY !== 'hidden') continue;
    if (el.closest('.el-scrollbar')) continue;
    if (el.closest('.sr-only')) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    const delta = el.scrollHeight - el.clientHeight;
    if (delta > 1) {
      hidden.push({
        tag: el.tagName.toLowerCase(),
        cls: String(el.className || '').slice(0, 90),
        delta: Math.round(delta),
      });
    }
  }
  hidden.sort((a, b) => b.delta - a.delta);
  return JSON.stringify({
    docOuter: Math.max(0, doc.scrollHeight - doc.clientHeight),
    mainOuter: wrap ? Math.max(0, wrap.scrollHeight - wrap.clientHeight) : -1,
    hOverflow: Math.max(0, doc.scrollWidth - doc.clientWidth),
    hidden: hidden.slice(0, 6),
  });
})()`;

const NAV_CLICK_EXPRESSION = (label) => `(() => {
  const btn = Array.from(document.querySelectorAll('.sidebar .nav-item')).find(
    (el) => (el.querySelector('.nav-label strong') || {}).textContent === ${JSON.stringify(label)},
  );
  if (!btn) return false;
  btn.click();
  return true;
})()`;

const MOBILE_DETECT = `matchMedia('(max-width: 980px)').matches`;

async function evaluate(send, expression) {
  const res = await send("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (res.exceptionDetails) {
    throw new Error(`Runtime.evaluate failed: ${JSON.stringify(res.exceptionDetails)}`);
  }
  return res.result?.value;
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function navigateTo(send, label, mobile) {
  if (mobile) {
    await evaluate(send, `document.querySelector('.mobile-menu-button')?.click(); true`);
    await wait(420);
  }
  await evaluate(send, NAV_CLICK_EXPRESSION(label));
  await wait(820);
}

/**
 * @param {(method: string, params?: object) => Promise<any>} send
 * @param {{label?: string, pages?: string[]}} opts
 */
export async function auditAll(send, opts = {}) {
  const label = opts.label || "cdp";
  const navLabels = await evaluate(
    send,
    `Array.from(document.querySelectorAll('.sidebar .nav-label strong')).map((el) => el.textContent)`,
  );
  const pages = opts.pages || navLabels || [];
  const results = [];
  const failures = [];

  for (const page of pages) {
    try {
      const mobile = await evaluate(send, MOBILE_DETECT);
      await navigateTo(send, page, mobile);
      const raw = await evaluate(send, MEASURE_EXPRESSION);
      const m = JSON.parse(raw || "{}");
      const allowOuter = WHITELIST_OUTER.has(page);
      const issues = [];
      if (!allowOuter && m.docOuter > 0) issues.push(`doc outer=${m.docOuter}px`);
      if (!allowOuter && m.mainOuter > 0) issues.push(`main outer=${m.mainOuter}px`);
      if (m.hOverflow > 0) issues.push(`横向溢出 ${m.hOverflow}px`);
      if (m.hidden && m.hidden.length > 0) {
        issues.push(`隐藏裁切 ${m.hidden.map((h) => `${h.cls} +${h.delta}px`).join(", ")}`);
      }
      const ok = issues.length === 0;
      results.push({label, page, docOuter: m.docOuter, mainOuter: m.mainOuter, hOverflow: m.hOverflow, hidden: m.hidden || [], ok, issues});
      if (!ok) failures.push({label, page, issues});
    } catch (error) {
      results.push({label, page, ok: false, issues: [`审计异常: ${error.message}`]});
      failures.push({label, page, issues: [`审计异常: ${error.message}`]});
    }
  }

  return {label, results, failures};
}

export function formatReport(report) {
  const lines = [];
  lines.push(`== 滚动审计（${report.label}）==`);
  for (const row of report.results) {
    const mark = row.ok ? "PASS" : "FAIL";
    const extra = row.ok ? "" : `  ${row.issues.join("; ")}`;
    lines.push(`${mark}  ${row.page}  outer=${row.docOuter}/${row.mainOuter}  hx=${row.hOverflow}${extra}`);
  }
  return lines.join("\n");
}
