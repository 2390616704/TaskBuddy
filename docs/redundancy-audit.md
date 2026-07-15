# 冗余与安全审计

## Provider 与 SDK

- 模型 SDK 调用只位于 `apps/api/app/providers/openai_compatible.py`。
- Mock 与真实模型实现相同 `ModelProvider` 协议。
- Provider Registry 是公开元数据和按 ID 查找的唯一入口。
- 浏览器只持有 `providerId`，不接触 Key 或 Base URL。

## Prompt 与输出

- 系统 Prompt 只有一份生产来源：`apps/api/app/prompt/system.md`。
- Prompt Builder 保留 system/user/assistant 角色，不复制多份长模板。
- 模型输出直接使用 Markdown，不存在 JSON 信封、中文标题解析器或重复的结构映射。
- Markdown 统一由 `MarkdownText` 渲染，未手写解析器。

## API 与数据

- SQLite 是会话、消息、状态、标题和会话 Provider 的唯一持久化事实来源。
- 发送、取消和重试共用 ConversationService 与 Provider 接口。
- 会话创建后锁定 Provider，避免请求级参数与数据库状态重复。
- 旧数据库通过启动迁移补充 `provider_id=mock`。

## 第三方参考

Spring AI Alibaba Studio 的 `agent-chat-ui` 声明 MIT License。TaskBuddy 采用其布局和 Markdown 依赖选择，不复制 LangGraph 业务状态、工具调用、KaTeX 或完整 UI。OpenAI Agents SDK 作为包依赖使用，不复制其源码到仓库。

## 密钥检查事项

- `.env`、本地数据库、虚拟环境和构建产物已加入 `.gitignore`；
- `.env.example` 的 `MODEL_API_KEY` 保持为空；
- Base URL、模型名和环境变量名称不是密钥，可公开用于复现；
- 提交前仍需由用户执行工作树与 Git 历史密钥扫描，并把实际结果填入人工测试清单；
- 若发现真实密钥进入历史，必须先撤销并轮换，再清理历史，不能只删除当前文件。

## 当前状态

本文记录静态设计审计结论，不代表运行测试或密钥扫描已经通过。实际验证状态以 `docs/manual-test-checklist.md` 为准。
