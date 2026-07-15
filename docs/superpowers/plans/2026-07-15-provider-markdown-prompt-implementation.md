# Provider、Markdown 与 Prompt 改进实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现按会话选择 Provider 的真实按钮、安全 Markdown、首条消息标题和基于语义的 Prompt 行为。

**Architecture:** FastAPI 通过 Provider Registry 暴露公开元数据，并按会话持久化的 `providerId` 选择统一适配器；Next.js 在创建会话时选择 Provider，已有会话只显示不可变来源。模型流直接传输自由 Markdown，前端使用成熟组件渲染，不增加 JSON 信封或板块解析器。

**Tech Stack:** Python 3.12、FastAPI、SQLAlchemy、SQLite、OpenAI Agents SDK、Next.js 15、React 19、TypeScript、react-markdown、remark-gfm。

**验证约定:** 按用户要求，Codex 不运行测试命令。每个任务只把操作步骤和预期结果追加到 `docs/manual-test-checklist.md`，实际结果由用户填写；不得把“待执行”描述成“通过”。

---

## 文件结构

- `apps/api/app/providers/registry.py`：Provider 注册、公开元数据与按 ID 查找。
- `apps/api/app/providers/openai_compatible.py`：通用 OpenAI-compatible Agents SDK 适配器。
- `apps/api/app/config.py`：通用模型环境变量。
- `apps/api/app/repositories/models.py`、`conversations.py`：会话 Provider、标题和更新时间事实。
- `apps/api/app/repositories/database.py`：SQLite 向后兼容迁移。
- `apps/api/app/api/routes/providers.py`：只读公开 Provider 列表。
- `apps/api/app/api/routes/conversations.py`：创建会话时校验并保存 Provider。
- `apps/web/src/features/providers/`：Provider 类型与 API 客户端。
- `apps/web/src/components/chat/provider-picker.tsx`：新会话 Provider 选择。
- `apps/web/src/components/chat/markdown-text.tsx`：安全 Markdown 渲染边界。
- `apps/web/src/components/chat/agent-header.tsx`：显示当前 Provider 并触发新会话选择。
- `apps/web/src/components/chat/chat-app.tsx`：Provider 状态、新建会话和标题刷新协调。
- `apps/api/app/prompt/system.md`、`validator.py`、`providers/mock.py`：语义场景与最低必要结构约束。
- `.env.example`、`README.md`：通用真实模型配置和切换说明。

### Task 1：建立通用 Provider Registry 和公开列表

**Files:**
- Create: `apps/api/app/providers/registry.py`
- Create: `apps/api/app/providers/openai_compatible.py`
- Create: `apps/api/app/api/routes/providers.py`
- Modify: `apps/api/app/config.py`
- Modify: `apps/api/app/main.py`
- Modify: `.env.example`
- Modify: `docs/manual-test-checklist.md`

- [ ] **Step 1：把 DeepSeek 专名配置替换为通用配置**

`Settings` 使用 `model_api_key: SecretStr | None`、`model_base_url`、`model_name` 和 `model_display_name`，环境变量分别为 `MODEL_API_KEY`、`MODEL_BASE_URL`、`MODEL_NAME`、`MODEL_DISPLAY_NAME`。`MODEL_PROVIDER` 只控制未显式选择时的默认 ID，不把供应商名称写进字段名。

- [ ] **Step 2：迁移真实适配器名称与职责**

将 `OpenAIAgentsProvider` 移到 `openai_compatible.py`，Provider ID 固定为 `openai-compatible`，显示名称来自设置；SDK 仍接收服务端的 Key、Base URL 和模型名。删除生产代码对 `DEEPSEEK_*` 的读取。

- [ ] **Step 3：实现 Registry**

Registry 始终注册 `mock`。当 `MODEL_API_KEY` 非空时注册可用的 `openai-compatible` 实例；为空时保留不可用的公开元数据。提供 `list_public()` 和 `require_available(provider_id)`，后者对未知和未配置状态返回不同领域异常。

- [ ] **Step 4：新增公开 API**

`GET /api/providers` 返回：

```json
[
  {"id":"mock","displayName":"Mock","modelName":"deterministic","available":true},
  {"id":"openai-compatible","displayName":"DeepSeek","modelName":"deepseek-v4-flash","available":true}
]
```

响应不得包含 Key、Base URL、配置对象或内部异常。应用启动时把 Registry 放入 `app.state.provider_registry`。

- [ ] **Step 5：同步环境示例和人工验收事项**

`.env.example` 完整列出五个通用变量，密钥值为空；人工清单追加 Provider 列表响应、未配置禁用和浏览器无密钥检查。

- [ ] **Step 6：提交**

```text
feat: expose configurable provider registry
```

### Task 2：将 Provider 固定到会话并驱动真实选择按钮

**Files:**
- Modify: `apps/api/app/domain/messages.py`
- Modify: `apps/api/app/repositories/models.py`
- Modify: `apps/api/app/repositories/database.py`
- Modify: `apps/api/app/repositories/conversations.py`
- Modify: `apps/api/app/api/routes/conversations.py`
- Modify: `apps/api/app/application/conversations.py`
- Create: `apps/web/src/features/providers/api.ts`
- Create: `apps/web/src/features/providers/types.ts`
- Create: `apps/web/src/components/chat/provider-picker.tsx`
- Modify: `apps/web/src/components/chat/agent-header.tsx`
- Modify: `apps/web/src/components/chat/composer.tsx`
- Modify: `apps/web/src/components/chat/chat-app.tsx`
- Modify: `apps/web/src/features/conversations/types.ts`
- Modify: `apps/web/src/features/conversations/api.ts`
- Modify: `docs/manual-test-checklist.md`

- [ ] **Step 1：持久化会话 Provider**

`Conversation`、`ConversationRow` 和序列化响应新增 `provider_id/providerId`。数据库启动迁移使用 SQLite `PRAGMA table_info(conversations)` 检查列；缺失时添加 `provider_id VARCHAR(80) NOT NULL DEFAULT 'mock'`，使旧数据库可继续读取。

- [ ] **Step 2：创建会话时校验选择**

`CreateConversationRequest` 接收 `providerId`，默认 `mock`。路由通过 Registry 校验可用性后再保存。发送与重试从会话读取 `provider_id` 并取得对应适配器，不再使用全局单实例 Provider。

- [ ] **Step 3：实现 Provider Picker**

Picker 从 `/api/providers` 加载数据；可用项可选，不可用项显示“未配置”并禁用。点击右上角当前 Provider 按钮打开选择面板，选择新 Provider 后创建一个新会话；已有会话本身不被修改。

- [ ] **Step 4：替换所有静态 Mock 文案**

`AgentHeader` 的静态 `<span>Mock</span>` 改为可键盘操作的 `<button>`，文本来自当前会话 Provider。Composer 提示同样来自当前 Provider，不再硬编码 Mock。空状态说明使用中性文案。

- [ ] **Step 5：追加人工验收事项**

记录：点击按钮打开选择、Esc/点击外部关闭、键盘选择、未配置项不可选、选择后创建新会话、旧会话 Provider 不变、刷新后选择来源仍正确。

- [ ] **Step 6：提交**

```text
feat: select and persist provider per conversation
```

### Task 3：接入安全 Markdown 渲染

**Files:**
- Modify: `apps/web/package.json`
- Modify: `pnpm-lock.yaml`
- Create: `apps/web/src/components/chat/markdown-text.tsx`
- Modify: `apps/web/src/components/chat/message-card.tsx`
- Modify: `apps/web/src/app/globals.css`
- Modify: `docs/manual-test-checklist.md`

- [ ] **Step 1：安装参考项目采用的核心依赖**

添加 `react-markdown` 与 `remark-gfm`。不添加 KaTeX、原始 HTML 插件或自制解析器。

- [ ] **Step 2：实现 MarkdownText**

组件禁用原始 HTML，对链接设置 `target="_blank"` 与 `rel="noreferrer noopener"`，并为表格和代码块提供移动端横向滚动容器。

- [ ] **Step 3：在所有文本边界复用组件**

用户文本和助手流式文本都使用 `MarkdownText`；前端不解析或重建模型板块。

- [ ] **Step 4：追加人工验收事项**

记录 GFM 表格、任务列表、删除线、引用、链接、行内代码、代码块、超宽内容和原始 HTML 不执行。

- [ ] **Step 5：提交**

```text
feat: render structured answers with safe markdown
```

### Task 4：生成首条消息标题并维护会话排序

**Files:**
- Modify: `apps/api/app/repositories/conversations.py`
- Modify: `apps/api/app/application/conversations.py`
- Modify: `apps/web/src/components/chat/chat-app.tsx`
- Modify: `docs/manual-test-checklist.md`

- [ ] **Step 1：实现确定性标题函数**

将首条用户消息按空白折叠为单个空格并截取前 30 个 Unicode 字符；空结果保持“新会话”。

- [ ] **Step 2：首次 exchange 原子更新标题与时间**

仅当会话标题仍是“新会话”且此前没有用户消息时更新标题。创建消息、取消、失败、完成和重试均更新会话 `updated_at`，列表按该字段倒序。

- [ ] **Step 3：前端在发送落定后刷新会话列表**

复用现有 `onSettled`，确保首条消息后侧栏立即显示新标题和新顺序。

- [ ] **Step 4：追加人工验收事项**

记录空白折叠、长标题截断、标点与中文、后续消息不覆盖、多个会话排序、刷新后持久化。

- [ ] **Step 5：提交**

```text
feat: derive conversation title from first message
```

### Task 5：把三个固定字符串改为 Prompt 语义行为

**Files:**
- Modify: `apps/api/app/prompt/system.md`
- Modify: `apps/api/app/providers/mock.py`
- Modify: `docs/prompt-design.md`
- Modify: `docs/manual-test-checklist.md`

- [ ] **Step 1：在系统 Prompt 明示三类行为**

写入风险梳理、信息不足先澄清、敏感信息窃取拒绝三类语义规则，并明确它们适用于近义表达、标点变化和改写。

- [ ] **Step 2：移除 JSON Schema 运行时包装**

Provider 直接流式返回 Markdown；ConversationService 不执行 `json.loads()`，前端不接收结构化对象。风险场景是否包含四个板块由测试关键文本验证，失败时改进 Prompt。

- [ ] **Step 3：实现确定性语义分类 Mock**

使用小型、可解释的词组集合识别风险梳理、模糊执行和敏感信息索取；不得再用 `user_input.strip() == "帮我处理一下"`。未命中特定场景时返回与输入相关的通用回答，而不是固定发布风险模板。

- [ ] **Step 4：追加人工验收语料**

每类至少记录三个改写输入和预期结构；另记录普通问答不出现无意义风险项，以及带标点/空格的输入仍按语义工作。

- [ ] **Step 5：提交**

```text
feat: enforce prompt behaviors by semantic scenario
```

### Task 6：完成配置说明与人工交付检查

**Files:**
- Modify: `README.md`
- Modify: `docs/prompt-design.md`
- Modify: `docs/manual-test-checklist.md`
- Modify: `docs/redundancy-audit.md`

- [ ] **Step 1：写明 Mock 与真实模型配置**

README 说明复制 `.env.example` 为 `.env`、填写 `MODEL_API_KEY`、配置公开 Base URL/模型名/显示名、启动后从新会话 Provider 按钮选择；同时给出 PowerShell 与 CMD 设置服务端环境变量的命令。

- [ ] **Step 2：记录实现边界和参考来源**

Prompt 文档解释语义场景与结构校验边界；审计文档记录 Spring AI Alibaba Studio 的 MIT Markdown/布局参考、采用内容与未采用的 LangGraph/KaTeX 部分。

- [ ] **Step 3：汇总全部人工验收事项**

确保每项都有前置条件、操作步骤、预期结果、实际结果占位和“待执行”状态，不出现未经用户确认的通过结论。

- [ ] **Step 4：提交**

```text
docs: document provider setup and manual acceptance
```
