# Agent 接入总览

Rhine-Lore 的 Agent 接口面向两类宿主：Lore 自己的对话页，以及运行在同一台设备或可信局域网中的外部 Agent。当前接口是本地产品协议，不是可直接暴露到公网的多租户 API。

## 接入模型

```text
用户消息
  |
  v
POST /lore-api/llm/chat 或 /chat/stream
  |
  +-- 只读工具：对话循环内自动执行，结果继续交给模型
  |
  +-- 写工具：返回 pending action，不执行
                  |
                  v
          宿主显示工具、目标与参数
                  |
             用户明确确认
                  |
                  v
       POST /lore-api/agent/execute
                  |
          自动快照（适用时）
                  |
             执行并返回结果
```

!!! danger "确认不是服务端授权"
    当前 `/lore-api/agent/execute` 不验证确认令牌，也没有用户鉴权。所谓“已确认”是宿主必须遵守的交互协议，而不是后端当前能够证明的安全事实。接入前必须阅读 [安全与确认](security.md)。

## 最小对话请求

先在 Lore 设置中配置 OpenAI 兼容模型与 API Key，然后请求：

```bash
curl -X POST http://127.0.0.1:8786/lore-api/llm/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "列出我的项目，并概括最近的故事。"}
    ],
    "attachments": []
  }'
```

典型只读响应：

```json
{
  "answer": "你目前有两个项目……",
  "model": "configured-model",
  "provider": "openai-compatible",
  "actions": [
    {
      "tool": "list_projects",
      "args": {},
      "result": {"projects": []}
    }
  ]
}
```

当模型提出写操作时，动作只会作为待确认项返回：

```json
{
  "answer": "我可以把这段内容追加为新章节。",
  "actions": [
    {
      "tool": "append_chapter",
      "args": {
        "project_id": "project-123",
        "title": "雨夜来客",
        "content": "……"
      },
      "pending": true,
      "result": null
    }
  ]
}
```

宿主确认后再执行：

```bash
curl -X POST http://127.0.0.1:8786/lore-api/agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "append_chapter",
    "args": {
      "project_id": "project-123",
      "title": "雨夜来客",
      "content": "……"
    }
  }'
```

## 宿主必须实现

1. 保留会话中返回的原始 `tool` 和 `args`，不要从自然语言回答重新推断参数。
2. 把动作目标、影响范围和正文预览显示给用户。
3. 每个写操作单独确认；删除和结构变更使用更强的二次确认。
4. 只在确认后调用 `/lore-api/agent/execute`。
5. 保存响应中的 `snapshot`、`tool` 和结果，提供可见的恢复路径。
6. 执行后重新读取目标实体，不以模型回答作为最终状态。
7. 不自动重试非幂等写工具。

## 当前协议状态

- 工具由系统提示中的文本列表定义，还没有机器可读 JSON Schema。
- 模型通过输出单行 JSON 请求工具，后端从文本中提取；不是模型提供商的原生 structured tool calling。
- 单轮最多进行五次模型调用；只读工具结果最多回填约 1200 个 JSON 字符。
- 流式端点先完成模型/工具循环，再以 SSE 分片返回文本，因此目前是界面打字机流，不是上游模型实时 token 流。
- `/lore-api/agent/execute` 只接受写工具。外部 Agent 读取数据应使用常规 REST GET 接口。

接口细节见 [HTTP 与流式协议](http-api.md)，完整参数见 [工具参考](tool-reference.md)。
