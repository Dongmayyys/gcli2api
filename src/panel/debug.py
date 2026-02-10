"""
Debug 控制路由 - 运行时调试开关 + 日志查看

通过控制面板或直接 URL 控制 debug 日志的开关状态，无需重启服务。
用于分析不同客户端的请求体结构和提示词注入行为。

控制面板调用（Bearer token 鉴权）：
    GET  /debug/status   → 查看状态
    GET  /debug/on       → 开启
    GET  /debug/off      → 关闭
    GET  /debug/log      → 读取日志内容
    DELETE /debug/log    → 清空日志
"""

import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from log import log
from src.utils import verify_panel_token

# 项目根目录
_project_root = Path(__file__).resolve().parent.parent.parent
_log_file = _project_root / "docs" / "requests.log"

# 运行时 debug 开关（进程内存，重启自动归零）
debug_log_enabled = False

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/status")
async def debug_status(token: str = Depends(verify_panel_token)):
    """查看调试日志状态"""
    log_size = 0
    if _log_file.exists():
        log_size = _log_file.stat().st_size
    return JSONResponse(content={
        "debug_log": debug_log_enabled,
        "log_size": log_size,
    })


@router.get("/on")
async def debug_on(token: str = Depends(verify_panel_token)):
    """开启请求体调试日志"""
    global debug_log_enabled
    debug_log_enabled = True
    log.info("🔓 DEBUG 日志已开启 → docs/requests.log")
    return JSONResponse(content={"debug_log": True, "message": "调试日志已开启"})


@router.get("/off")
async def debug_off(token: str = Depends(verify_panel_token)):
    """关闭请求体调试日志"""
    global debug_log_enabled
    debug_log_enabled = False
    log.info("🔒 DEBUG 日志已关闭")
    return JSONResponse(content={"debug_log": False, "message": "调试日志已关闭"})


@router.get("/log")
async def debug_log_content(token: str = Depends(verify_panel_token)):
    """读取调试日志文件，解析 JSONL 并返回 JSON 数组"""
    if not _log_file.exists():
        return JSONResponse(content=[])
    try:
        records = []
        for line in _log_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                # 兼容旧格式或损坏行，跳过
                continue
        return JSONResponse(content=records)
    except Exception as e:
        log.warning(f"[DEBUG] 读取日志失败: {e}")
        return JSONResponse(content=[], status_code=500)


@router.delete("/log")
async def debug_log_clear(token: str = Depends(verify_panel_token)):
    """清空调试日志文件"""
    try:
        if _log_file.exists():
            _log_file.write_text("", encoding="utf-8")
            log.info("🗑️ DEBUG 日志已清空")
        return JSONResponse(content={"message": "日志已清空"})
    except Exception as e:
        log.warning(f"[DEBUG] 清空日志失败: {e}")
        return JSONResponse(content={"message": f"清空失败: {e}"}, status_code=500)
