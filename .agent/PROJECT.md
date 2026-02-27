# PROJECT: gcli2api

> 生成时间: 2026-02-25  |  最后更新: 2026-02-25

## 技术栈

- Runtime: Python 3.12+ (target 3.13)
- Framework: FastAPI + Hypercorn (ASGI)
- Language: Python
- Database: SQLite (默认, aiosqlite) / MongoDB (可选, motor) / Redis (可选缓存)
- Package Manager: pip (requirements.txt + pyproject.toml)
- Monorepo: 无

## 常用命令

- 安装依赖: `pip install -r requirements.txt`
- 开发启动: `python web.py`
- 构建 Docker: `docker build -t gcli2api .`
- 测试（全部）: `pytest`
- 测试（单个）: `pytest test_xxx.py -v`
- Lint: `flake8` / `black --check .` / `mypy .`

## 目录结构

- `web.py` → 入口文件，FastAPI app 创建、路由挂载、Hypercorn 启动
- `config.py` → 统一配置系统（ENV > Storage > Default 优先级链）
- `log.py` → 日志模块
- `src/` → 核心源码
  - `src/api/` → 底层 API 客户端（直接与 Google API 通信）
    - `geminicli.py` → GeminiCLI Code Assist API 客户端
    - `antigravity.py` → Antigravity (daily sandbox) API 客户端
    - `utils.py` → API 工具函数（cooldown 解析、流式收集等）
  - `src/router/` → FastAPI 路由层（接收请求、格式转换、调用 API 客户端）
    - `geminicli/` → GeminiCLI 路由（openai.py, gemini.py, anthropic.py, model_list.py）
    - `antigravity/` → Antigravity 路由（同结构）
    - `base_router.py` → 路由基类 / 公共逻辑
    - `hi_check.py` → 健康检查
  - `src/converter/` → 格式转换核心
    - `openai2gemini.py` → OpenAI ↔ Gemini 双向转换（含 Tool/Function 转换）
    - `anthropic2gemini.py` → Anthropic (Claude) ↔ Gemini 转换
    - `gemini_fix.py` → Gemini 请求规范化（thinking config、search、图片生成）
    - `anti_truncation.py` → 流式抗截断机制
    - `fake_stream.py` → 假流式实现
    - `thoughtSignature_fix.py` → thinking signature 编解码
  - `src/panel/` → 控制面板（Web UI 后端路由）
    - `auth.py` → 面板认证
    - `creds.py` → 凭证 CRUD API
    - `config_routes.py` → 配置管理 API
    - `debug.py` → 调试日志 API
    - `logs.py` → 日志查看/WebSocket
    - `version.py` → 版本信息 API
  - `src/storage/` → 存储后端实现
    - `sqlite_manager.py` → SQLite 存储
    - `mongodb_manager.py` → MongoDB 存储
  - `src/storage_adapter.py` → 存储适配器（Protocol + 工厂模式，自动选择后端）
  - `src/credential_manager.py` → 凭证管理器（单例，负载均衡、轮换、刷新、封禁）
  - `src/auth.py` → OAuth 2.0 认证流程管理（GCLI + Antigravity 双模式）
  - `src/google_oauth_api.py` → Google OAuth API 底层封装
  - `src/httpx_client.py` → 统一 httpx 异步 HTTP 客户端
  - `src/models.py` → Pydantic 数据模型（OpenAI / Gemini / Anthropic 格式）
  - `src/task_manager.py` → 全局异步任务生命周期管理
  - `src/utils.py` → 公共常量与工具函数
  - `src/token_estimator.py` → Token 估算
  - `src/request_logger.py` → 请求日志中间件
- `front/` → 控制面板前端
  - `control_panel.html` → 桌面端面板
  - `control_panel_mobile.html` → 移动端面板
  - `common.js` → 前端公共逻辑 (~145KB)
- `creds/` → 凭证文件存储目录
- `docs/` → 文档（含英文 README）

## 架构概要

API 代理服务，将 Google GeminiCLI (Code Assist) 和 Antigravity API 封装为
OpenAI / Gemini / Anthropic 三种兼容格式。采用三层架构：
Router 层接收多格式请求 → Converter 层做格式双向转换 → API 客户端层与 Google 后端通信。
凭证管理支持多凭证随机负载均衡 + 自动刷新/封禁/冷却。
存储层通过 Protocol + 适配器模式支持 SQLite / MongoDB / Redis 可插拔切换。

## 核心概念

- **GeminiCLI 模式**: 通过 Google Code Assist (cloudcode-pa) 端点访问 Gemini 模型
- **Antigravity 模式**: 通过 Google daily sandbox 端点访问模型（含 Claude 系列）
- **凭证轮换**: 多个 OAuth 凭证随机选取，按调用次数/错误自动轮换
- **Thinking Config**: 模型名后缀控制思考预算（-max, -high, -medium, -low, -nothinking）
- **抗截断**: 检测流式响应被截断后自动续接

## 代码约定

- 异步优先: 所有 I/O 操作使用 async/await
- 配置优先级: 环境变量 > 存储（DB/文件） > 默认值
- 双模式: 大部分模块通过 `mode` 参数区分 "geminicli" / "antigravity"
- 凭证管理器使用单例包装器 `_CredentialManagerSingleton` 实现懒加载
- 存储后端通过 `StorageBackend` Protocol 定义接口，`StorageAdapter` 工厂自动选择实现
- Pydantic v2 数据模型，`Config.extra = "allow"` 宽容解析
- Black 格式化，line-length=100
- 中文注释 + 英文 docstring 混用

## Git 约定

- 分支策略: `master`（上游主分支） + `my-dev`（本地开发分支）
- Commit 格式: 混合风格，无严格规范
  - `feat: 控制面板调试Tab - 请求体日志捕获与可视化`
  - `refactor: 精简模型列表，从120个减到20个`
  - `Update mongodb_manager.py`（上游风格，自由格式）
  - `chore: update version.txt [skip ci]`（自动生成）

## 已有的规则文件
