# LEARNINGS
> 最后更新: 2026-02-26

## 架构与设计决策

- **请求日志**: `src/request_logger.py` 中间件替代 Hypercorn access log（默认关闭，`ACCESS_LOG_ENABLED=true` 可恢复）。emoji 标注模型：🚀flash ⭐pro ☁️claude 🔹其他
- **调试日志**: JSONL 格式写入 `docs/requests.log`，只记入站请求体不记响应。面板 Tab 操作（Bearer token 鉴权）
- **模型列表**: `src/utils.py` 只展示基础模型+思考后缀，手动输入其他前缀仍有效
- **Redis 可选缓存层**: `mongodb_manager.py` 用 Redis Set 做凭证池 + TTL key 做冷却。设 `REDIS_URL` 启用，不设则纯 MongoDB
- **重试机制**: 无 cooldown 的 429/503 保留当前凭证重试；有 cooldown 的才切换
- **成功记录 fire-and-forget**: `credential_manager.py` 用 `asyncio.create_task` + 条件写入，不阻塞请求链路
- **antigravity 伪装 prompt 已取消**: `gemini_fix.py` 中 systemInstruction 注入被注释掉，客户端原样透传

## 代码陷阱与注意事项

- `gemini.py`: `stream_generate_content` 需 `Request` 参数获取 UA，`_write_debug_log` 用 `extract_client_name()` 而非截取 UA 第一段
- `gemini_fix.py`: Gemini 3 系列 `-maxthinking` 用 `thinkingLevel: "high"` 替代 `thinkingBudget`；`claude-opus-4-6-thinking` 不支持预填充
- `log.py`: `ENABLE_LOG=0` 彻底关闭日志。flush 间隔 2s，WebSocket 推送最多延迟 2s
- `request.body()` 在 Starlette 中会缓存，可多次读取
- `front/common.js` (~145KB CRLF): 模板字符串特殊字符易致工具匹配失败，优先用字符串拼接或 PowerShell 按行号操作

## 模块间关系

- Preview 通道: `common.js` → `panel/creds.py` → `credential_manager.py` → `sqlite_manager.py`
- 请求日志: HTTP → `request_logger.py`（中间件）→ `log.py`
- 调试日志: API → `gemini.py:_write_debug_log` → `docs/requests.log` ← `panel/debug.py` ← `common.js`
- `panel/debug.py` 的 `debug_log_enabled` 被 `gemini.py` 跨模块 import

## Git 习惯

- `master`（上游）→ `my-dev`（部署），同步流程见 `/sync-upstream` workflow
- 用户偏好 `git commit --amend` + `--force` 保持干净历史
