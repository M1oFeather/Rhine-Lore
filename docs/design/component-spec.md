# Rhine-Lore 组件规范

版本：2026-08-12 · 对应验收标准 F（一致性）

## 颜色令牌（styles.css `:root` / `[data-theme="dark"]`）

所有 UI 颜色必须来自令牌，禁止硬编码十六进制（`scripts/tokenize-css.mjs` 已全量迁移）。

| 语义 | 令牌 | 用途 |
| --- | --- | --- |
| 背景 | `--bg` / `--bg-soft` / `--chip-bg` | 页面底、渐变段、标签底色 |
| 面板 | `--panel` / `--panel-soft` / `--panel-subtle` / `--panel-hover` / `--panel-active` | 卡片、悬浮、选中 |
| 文字 | `--text` / `--text-soft` / `--text-mid` / `--muted` / `--muted-2` / `--muted-3` | 正文→辅助→禁用 |
| 强调文字 | `--ink-strong` / `--ink-blue` | 卡片标题、AI 条目标题 |
| 线 | `--border` / `--border-soft` / `--border-2` / `--border-3` | 边框、分隔 |
| 品牌色 | `--blue` / `--blue-deep` / `--blue-link` / `--blue-soft` / `--blue-border` | 主操作、链接、浅底 |
| 状态色 | `--green*` / `--amber*` / `--red*` / `--purple*` / `--teal*` | 成功/警告/错误/特殊 |
| 深色面 | `--sidebar` / `--sidebar-grad` / `--on-dark` / `--on-accent` | 侧边栏与彩色底上的文字 |
| 浮动 | `--topbar-bg` / `--composer-bg` / `--composer-border` | 半透明顶栏与输入区 |
| 阴影 | `--shadow` / `--shadow-raised` | 卡片、弹层 |

## 尺寸与圆角

- 圆角：`--radius: 8px`（小件）、`--radius-md: 12px`（卡片）、`--radius-lg: 18px`（大卡/弹层）；
- 触控：主操作 ≥ 44px，次操作 ≥ 36px；
- 固定页内容区：`padding 18px`（桌面）/ `12px 12px 88px`（手机，底部避让）。

## 通用组件

- **卡片** `el-card`：`shadow="never"` + 圆角 `--radius-lg`，内容用 `card-header`（标题 + 副说明 + 操作）；
- **空态** `EmptyState`：图标 + 标题 + 说明 + 主/次 CTA，禁止裸文字空态；
- **抽屉** `el-drawer`：编辑类从底部弹出（82%–88%），目录/历史右侧弹出；保存成功必须 toast；
- **Toast**：统一 `toastSuccess`，写操作成功/失败/进行中三态齐全；
- **状态面板**：固定高度标签页 + 白名单内滚（演化状态卡为范本）；
- **滚动容器**：页面本身 outer=0，仅白名单（正文/小说阅读/书架阅读、演化时间线、状态卡）内滚；隐藏裁切视为缺陷；
- **图标**：`GameIcon` 只允许 `gameIconPack.ts` 中存在的名字，缺名会导致渲染崩溃。

## 侧边栏

- 展开态：图标 + 主标签 + 一句话副标题；折叠态：仅图标 + tooltip；
- 当前页必须 `aria-current="page"`；
- 不放置品牌块；页脚只放状态点与版本。

## 新增页面清单

1. 用 `section.activity-panel` 包裹；
2. 首屏只放 1–3 个主操作，其余折叠；
3. 空态、toast、抽屉齐备后提交。

## 主题

- 跟随 `data-theme="dark"` 自动切换；新增颜色必须同时补浅/深两值；
- 设置页「外观主题」提供 浅色/深色/跟随系统；
- 阅读主题（白/米黄/夜间）是独立的阅读令牌覆盖，不与应用主题混用。
