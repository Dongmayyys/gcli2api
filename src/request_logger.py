"""
请求日志中间件 - 输出精简的 API 调用日志

格式: [时间] [INFO] emoji 模型 | 客户端
示例: 
  - 🚀 gemini-3-flash | CherryStudio  (🚀 = antigravity)
  - ✨ gemini-3-flash | Cursor        (✨ = geminicli)
"""

import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from log import log


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
    
    示例:
    - "Mozilla/5.0 ... CherryStudio/1.7.13 ..." -> "CherryStudio"
    - "Mozilla/5.0 ... Cursor/2.1.0 ..." -> "Cursor"
    - "python-requests/2.28.0" -> "python-requests"
    """
    if not user_agent:
        return "Unknown"
    
    # 常见客户端模式
    client_patterns = [
        r"(CherryStudio)/[\d.]+",
        r"(Cursor)/[\d.]+",
        r"(VSCode)/[\d.]+",
        r"(Insomnia)/[\d.]+",
        r"(Postman)/[\d.]+",
        r"(HTTPie)/[\d.]+",
        r"(curl)/[\d.]+",
        r"(python-requests)/[\d.]+",
        r"(axios)/[\d.]+",
        r"(node-fetch)/[\d.]+",
        r"(Electron)/[\d.]+",
    ]
    
    for pattern in client_patterns:
        match = re.search(pattern, user_agent, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # 如果没匹配到已知客户端，尝试提取第一个产品名
    # 格式: ProductName/Version
    match = re.search(r"^([A-Za-z][A-Za-z0-9_-]*)/", user_agent)
    if match:
        return match.group(1)
    
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


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    精简请求日志中间件
    
    只记录 API 调用，忽略静态资源等其他请求
    """
    
    async def dispatch(self, request: Request, call_next):
        # 解析请求信息
        path = request.url.path
        user_agent = request.headers.get("user-agent", "")
        
        info = parse_request_info(path, user_agent)
        
        if info:
            mode, model, client = info
            # 不同模式用不同 emoji: 🚀 = antigravity, ✨ = geminicli
            emoji = "🚀" if mode == "antigravity" else "✨"
            log.info(f"{emoji} {model} | {client}")
        
        # 继续处理请求
        response = await call_next(request)
        return response
