# AI 协作记录

本项目由用户与 Codex 共同完成设计和实现。用户负责产品边界、技术取舍批准与最终人工验收；Codex 负责读取考题、分析参考项目、编写代码和交付文档。

## 采用的外部参考

- Spring AI Alibaba Studio：采用固定视口、独立消息滚动、底部 Composer 的布局原则，以及 `react-markdown + remark-gfm` 的 Markdown 组件边界；未采用其 LangGraph 状态、Radix UI、KaTeX 和完整 Tailwind 组件。
- OpenAI Agents Python SDK：用于 OpenAI-compatible 真实模型适配和流式事件读取。

参考项目的许可和边界在冗余审计中记录。项目没有把第三方业务组件整套复制为自己的实现。

## 关键人工纠偏

- 从 Java 技术栈纠正为考题允许且便于复现的 Next.js + FastAPI；
- 从静态 Mock 标签纠正为按会话持久化的真实 Provider 选择；
- 从全页增长布局纠正为 Studio 风格的固定视口与独立滚动；
- 从固定六字段 JSON 回复纠正为模型自由 Markdown；
- 从考题三个原句匹配纠正为语义行为与改写场景；
- 测试执行改由用户亲自完成，Codex 只维护待执行清单，不伪造通过结果。

## 质量声明

AI 对话本身不是质量证据。可运行源码、Git 提交、人工测试记录、密钥审计和从零复现结果才是交付证据。当前人工清单中未填写的项目仍为待执行。
