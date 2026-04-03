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
    """收集前端日志并保存到 debug 目录"""
    try:
        frontend_log_filename = logs_dir / f"frontend_{datetime.now().strftime('%Y%m%d')}.log"

        frontend_logger = logging.getLogger("frontend")
        frontend_logger.setLevel(logging.DEBUG)

        if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(frontend_log_filename)
                   for h in frontend_logger.handlers):
            file_handler = logging.FileHandler(str(frontend_log_filename), encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s - [FRONTEND] - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            frontend_logger.addHandler(file_handler)

        timestamp = request.timestamp or datetime.now().isoformat()
        source = request.source or "unknown"
        extra_info = request.extra or {}

        log_message = f"[{source}] {request.message}"
        if extra_info:
            log_message += f" | Extra: {json.dumps(extra_info, ensure_ascii=False)}"

        log_level = request.level.lower()
        if log_level == "error":
            frontend_logger.error(log_message)
        elif log_level == "warn":
            frontend_logger.warning(log_message)
        elif log_level == "info":
            frontend_logger.info(log_message)
        else:
            frontend_logger.debug(log_message)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": 200,
                "message": "日志已保存",
                "data": {"log_file": str(frontend_log_filename)}
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
