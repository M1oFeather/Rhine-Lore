/**
 * 一次性工具：把 styles.css 中 :root / [data-theme="dark"] 之外的
 * 硬编码十六进制颜色替换为语义令牌（var(--*)）。
 * 已令牌化的区域（文件开头的两个定义块）自动跳过。
 *
 * 用法：node scripts/tokenize-css.mjs
 */

import {readFileSync, writeFileSync} from "node:fs";
import {fileURLToPath} from "node:url";

const FILE = fileURLToPath(new URL("../ui/src/styles.css", import.meta.url));

const MAP = {
  "#f3f5f9": "--bg",
  "#f3f5f8": "--bg",
  "#f2f5f9": "--bg",
  "#f5f7fb": "--bg-soft",
  "#f4f7fb": "--bg-soft",
  "#f6f8fb": "--bg-soft",
  "#f6f9fc": "--bg-soft",
  "#f1f5f9": "--bg-soft",
  "#f0f4f8": "--bg-soft",
  "#f4f6f9": "--bg-soft",
  "#f7f9fc": "--bg-soft",
  "#f7fafc": "--bg-soft",
  "#eef4fc": "--bg-soft",
  "#f8fafc": "--panel-soft",
  "#f8faff": "--panel-hover",
  "#f8fbff": "--panel-hover",
  "#fbfdff": "--panel-subtle",
  "#fbfcfe": "--panel-subtle",
  "#fafbfd": "--panel-subtle",
  "#f7faff": "--panel-hover",
  "#f3f7ff": "--panel-active",
  "#eef2f7": "--chip-bg",
  "#edf0f3": "--chip-bg",
  "#edf1f5": "--chip-bg",
  "#e7ecf1": "--chip-bg",
  "#e8edf4": "--chip-bg",
  "#e8f0fa": "--blue-soft",
  "#eaf2ff": "--blue-soft",
  "#eaf3fe": "--blue-soft",
  "#edf4ff": "--blue-soft",
  "#e3f0fd": "--blue-soft",
  "#f2f8ff": "--blue-soft",
  "#f5f8ff": "--blue-soft",
  "#e7f0ff": "--blue-soft",
  "#eef4ff": "--blue-soft",
  "#dbeafe": "--blue-border",
  "#e3eaf2": "--border",
  "#e4e7ec": "--border",
  "#d5dce5": "--border-soft",
  "#c9d7e8": "--border-2",
  "#cbd5e1": "--border-2",
  "#cbd8ea": "--border-2",
  "#cdd9e7": "--border-2",
  "#c5d3e6": "--border-2",
  "#c6d2e2": "--border-2",
  "#b9c8dd": "--border-2",
  "#b8cfe8": "--border-3",
  "#c7d7f5": "--blue-border",
  "#b9c9e8": "--blue-border",
  "#b9ccf0": "--blue-border",
  "#b8d4f2": "--blue-border",
  "#c6d8ff": "--blue-border",
  "#9db4d9": "--blue-border-2",
  "#9dbbff": "--blue-border-2",
  "#93b7ff": "--blue-border-2",
  "#8bb3ff": "--blue-border-2",
  "#8ba6c8": "--muted-blue",
  "#60a5fa": "--blue-light",
  "#7dd3fc": "--blue-light-2",
  "#101828": "--text",
  "#151a22": "--text",
  "#1b212b": "--text",
  "#263c53": "--text-soft",
  "#33475c": "--text-mid",
  "#44566b": "--text-mid",
  "#2b4a6f": "--text-soft",
  "#1c2f45": "--text-soft",
  "#1f2933": "--text-soft",
  "#2c3644": "--text-soft",
  "#475467": "--muted-2",
  "#52606d": "--muted-2",
  "#6b7d90": "--muted-2",
  "#64748b": "--muted-2",
  "#7f8b99": "--muted",
  "#5b6b7c": "--muted-2",
  "#8a97a6": "--muted",
  "#8c98a8": "--muted",
  "#94a3b8": "--muted",
  "#9aa5b3": "--muted",
  "#aeb8c5": "--muted-2",
  "#c6cfda": "--muted-3",
  "#16324f": "--ink-strong",
  "#172554": "--ink-blue",
  "#25497a": "--ink-blue",
  "#1e4f9f": "--blue-deep",
  "#1d4ed8": "--blue-deep",
  "#1e40af": "--blue-deep",
  "#1f6feb": "--blue-link",
  "#2563eb": "--blue",
  "#3b6fb5": "--blue-link",
  "#4a78ad": "--blue-link",
  "#12b76a": "--green",
  "#24724c": "--green-deep",
  "#276749": "--green-deep",
  "#2e8b57": "--green-deep",
  "#067647": "--green-deep",
  "#0f766e": "--teal",
  "#0f7b75": "--teal",
  "#3b7772": "--teal",
  "#a7d7bc": "--green-border",
  "#b8e2ca": "--green-border",
  "#bfe3cd": "--green-border",
  "#bfe7c9": "--green-border",
  "#e0f2e9": "--green-soft",
  "#e0f7f5": "--teal-soft",
  "#e4f0ef": "--teal-soft",
  "#e5f7ec": "--green-soft",
  "#ecfdf3": "--green-soft",
  "#edf9f2": "--green-soft",
  "#f1fbf5": "--green-soft",
  "#f0fff4": "--green-soft",
  "#b7791f": "--amber",
  "#b45309": "--amber-deep",
  "#c0691d": "--amber",
  "#d97706": "--amber",
  "#9a6a12": "--amber-deep",
  "#7a5b1e": "--amber-deep",
  "#6b5c33": "--amber-ink",
  "#4a3f2f": "--amber-ink",
  "#ecd9b0": "--amber-border",
  "#e2d5b8": "--amber-border",
  "#e4dcc4": "--amber-border",
  "#f9f3e3": "--amber-soft",
  "#fdf0df": "--amber-soft",
  "#fdf3e3": "--amber-soft",
  "#fffaf0": "--amber-soft",
  "#fffefa": "--amber-soft",
  "#fffdf8": "--amber-soft",
  "#fef3c7": "--amber-soft",
  "#f3ead2": "--amber-soft",
  "#f4f1e8": "--amber-soft",
  "#f04438": "--red",
  "#c03030": "--red-deep",
  "#a93a32": "--red-deep",
  "#8f3d38": "--red-deep",
  "#fde8e8": "--red-soft",
  "#fdeaea": "--red-soft",
  "#fff5f4": "--red-soft",
  "#fbe4ee": "--pink-soft",
  "#a13563": "--pink-deep",
  "#f0c2bd": "--red-border",
  "#f2c9c9": "--red-border",
  "#7a3fc0": "--purple",
  "#7c3aed": "--purple",
  "#f0e7fb": "--purple-soft",
  "#0f1722": "--sidebar",
  "#121823": "--sidebar-grad",
};

const norm = (hex) => {
  let value = hex.toLowerCase();
  if (value.length === 4) {
    value = `#${value[1]}${value[1]}${value[2]}${value[2]}${value[3]}${value[3]}`;
  }
  return value;
};

const source = readFileSync(FILE, "utf8");
const lines = source.split("\n");

// 跳过文件开头的 :root 与 [data-theme="dark"] 定义块
let start = 0;
let braceDepth = 0;
let defined = 0;
for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  if (line.includes("{")) braceDepth += 1;
  if (line.includes("}")) braceDepth -= 1;
  if (braceDepth === 0 && (line.includes(":root") || line.includes('[data-theme="dark"]'))) {
    start = i;
    defined += 1;
  }
  if (defined >= 2) {
    break;
  }
}

let replacements = 0;
const unmapped = new Set();
const output = [];
let inDefined = false;
let defDepth = 0;

for (let i = 0; i < lines.length; i++) {
  const raw = lines[i];
  if (!inDefined && (raw.includes(":root") || raw.includes('[data-theme="dark"]'))) {
    inDefined = true;
    defDepth = 0;
  }
  if (inDefined) {
    defDepth += (raw.match(/\{/g) || []).length - (raw.match(/\}/g) || []).length;
    output.push(raw);
    if (defDepth <= 0) inDefined = false;
    continue;
  }

  let line = raw;
  const colorMatches = line.matchAll(/#[0-9a-fA-F]{3,8}\b/g);
  const matches = [...colorMatches];
  if (matches.length === 0) {
    output.push(line);
    continue;
  }
  const property = (line.match(/^\s*([a-z-]+)\s*:/) || [])[1] || "";
  const isTextLike = property.startsWith("color") || property.startsWith("fill") || property.startsWith("border");
  for (const match of matches) {
    const key = norm(match[0]);
    let token;
    if (key === "#ffffff" || key === "#fff") {
      token = isTextLike ? "--on-accent" : "--panel";
    } else if (key === "#eef3f8") {
      token = property.startsWith("color") ? "--on-dark" : "--bg-soft";
    } else {
      token = MAP[key];
    }
    if (!token) {
      unmapped.add(match[0]);
      continue;
    }
    line = line.replace(match[0], `var(${token})`);
    replacements += 1;
  }
  output.push(line);
}

writeFileSync(FILE, output.join("\n"), "utf8");
console.log(`替换 ${replacements} 处颜色`);
if (unmapped.size > 0) {
  console.log(`未映射: ${[...unmapped].join(", ")}`);
  process.exitCode = 1;
} else {
  console.log("全部映射完成");
}
