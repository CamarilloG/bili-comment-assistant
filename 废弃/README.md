# 废弃 (Deprecated)

本目录存放**已废弃、不再参与运行与打包**的代码与文档，仅作历史参考。

## 目录说明

| 子目录/文件 | 说明 |
|-------------|------|
| **doc/** | 历史架构文档（含已废弃的 AI 中控台架构规划等） |
| **ai_center_legacy/** | 原 AI 中控台后端（Planner / Dispatcher / Executor / Validator / Reporter / EventBus / StateMachine 及 models、prompts）。前端与 `/api/session`、`/ws/session` 已移除，此处仅保留备份。当前项目仅保留根目录 `ai_center/model_router.py` 供 AI 模型路由使用。 |

## 当前项目结构（未废弃）

- **core/** — 核心逻辑（登录、搜索、评论、暖机、配置等）
- **modules/** — 功能模块（auth、comment、warmup、ai_gen、config 等）
- **web/** — FastAPI + Vue 控制面板（仅 Vue 前端，无 AI 中控台）
- **gui_tabs/** — GUI 标签页
- **utils/** — 工具
- **server/** — 本地 API 服务
- **ai_center/** — 仅保留 `model_router.py`（AI 模型路由）
- **bots/** — 机器人相关（可选）

运行与打包时不会包含本 `废弃/` 目录。
