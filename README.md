# TaskBuddy

TaskBuddy 是一个可本地运行的工作事项对话助手。它提供持久化会话、SSE 流式回复、取消与重试、按会话选择模型，以及安全的 Markdown 渲染。默认 Mock Provider 不需要任何密钥。

## 环境要求

- Node.js 20+
- pnpm 10.5.1（由 Corepack 管理）
- Python 3.12
- Windows PowerShell；其他系统可使用等价命令

SQLite 数据库随应用自动创建，不要求安装 PostgreSQL、Docker 或外部数据库。

## 从零安装

```powershell
corepack enable
corepack pnpm install
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\apps\api[dev,model]"
```

## 启动 Mock 模式

仓库不创建 `.env` 时默认仍可使用 Mock。启动前后端：

```powershell
corepack pnpm dev
```

- 页面：http://127.0.0.1:3000/
- 健康检查：http://127.0.0.1:8000/health

点击页面右上角 Provider 按钮，选择 Mock 后会创建一个绑定 Mock 的新会话。

## 配置真实模型

复制示例文件：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`：

```env
MODEL_PROVIDER=mock
DATABASE_URL=sqlite+aiosqlite:///./data/taskbuddy.db
MODEL_API_KEY=替换为考官自己的密钥
MODEL_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-v4-flash
MODEL_DISPLAY_NAME=DeepSeek
```

`MODEL_API_KEY` 只由 FastAPI 服务端读取。浏览器不会提交、保存或接收密钥。`.env` 已被 Git 忽略，禁止提交真实值；`.env.example` 只保存空值和公开配置。

也可以不创建 `.env`，直接设置服务端环境变量。

PowerShell：

```powershell
$env:MODEL_API_KEY="替换为考官自己的密钥"
$env:MODEL_BASE_URL="https://api.deepseek.com"
$env:MODEL_NAME="deepseek-v4-flash"
$env:MODEL_DISPLAY_NAME="DeepSeek"
corepack pnpm dev
```

CMD：

```bat
set MODEL_API_KEY=替换为考官自己的密钥
set MODEL_BASE_URL=https://api.deepseek.com
set MODEL_NAME=deepseek-v4-flash
set MODEL_DISPLAY_NAME=DeepSeek
corepack pnpm dev
```

启动后，点击右上角 Provider 按钮并选择真实模型。选择会创建新会话；已有会话不会中途更换 Provider。

OpenAI-compatible 适配器使用 OpenAI Agents SDK。更换兼容供应商时只调整 `MODEL_BASE_URL`、`MODEL_NAME` 和显示名，不需要修改前端或业务路由。

## 输出与安全边界

模型直接流式输出 Markdown，前端使用 `react-markdown` 和 `remark-gfm` 渲染。系统不会给回复增加 JSON 信封，也不会通过字符串解析重建“结论”等板块。发布风险场景的四个板块由 Prompt 行为约束，测试通过关键行为验证。

原始 HTML 不会执行；外部链接使用安全的新窗口属性。系统 Prompt、密钥和环境配置不得进入响应或日志。

## 人工验收

按项目约定，本阶段由用户亲自执行测试。完整步骤与预期结果见 [人工测试清单](docs/manual-test-checklist.md)。未填写实际结果的项目均为“待执行”，不代表通过。

## 项目结构

```text
apps/web/                 Next.js 前端、SSE 客户端和聊天组件
apps/api/app/api/         FastAPI 路由与错误映射
apps/api/app/application/ 对话用例与状态协调
apps/api/app/providers/   Mock、OpenAI-compatible 和 Provider Registry
apps/api/app/prompt/      系统 Prompt 与上下文构建
apps/api/app/repositories SQLite 模型、迁移和仓储
docs/                     Prompt、审计、协作与人工验收材料
```

## 常见问题

- 真实模型显示“未配置”：确认启动后端的同一终端进程能够读取 `MODEL_API_KEY`，然后重启服务。
- 页面仍显示旧内容：确认后端已重启；Next.js 前端支持热更新，但 Uvicorn 当前启动命令未启用 `--reload`。
- 模型返回 `MODEL_UNAVAILABLE`：检查兼容接口的 Base URL、模型名、密钥权限和余额。
- 不配置密钥：选择 Mock，完整的发送、流式、取消、重试和持久化流程仍可使用。
