# Rhine-Lore 动效库

版本：2026-08-12 · 对应验收标准 I（动画与动效）

## 时长与缓动

| 场景 | 时长 | 缓动 |
| --- | --- | --- |
| 页面切换（淡入 + 轻微上移） | 140–180ms | ease-out（`page-in`） |
| 按钮按压反馈 | ≤ 100ms 出现，过渡 160–220ms | ease |
| 卡片 hover（边框/阴影/位移） | 150–170ms | ease |
| 抽屉 / 弹层 | ≤ 240ms | ease-out |
| 三点思考 | 1.2s 循环 | steps（`chat-blink`） |
| 流式光标 | 0.9s 闪烁 | steps（`stream-cursor-blink`） |

原则：动画只用 `transform` / `opacity`，不触发布局抖动。

## 关键帧

- `page-in`：`opacity 0 → 1` + `translateY(6px → 0)`，挂在 `.activity-panel`；
- `chat-blink`：三点 0.25→1 透明度脉冲；
- `stream-cursor-blink`：流式输出光标闪烁。

## 无障碍

`prefers-reduced-motion: reduce` 时关闭非必要动画（页面切换、光标闪烁等）。

## 流式输出（打字机）

1. 后端 SSE：`start → delta（6 字符/12ms）→ done`；
2. 客户端按 `max(3, len/150)` 字符/帧匀速揭示，防止快速响应跳过中间态；
3. 流式中显示 `.streaming-text` + `.stream-cursor`，完成后提交完整消息；
4. 无 API Key 时回落离线草稿，不阻塞。

## 验收

- 常规模式与 reduced-motion 各验一次；
- 页面切换不闪烁、无白屏；
- 滚动审计保持 outer=0（见 `scroll-audit.md`）。
