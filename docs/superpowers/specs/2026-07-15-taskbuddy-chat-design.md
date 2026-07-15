# TaskBuddy 对话智能体设计规格

## 1. 目标与范围

本项目实现考题要求的内部“工作事项助手”：用户能够创建并继续会话，以流式方式获得结构化回答，并能明确识别发送、生成、完成、取消、失败和重试状态。默认 Mock 模式无需密钥即可完成全部核心验收；真实模型是通过相同内部协议接入的可选能力。

第一版只实现一个工作事项助手。不加入多智能体编排、工具调用、身份认证、知识检索、附件、语音和云部署。Spring AI Alibaba Studio、assistant-ui 和 OpenAI Agents SDK 只作为设计与实现参考，不作为复制项目的来源。

## 2. 技术方向

- 前端：Next.js、React、严格模式 TypeScript。
- 后端：Python、FastAPI、Pydantic。
- 持久化：SQLite，通过仓储接口隔离。
- 传输：POST 请求返回具名 SSE 事件；资源管理使用普通 REST。
- 模型：默认 `MockModelProvider`；可选 `OpenAIAgentsProvider`。
- 测试：pytest/httpx、Vitest/Testing Library、Playwright。

PostgreSQL 不作为默认依赖，因为本地单用户评审不需要独立数据库服务。Docker 可以作为补充运行方式，但不能成为唯一运行方式。

## 3. 总体架构

```text
Next.js 对话页面
        │ REST / SSE / cancel
        ▼
FastAPI HTTP/SSE 路由
        ▼
ConversationService
   ├── PromptBuilder
   ├── OutputValidator
   ├── ConversationRepository ── SQLite
   └── ModelProvider
          ├── MockModelProvider
          └── OpenAIAgentsProvider ── openai-agents
```

路由只负责请求校验、`requestId`、事件编码和断连检测。`ConversationService` 拥有发送、生成、完成、失败、取消和重试的生命周期。Prompt 构建、输出校验、Provider 和数据库写入不得堆叠在路由函数中。

业务代码只依赖项目自有的 `ModelProvider` 和 `ModelEvent`。`OpenAIAgentsProvider` 通过正常安装的官方 PyPI 包接入，并负责输入、事件、异常和取消语义的转换；不得复制 Agents SDK 源码，也不得让 SDK 类型进入路由、应用服务、数据库或前端。

## 4. 数据模型与事实归属

### 4.1 Conversation

- `id`
- `agent_id`
- `title`
- `created_at`
- `updated_at`

### 4.2 Message

- `id`
- `conversation_id`
- `role`：`user | assistant`
- `content`
- `status`：`pending | streaming | completed | cancelled | failed`
- `in_reply_to_message_id`：助手消息对应的用户消息
- `retry_of_message_id`：重试时指向上一条失败或取消的助手消息
- `error_code`
- `client_message_id`：客户端发送幂等键，仅用户消息使用
- `created_at`
- `updated_at`

服务端数据库是会话和消息的唯一持久化事实来源。客户端可以乐观显示用户消息，但必须使用服务端 `message.accepted` 返回的 ID 和后续历史查询完成对账。

助手消息本身代表一次生成尝试，不另建重复的持久化生成状态。运行中的 `asyncio.Task` 和取消事件只存在于进程内，并按助手消息 ID 注册。

## 5. 生成、取消与重试

正常路径为：保存用户消息并创建 `pending` 助手消息，注册运行任务后转为 `streaming`，最终输出校验通过后转为 `completed`。

显式取消和浏览器断连使用同一服务端取消流程：原子记录取消意图、设置取消事件、取消 `asyncio.Task`、停止 Provider，最后把助手消息写为 `cancelled`。重复取消必须幂等。

`completed`、`cancelled` 和 `failed` 均为终态。数据库使用带当前状态条件的更新，防止后到的完成、失败或取消事件覆盖已经写入的终态。每个增量写入前检查消息仍为当前 `streaming` 尝试；取消后的迟到增量直接丢弃并记录计数，不写入消息。

服务启动时扫描遗留的 `pending` 和 `streaming` 消息，将其恢复为带稳定错误码的可重试失败，避免重启后永久显示生成中。

重试不复制用户消息，而是创建新的助手消息；该消息通过 `in_reply_to_message_id` 关联原用户消息，并通过 `retry_of_message_id` 关联上一生成尝试。

## 6. Prompt 信任边界

`PromptBuilder` 接收结构化 `PromptPackage`，至少包含：

- `system`：版本化的身份、目标、安全约束和输出契约，来自服务端受控配置；
- `history`：保留原角色的历史消息，按明确预算裁剪；
- `user`：当前原始用户输入，始终作为独立用户消息；
- `external_context`：本题默认为空，未来只作为带来源的数据证据；
- `output_schema`：服务端定义的 Pydantic Schema；
- `prompt_version`：可安全记录的版本标识。

系统规则、历史、当前用户输入和外部资料不得简单插值成一段同等级指令。历史内容和用户输入均不受信任，不能覆盖系统规则。日志只记录 Prompt 版本、输入长度和必要标识，不记录完整系统提示词或完整对话。

## 7. 结构化输出

`WorkAssistantResponse` 包含：

- `mode`：`answer | clarification | refusal`
- `conclusion`
- `risks[]`
- `open_questions[]`
- `next_steps[]`
- `notice`

模型原始输出先通过 Pydantic 结构校验，再进行模式与字段的业务一致性检查，只有规范化结果可以持久化并交给 UI 渲染。真实 Provider 最多允许一次受控格式修复；仍失败时保存 `failed` 和 `INVALID_MODEL_OUTPUT`，不得把原始 JSON 直接展示给用户。

三个固定行为场景为：发布风险请求返回包含结论、风险项、待确认项和下一步的 `answer`；“帮我处理一下”返回必要澄清问题且不编造执行；索取系统提示词和 API Key 时返回 `refusal`，不泄露信息并保持任务边界。

## 8. API 与 SSE 契约

```text
POST /api/conversations
GET  /api/conversations
GET  /api/conversations/{conversationId}/messages
POST /api/conversations/{conversationId}/messages
POST /api/conversations/{conversationId}/messages/{assistantMessageId}/cancel
POST /api/conversations/{conversationId}/messages/{assistantMessageId}/retry
GET  /health
```

发送请求包含 `content`、固定的 `agentId` 和浏览器生成的 `clientMessageId`。相同 `clientMessageId` 在同一会话内返回同一已创建消息，不重复保存。一个会话同一时间只允许一个活动生成，冲突返回 `409 CONVERSATION_BUSY`；不同会话可以并行生成。

SSE 事件包括：

- `message.accepted`：`requestId`、用户消息 ID、助手消息 ID；
- `message.delta`：助手消息 ID、单调递增 `sequence`、文本增量；
- `message.completed`：助手消息 ID、终态和规范化内容；
- `message.cancelled`：助手消息 ID 和终态；
- `message.error`：助手消息 ID、稳定错误码、用户可读消息、`requestId` 和 `retryable`；
- `heartbeat`：只维护连接，不进入消息和数据库。

流开始前的 HTTP 错误统一返回 `{ error: { code, message, requestId, details? } }`。流开始后的错误先把数据库消息写为 `failed`，再发送 `message.error` 并关闭 SSE。Provider 原始异常、堆栈、Prompt 和密钥不得进入响应。

## 9. 前端设计

1440px 下使用会话侧栏和对话主区；375px 下侧栏变为抽屉，主区保持智能体标题、消息列表和固定输入区。智能体说明显示名称、目标、输出能力和“不执行真实操作”等边界，但不显示完整系统提示词。

主要边界为：

- `AppShell`：组合 `ConversationSidebar`、`AgentHeader` 和 `ChatPanel`；
- `MessageList`：自动滚动并按角色与结构化模式选择 `MessageCard`；
- `Composer`：空输入校验、Enter 发送、Shift+Enter 换行以及发送/停止互斥；
- `useConversationStream`：使用 `fetch` 和 `AbortController` 消费 SSE，按 `sequence` 合并增量，并在终态后重新读取历史完成对账。

发送期间禁止同一会话再次提交。UI 必须区分发送中、生成中、完成、取消、失败和可重试状态，并提供首次使用、网络异常、服务错误和空输入反馈。全部交互控件具备键盘可达性和明确无障碍名称。

## 10. 安全与配置

默认 `MODEL_PROVIDER=mock`。真实 `OPENAI_API_KEY` 只能由 FastAPI 服务端从本地环境读取，不得使用任何 `NEXT_PUBLIC_` 密钥变量，也不得由浏览器传递。

本项目的可选真实 Provider 使用 OpenAI 兼容的 DeepSeek Chat Completions 接口，配置项为：

- `DEEPSEEK_CODE_API_KEY`：必需的服务端密钥；兼容读取 `DEEPSEEK_API_KEY` 作为次级名称；
- `DEEPSEEK_BASE_URL`：默认公开 Base URL `https://api.deepseek.com`，允许在本地环境覆盖；
- `DEEPSEEK_MODEL`：默认 `deepseek-v4-flash`，允许在本地环境覆盖；
- `MODEL_PROVIDER`：只有显式设为 `deepseek` 时才创建真实 Provider。

`DEEPSEEK_CODE_API_KEY` 只是可公开提交的环境变量名称，环境变量中保存的实际值才是密钥。Base URL 和模型名默认可以出现在源码、`.env.example` 和 README 中，因为它们用于复现公开接口配置；若 Base URL 指向公司内网、私有网关或包含租户标识，则按敏感信息处理，不得提交。

`OpenAIAgentsProvider` 使用 `AsyncOpenAI(api_key=..., base_url=...)` 和 Agents SDK 的 `OpenAIChatCompletionsModel`。传给 SDK 的是 Base URL，不是已经带 `/chat/completions` 的完整 endpoint，避免 SDK 重复拼接路径。真实密钥使用 `SecretStr` 保存，禁止出现在对象字符串、异常、追踪和测试快照中。

仓库只提交没有真实值的 `.env.example`；`.env`、虚拟环境、本地数据库、构建产物和视觉讨论文件均由 `.gitignore` 排除。结构化日志只记录 `requestId`、会话/消息 ID、Provider 名称、状态、耗时、错误码和必要长度信息。

提交前及 CI 中执行 Gitleaks 和文本规则扫描，并覆盖当前工作树与 Git 历史。如果密钥曾进入历史，必须先撤销轮换，再使用 `git filter-repo` 清理并重新扫描；删除当前文件不能视为完成处理。

## 11. 错误恢复

- 空输入不创建消息并返回 422；
- 会话不存在返回 `CONVERSATION_NOT_FOUND`；
- 同会话并发生成返回 `CONVERSATION_BUSY`；
- Provider 不可用时写入 `failed` 并允许重试；
- 输出非法时返回 `INVALID_MODEL_OUTPUT`，不展示原始 JSON；
- 取消后保留已经生成且已接受的部分内容，并明确标为已取消；
- 网络失败使用 `clientMessageId` 对账，不盲目重复发送；
- 重启遗留生成恢复为可重试失败。

## 12. 测试策略

后端单元测试覆盖 Prompt 分层、三个固定场景、结构化校验、Mock Provider 的成功/异常/取消/非法输出、状态转换、终态竞争和重试关系。

后端接口测试覆盖会话 API、SSE 顺序、显式与重复取消、断连取消、同会话并发、`clientMessageId` 幂等、SQLite 重启持久化和统一错误结构。

前端组件测试覆盖键盘输入、空输入、发送/停止/重试、增量合并和重复序号、结构化回答、会话切换、自动滚动及关键无障碍属性。

Playwright 覆盖无密钥首次运行、Mock 流式完成、中途停止后刷新、Provider 失败后重试，以及 375px/1440px 的交互与截图。

## 13. 交付与审计

根目录提供统一的安装、开发启动、格式化检查、Lint、类型检查、测试、端到端、生产构建和密钥扫描命令。README 必须让评审者从全新克隆开始复现，不要求预装 PostgreSQL 或拥有模型密钥。

除 README 外，交付 `docs/prompt-design.md`、`docs/ai-collaboration.md` 和 `docs/redundancy-audit.md`。AI 协作文档记录真实使用的 Codex 与 Claude Code Prompt、采纳与拒绝的建议、人工决策和验证证据。冗余审计逐项记录检查方法、发现、处理结果和证据位置。

Git 历史按有意义的垂直切片提交，不伪造提交时间，也不把纯格式改动包装成功能提交。

## 14. 已知取舍

- SQLite 满足本地单用户演示，不面向高并发生产负载；仓储接口保留未来迁移能力。
- 单会话串行生成减少消息串台和取消竞争；不同会话仍可并行。
- OpenAI Agents SDK 只用于可选真实 Provider，默认验收不依赖外部服务。
- DeepSeek 模型名和公开 Base URL 是可配置默认值，不是秘密；密钥值永不进入仓库、浏览器、日志、截图和测试证据。
- 第一版不做断线续传；断连会取消当前生成，刷新后通过持久化历史恢复终态。
