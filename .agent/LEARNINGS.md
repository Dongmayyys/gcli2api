# LEARNINGS
> 最后更新: 2026-02-27

## 架构与设计决策

- **请求日志中间件**: `src/request_logger.py` 统一处理精简日志 + 调试日志。emoji 标注模型（🚀flash ⭐pro ☁️claude 🔹其他），从请求体提取 OpenAI/Anthropic 端点的模型名
- **调试日志**: 中间件层统一记录所有端点的原始请求体到 `docs/requests.log`（JSONL），自动识别 Gemini/OpenAI/Anthropic 格式提取摘要。面板 `/debug/on` 开关控制
- **客户端识别**: 排除法（过滤浏览器引擎 token）替代硬编码列表，自动识别任意新客户端 + 纯名称 UA（如 `"Kelivo"`）
- **模型列表**: `src/utils.py` 只展示基础模型+思考后缀，手动输入其他前缀仍有效
- **Redis 可选缓存层**: `mongodb_manager.py` 用 Redis Set 做凭证池 + TTL key 做冷却。设 `REDIS_URL` 启用，不设则纯 MongoDB
- **重试机制**: 无 cooldown 的 429/503 保留当前凭证重试；有 cooldown 的才切换
- **成功记录 fire-and-forget**: `credential_manager.py` 用 `asyncio.create_task` + 条件写入，不阻塞请求链路
- **antigravity 伪装 prompt 已取消**: `gemini_fix.py` 中 systemInstruction 注入被注释掉，客户端原样透传
- **Token usage 透传**: 三种格式（OpenAI/Gemini/Anthropic）的 token 用量都直接映射后端 `usageMetadata`，不做本地估算。`openai2gemini.py:_convert_usage_metadata` 和 `anthropic2gemini.py` L893 负责字段映射

## 代码陷阱与注意事项

- `gemini.py`: `stream_generate_content` 需 `Request` 参数获取 UA（`_write_debug_log` 已移至中间件）
- `gemini_fix.py`: Gemini 3 系列 `-maxthinking` 用 `thinkingLevel: "high"` 替代 `thinkingBudget`；`claude-opus-4-6-thinking` 不支持预填充
- `log.py`: `ENABLE_LOG=0` 彻底关闭日志。flush 间隔 2s，WebSocket 推送最多延迟 2s
- `request.body()` 在 Starlette 中会缓存，可多次读取
- `front/common.js` (~145KB CRLF): 模板字符串特殊字符易致工具匹配失败，优先用字符串拼接或 PowerShell 按行号操作
- **端点格式选择**: 默认用 OpenAI 格式（客户端和 `openai2gemini.py` 转换层都最成熟，出问题概率最低）；需要抗截断等高级功能时用 Gemini 格式（少一层转换）；Anthropic 仅兼容性兜底
- **假流式 Anthropic token 不准**: `fake_stream.py:build_anthropic_fake_stream_chunks` 硬编码 `input_tokens: 0`，`output_tokens` 用字符长度代替 token 数。仅影响 `假流式/` 前缀 + Anthropic 端点的组合
- **`/v1/messages/count_tokens`**: 用 `token_estimator.py` 本地粗估（字符数/4 + 图片×300），非后端真实计数

## 模块间关系

- Preview 通道: `common.js` → `panel/creds.py` → `credential_manager.py` → `sqlite_manager.py`
- 请求日志: HTTP → `request_logger.py`（中间件）→ `log.py`
- 调试日志: HTTP → `request_logger.py`（中间件，import `debug_log_enabled`）→ `docs/requests.log` ← `panel/debug.py` ← `common.js`

## Git 习惯

- `master`（上游）→ `my-dev`（部署）
- 用户偏好 `git commit --amend` + `--force` 保持干净历史
