"""
日志路由
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, status, Body
from fastapi.responses import JSONResponse

from services.api.shared.config import logger, logs_dir
from services.api.shared.models import FrontendLogRequest
from services.api.shared.operation_log import get_recent_operations, get_all_operations

router = APIRouter(prefix="/api", tags=["log"])


@router.post("/log/frontend")
async def collect_frontend_log(request: FrontendLogRequest = Body(...)):
    """收集前端日志并保存到 web_YYYYMMDD.log"""
    try:
        web_log_filename = logs_dir / f"web_{datetime.now().strftime('%Y%m%d')}.log"

        web_logger = logging.getLogger("web")
        web_logger.setLevel(logging.DEBUG)
        web_logger.propagate = False  # 不向上传递给 root logger，避免进入 gateway 日志

        if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(web_log_filename)
                   for h in web_logger.handlers):
            file_handler = logging.FileHandler(str(web_log_filename), encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s - [WEB] - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            web_logger.addHandler(file_handler)

        def _write_entry(entry: dict):
            ts = entry.get("timestamp") or datetime.now().isoformat()
            src = entry.get("source") or "unknown"
            extra_info = entry.get("extra") or {}
            lvl = (entry.get("level") or "info").lower()
            msg = entry.get("message") or ""

            log_message = f"[{ts}] [{src}] {msg}"
            if extra_info:
                log_message += f" | {json.dumps(extra_info, ensure_ascii=False)}"

            if lvl == "error":
                web_logger.error(log_message)
            elif lvl == "warn":
                web_logger.warning(log_message)
            elif lvl == "info":
                web_logger.info(log_message)
            else:
                web_logger.debug(log_message)

        # 批量模式
        if request.entries:
            for entry in request.entries:
                _write_entry(entry)
        # 单条模式（兼容旧版前端）
        elif request.message:
            _write_entry({
                "level": request.level,
                "message": request.message,
                "timestamp": request.timestamp,
                "source": request.source,
                "extra": request.extra,
            })

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": 200,
                "message": "日志已保存",
                "data": {"log_file": str(web_log_filename)}
            }
        )

    except Exception as e:
        logger.error(f"保存前端日志失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存前端日志失败: {str(e)}"
        )


@router.get("/operation/logs/recent")
async def get_recent_logs(limit: int = 5, days: int = 180):
    """获取最近的操作日志"""
    try:
        operations = get_recent_operations(limit=limit, days=days)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": 200,
                "message": "获取操作日志成功",
                "data": operations
            }
        )
    except Exception as e:
        logger.error(f"获取操作日志失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取操作日志失败: {str(e)}"
        )


@router.get("/operation/logs/all")
async def get_all_logs(days: int = 180):
    """获取所有操作日志"""
    try:
        operations = get_all_operations(days=days)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": 200,
                "message": "获取所有操作日志成功",
                "data": operations
            }
        )
    except Exception as e:
        logger.error(f"获取所有操作日志失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取所有操作日志失败: {str(e)}"
        )
