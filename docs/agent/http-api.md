# HTTP 与流式协议

## 基础约定

- 默认地址：`http://127.0.0.1:8786`。
- 请求和响应使用 UTF-8 JSON，流式对话除外。
- 错误响应统一包含 `error` 字符串，但当前没有稳定的机器错误码。
- 当前 API 未版本化；接入方应固定兼容的 Rhine-Lore 版本。

## 普通对话

`POST /lore-api/llm/chat`

请求：

```json
{
  "messages": [
    {"role": "user", "content": "检查当前故事的人物动机。"}
  ],
  "attachments": [
    {
      "name": "第三章.txt",
      "kind": "txt",
      "text": "章节正文……"
    }
  ]
}
```

字段：

| 字段 | 必需 | 说明 |
| --- | --- | --- |
| `messages` | 是 | 非空数组；元素使用 `role` 与 `content` |
| `attachments` | 否 | 附件数组；系统提示当前使用前五个 |
| `attachments[].name` | 建议 | 显示名称 |
| `attachments[].kind` | 建议 | 前端使用 `txt`、`project`、`knowledge` |
| `attachments[].text` | 是 | 注入模型上下文的文本 |

成功返回：

```json
{
  "answer": "……",
  "model": "configured-model",
  "provider": "openai-compatible",
  "actions": []
}
```

常见错误：

| HTTP | 场景 |
| --- | --- |
| `400` | `messages` 为空、没有配置 API Key、请求参数错误 |
| `502` | 模型端连接、超时或响应格式错误 |

## SSE 对话

`POST /lore-api/llm/chat/stream`

请求体与普通对话相同。响应类型为 `text/event-stream; charset=utf-8`。每帧只有 `data:` 行，客户端应解析 JSON 内的 `type`，不要依赖 SSE `event:` 字段。

事件顺序：

```text
start -> delta ... -> done
```

```text
data: {"type":"start","model":"configured-model","provider":"openai-compatible"}

data: {"type":"delta","text":"第一段"}

data: {"type":"done","answer":"第一段……","actions":[]}
```

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| `start` | `model`, `provider` | 输出开始 |
| `delta` | `text` | 文本片段 |
| `done` | `answer`, `actions` | 完整答案与工具动作 |

当前服务端会先等待完整模型结果，再按固定字符片段发送 `delta`。调用方仍应处理网络中断，并以 `done.answer` 作为最终文本。

## 执行确认后的动作

`POST /lore-api/agent/execute`

```json
{
  "tool": "update_character",
  "args": {
    "project_id": "project-123",
    "name": "林岚",
    "drive": "找出失踪档案的来源"
  }
}
```

成功响应：

```json
{
  "ok": true,
  "tool": "update_character",
  "result": {"project": {}},
  "snapshot": {
    "id": "version-id",
    "kind": "project",
    "entity_id": "project-123"
  }
}
```

`snapshot` 可能为 `null`：新建、导入、演化和资料草稿等工具不在项目/书籍自动快照集合中。不要把 `snapshot: null` 当作执行失败。

| HTTP | 场景 |
| --- | --- |
| `200` | 工具执行成功 |
| `400` | 不是允许的写工具、参数转换失败或业务校验失败 |
| `404` | 项目、书籍、章节、人物或设定不存在 |

错误示例：

```json
{"error": "只允许执行已确认的写操作"}
```

## 读取上下文

外部 Agent 可使用以下只读 REST 接口准备上下文：

| 方法与路径 | 用途 |
| --- | --- |
| `GET /lore-api/projects` | 项目摘要列表 |
| `GET /lore-api/projects/{project_id}` | 完整项目 |
| `GET /lore-api/books` | 书架列表 |
| `GET /lore-api/books/{book_id}` | 书籍元数据与章节索引 |
| `GET /lore-api/books/{book_id}/chapters/{chapter_id}` | 单章正文 |
| `GET /lore-api/books/{book_id}/branches?chapter_id=...` | 分支列表 |
| `GET /lore-api/books/{book_id}/branches/{branch_id}/path` | 分支路径 |
| `GET /lore-api/books/{book_id}/analysis/status` | 长篇分析状态 |
| `GET /lore-api/versions?kind=project&entity_id=...` | 项目版本 |
| `GET /lore-api/versions?kind=book&entity_id=...` | 书籍版本 |
| `GET /lore-api/vault/status` | Vault 连接状态 |
| `GET /lore-api/llm/config` | 已脱敏模型配置 |

这些接口目前与前端共用，没有稳定的公开响应 Schema。接入方应做字段缺失容错，但不要悄悄吞掉类型错误。

## 版本恢复

读取版本：

```http
GET /lore-api/versions?kind=project&entity_id=project-123
```

恢复版本：

```json
POST /lore-api/versions/restore
{
  "kind": "project",
  "entity_id": "project-123",
  "version_id": "version-id"
}
```

恢复前会再创建当前状态快照。宿主仍应提示恢复会替换当前实体，并在操作完成后重新读取数据。
