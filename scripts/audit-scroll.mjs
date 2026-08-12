/**
 * Rhine-Lore 滚动审计 CLI（CDP WebSocket）。
 *
 * 用法：
 *   node scripts/audit-scroll.mjs ws://127.0.0.1:9222/devtools/page/<id>
 *
 * 可对 Android 模拟器 WebView（webview_devtools_remote_<pid>）或
 * Chrome remote debugging 端口执行全页面滚动审计。
 */

import {auditAll, formatReport} from "./audit-scroll-core.mjs";

const wsUrl = process.argv[2];
if (!wsUrl) {
  console.error("用法: node scripts/audit-scroll.mjs <cdp-websocket-url>");
  process.exit(2);
}

const ws = new WebSocket(wsUrl);
let id = 0;
const pending = new Map();

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const msgId = ++id;
    pending.set(msgId, {resolve, reject});
    ws.send(JSON.stringify({id: msgId, method, params}));
  });
}

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.id && pending.has(msg.id)) {
    const p = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) p.reject(new Error(JSON.stringify(msg.error)));
    else p.resolve(msg.result);
  }
};

ws.onerror = (event) => {
  console.error("WSERR", event.message || "error");
  process.exit(1);
};

ws.onopen = async () => {
  try {
    const report = await auditAll(send, {label: "cdp"});
    console.log(formatReport(report));
    console.log(`\n${report.failures.length} 个失败 / ${report.results.length} 个页面`);
    ws.close();
    process.exit(report.failures.length > 0 ? 1 : 0);
  } catch (error) {
    console.error("ERR", error.message);
    ws.close();
    process.exit(1);
  }
};
