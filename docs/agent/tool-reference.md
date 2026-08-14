# Agent 工具参考

工具分为只读和写入两组。内置对话循环可以自动运行只读工具；写入工具只生成待确认动作，并由宿主调用 `/lore-api/agent/execute`。

## 只读工具

| 工具 | 参数 | 返回 |
| --- | --- | --- |
| `list_projects` | 无 | 项目摘要列表 |
| `load_project` | `project_id` | 完整故事项目 |
| `export_project` | `project_id` | 完整故事项目 JSON |
| `list_books` | 无 | 书架列表 |
| `export_book` | `book_id` | 书籍与全部章节正文 |
| `get_llm_config` | 无 | 脱敏模型配置，不含 API Key |
| `get_server_status` | 无 | 服务、数据目录、项目/书籍数和 Vault 状态 |

只读工具不能通过 `/lore-api/agent/execute` 调用。外部 Agent 应使用 [HTTP 文档中的 GET 接口](http-api.md)。

## 项目写入

以下工具在修改已有项目之前自动生成项目快照。

| 工具 | 必需参数 | 可选/可编辑参数 | 风险 |
| --- | --- | --- | --- |
| `append_chapter` | `project_id` | `title`, `content` | 新增章节，非幂等 |
| `add_character` | `project_id` | `name`, `identity`, `role`, `age`, `stance`, `drive`, `fear`, `traits`, `abilities`, `weakness`, `secret`, `speech`, `appearance`, `background` | 新增人物，非幂等 |
| `update_character` | `project_id`，以及 `id` 或 `name` | 上述人物字段、`relationships`, `status`, `notes` | 按名称可能命中歧义对象 |
| `delete_character` | `project_id`，以及 `id` 或 `name` | 无 | 删除，破坏性 |
| `add_world_card` | `project_id` | `name`, `type`, `summary`, `details`, `significance`, `tags` | 新增设定，非幂等 |
| `update_world_card` | `project_id`，以及 `id` 或 `name` | `name`, `type`, `summary`, `details`, `significance`, `tags` | 按名称可能歧义 |
| `delete_world_card` | `project_id`，以及 `id` 或 `name` | 无 | 删除，破坏性 |
| `update_chapter` | `project_id`，以及 `chapter_id` 或现有 `title` | 新 `title`, `content` | 可能替换整章正文 |
| `delete_chapter` | `project_id`，以及 `chapter_id` 或 `title` | 无 | 删除，破坏性 |
| `update_project` | `project_id` | `name`, `genre`, `summary`, `global_guidance`, `chapter_turns` | 修改全局创作约束 |

优先使用稳定的 `id`，不要在存在同名对象时使用 `name` 或 `title` 定位。

## 书籍写入

| 工具 | 必需参数 | 可选参数 | 快照/风险 |
| --- | --- | --- | --- |
| `append_book_chapter` | `book_id` | `title`, `content` | 自动书籍快照；非幂等 |
| `merge_chapters` | `book_id`, `start_order`, `end_order` | `title` | 自动书籍快照；结构性且破坏性 |
| `import_txt` | `text` | `name`, `genre` | 新建书籍；不生成自动快照 |

`merge_chapters` 使用从 1 开始的连续顺序范围。执行前应向用户显示起止章节及合并后的标题。

## 项目创建

`create_project`

参数：`name`, `genre`, `summary`。该工具创建新项目，不生成“操作前快照”。重复请求会创建多个项目，失败或超时后不要盲目重试；先调用项目列表检查结果。

## 演化沙盘

| 工具 | 参数 | 说明 |
| --- | --- | --- |
| `evolution_start` | `project_id`, `project_name`, `genre`, `characters`, `world`; 可选 `map_nodes`, `map_edges`, `settings`, `seed` | 创建或重建演化状态 |
| `evolution_advance` | `project_id`; 可选 `choice_id` | 推进一回合 |
| `evolution_guidance` | `project_id`, `guidance` | 更新后续演化引导 |
| `evolution_reset` | `project_id` | 删除演化存档，破坏性 |

沙盘工具不纳入项目快照。`evolution_advance` 非幂等，同一个请求执行两次会前进两回合。

## 资料与设置

| 工具 | 参数 | 说明 |
| --- | --- | --- |
| `save_knowledge` | `title`, `content`; 可选 `tags` 数组 | 保存到 `story-workspace` 的实验性资料草稿，不会直接批准入库 |
| `update_llm_config` | 可选 `base_url`, `model`, `preset`, `level`, `reasoning_effort`, `temperature`, `top_p`, `max_tokens` | 修改非密钥模型配置；DeepSeek `level` 为 `fast` / `balanced` / `deep`，推理强度为 `low` / `high` / `max`，不能设置 API Key |

API Key 必须通过受控的设置流程配置。不要把密钥放进对话、附件或 Agent 工具参数。

## 自动快照范围

自动快照只覆盖：

```text
append_chapter, add/update/delete_character,
add/update/delete_world_card, update/delete_chapter,
update_project, append_book_chapter, merge_chapters
```

创建项目、导入书籍、沙盘、资料草稿和模型配置不在该集合中。宿主必须根据工具类别展示正确的恢复说明，不能统一宣称“所有 AI 操作都可回滚”。
