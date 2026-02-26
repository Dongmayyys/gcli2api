"""
请求日志中间件 - 输出精简的 API 调用日志 + 调试日志

精简日志格式: [时间] [INFO] emoji 模型 | 客户端
示例: 
  - 🚀 gemini-3-flash | CherryStudio   (🚀 = flash 系列)
  - ⭐ gemini-2.5-pro | Cursor          (⭐ = pro 系列)
  - ☁️ claude-sonnet-4 | CherryStudio   (☁️ = claude 系列)
  - 🔹 other-model | Browser            (🔹 = 其他)

调试日志: 通过 /debug/on 开启后，将原始请求体写入 docs/requests.log (JSONL)
"""

import datetime
import json
import re
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from log import log

# 项目根目录（用于调试日志文件路径）
_project_root = Path(__file__).resolve().parent.parent

# API 路径模式匹配
API_PATTERNS = [
    # Gemini 格式: /antigravity/v1beta/models/{model}:streamGenerateContent
    (r"^/antigravity/v1(?:beta)?/models/([^:]+):", "antigravity"),
    # OpenAI 格式: /antigravity/v1/chat/completions
    (r"^/antigravity/v1/chat/completions", "antigravity"),
    # Anthropic 格式: /antigravity/v1/messages
    (r"^/antigravity/v1/messages", "antigravity"),
    # Geminicli Gemini 格式: /v1beta/models/{model}:streamGenerateContent
    (r"^/v1(?:beta)?/models/([^:]+):", "geminicli"),
    # Geminicli OpenAI 格式: /v1/chat/completions
    (r"^/v1/chat/completions", "geminicli"),
    # Geminicli Anthropic 格式: /v1/messages
    (r"^/v1/messages", "geminicli"),
]


def extract_client_name(user_agent: str) -> str:
    """
    从 User-Agent 提取客户端名称
    
    策略：提取所有 Product/Version token，过滤掉浏览器引擎 token，
    取第一个非引擎 token 作为客户端名。无需为新客户端维护硬编码列表。
    
    示例:
    - "Mozilla/5.0 ... CherryStudio/1.7.13 Chrome/120 ..." -> "CherryStudio"
    - "python-requests/2.28.0" -> "python-requests"
    - "Kelivo" -> "Kelivo"
    """
    if not user_agent:
        return "Unknown"
    
    # 纯名称 UA（无空格无斜杠），如 "Kelivo"
    if re.match(r"^[A-Za-z][A-Za-z0-9_-]*$", user_agent):
        return user_agent
    
    # 浏览器引擎 / 通用 token（小写），遇到这些就跳过
    BROWSER_TOKENS = {
        "mozilla", "applewebkit", "chrome", "chromium", "safari",
        "gecko", "khtml", "edg", "edge", "opr", "opera",
    }
    
    # 提取所有 Product/Version token
    tokens = re.findall(r"([A-Za-z][A-Za-z0-9_-]*)/[\d.]+", user_agent)
    
    # 过滤掉浏览器引擎 token，取第一个剩余的
    for token in tokens:
        if token.lower() not in BROWSER_TOKENS:
            return token
    
    # 所有 token 都是引擎（纯浏览器访问）
    return "Browser"


def parse_request_info(path: str, user_agent: str) -> tuple:
    """
    解析请求信息
    
    返回: (mode, model, client) 或 None（如果不是 API 请求）
    """
    for pattern, mode in API_PATTERNS:
        match = re.match(pattern, path)
        if match:
            # 提取模型名（如果模式中有捕获组）
            model = match.group(1) if match.lastindex else "chat"
            client = extract_client_name(user_agent)
            return (mode, model, client)
    
    return None


def _write_debug_log(body_data: dict, model: str, client: str, mode: str, path: str):
    """
    将原始请求体以 JSONL 格式写入 docs/requests.log。
    
    统一记录所有端点（Gemini/OpenAI/Anthropic）的原始请求体，
    前端面板可解析为可折叠卡片。
    自动识别 Gemini / OpenAI / Anthropic 格式并提取摘要信息。
    """
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 格式无关的摘要提取
    msg_count = 0
    roles = {}
    has_system = False
    has_tools = False

    if "contents" in body_data:
        # Gemini 格式: contents[].role
        messages = body_data["contents"]
        msg_count = len(messages)
        for msg in messages:
            r = msg.get("role", "?")
            roles[r] = roles.get(r, 0) + 1
        has_system = "systemInstruction" in body_data
        has_tools = "tools" in body_data
    elif "messages" in body_data:
        # OpenAI / Anthropic 格式: messages[].role
        messages = body_data["messages"]
        msg_count = len(messages)
        for msg in messages:
            r = msg.get("role", "?")
            roles[r] = roles.get(r, 0) + 1
        # OpenAI: 有 role=system 的消息; Anthropic: 有 system 顶层字段
        has_system = "system" in body_data or any(m.get("role") == "system" for m in messages)
        has_tools = "tools" in body_data

    record = {
        "ts": ts,
        "model": model,
        "client": client,
        "mode": mode,
        "path": path,
        "msg_count": msg_count,
        "roles": roles,
        "has_system": has_system,
        "has_tools": has_tools,
        "body": body_data,
    }

    try:
        log_dir = _project_root / "docs"
        log_dir.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False)
        with open(log_dir / "requests.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
        log.debug("[DEBUG_LOG] 请求已记录到 docs/requests.log")
    except Exception as e:
        log.warning(f"[DEBUG_LOG] 写入日志失败: {e}")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    
    功能:
    1. 精简日志: emoji + 模型名 + 客户端（始终开启）
    2. 调试日志: 原始请求体写入文件（通过 /debug/on 开启）
    """
    
    async def dispatch(self, request: Request, call_next):
        # 解析请求信息
        path = request.url.path
        user_agent = request.headers.get("user-agent", "")
        
        info = parse_request_info(path, user_agent)
        
        if info:
            mode, model, client = info
            body_data = None

            # OpenAI/Anthropic 端点的模型名在请求体中，需要从 body 提取
            # request.body() 在 Starlette 中会缓存，不影响下游路由读取
            if model == "chat":
                try:
                    body = await request.body()
                    if body:
                        body_data = json.loads(body)
                        model = body_data.get("model", "unknown")
                except Exception:
                    model = "unknown"

            # 按模型系列选择 emoji
            model_lower = model.lower()
            if "claude" in model_lower:
                emoji = "☁️"
            elif "flash" in model_lower:
                emoji = "🚀"
            elif "pro" in model_lower:
                emoji = "⭐"
            else:
                emoji = "🔹"
            log.info(f"{emoji} {model} | {client}")

            # ===== 调试日志：记录原始请求体 =====
            from src.panel.debug import debug_log_enabled
            if debug_log_enabled:
                # 如果上面没读过 body（Gemini 端点），现在读
                if body_data is None:
                    try:
                        body = await request.body()
                        if body:
                            body_data = json.loads(body)
                    except Exception:
                        body_data = {"_error": "无法解析请求体"}
                if body_data:
                    _write_debug_log(body_data, model, client, mode, path)
        
        # 继续处理请求
        response = await call_next(request)
        return response

