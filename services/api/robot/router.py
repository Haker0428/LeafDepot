"""
机器人接口路由
"""
import json
import time
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException

from services.api.shared.config import logger

router = APIRouter(prefix="/api/robot", tags=["robot"])

# 机器人状态存储
_robot_status_store: Dict[str, Any] = {}
_status_event = asyncio.Event()


async def update_robot_status(method: str, data: Optional[Dict] = None):
    """更新机器人状态并触发事件"""
    _robot_status_store["ROBOT_STATUS"] = {
        "method": method,
        "timestamp": time.time(),
        "data": data or {}
    }
    logger.info(f"更新机器人状态: {method}")
    _status_event.set()


async def wait_for_robot_status(expected_method: str, timeout: int = 300):
    """等待特定机器人状态的同步函数"""
    logger.info(f"开始等待机器人状态: {expected_method}, 超时: {timeout}秒")
    start_time = time.time()
    _status_event.clear()

    if "ROBOT_STATUS" in _robot_status_store:
        current_status = _robot_status_store["ROBOT_STATUS"]
        if current_status.get("method") == expected_method:
            logger.info(f"已存在期望状态: {expected_method}")
            return current_status

    while True:
        try:
            await asyncio.wait_for(_status_event.wait(), timeout=1.0)
            if "ROBOT_STATUS" in _robot_status_store:
                current_status = _robot_status_store["ROBOT_STATUS"]
                logger.info(f"收到机器人状态: {current_status.get('method')}")
                if current_status.get("method") == expected_method:
                    logger.info(f"收到期望状态: {expected_method}")
                    return current_status
            _status_event.clear()
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            if elapsed_time >= timeout:
                logger.error(f"等待机器人状态超时: {expected_method}")
                raise asyncio.TimeoutError(f"等待 {expected_method} 状态超时")
            continue


@router.post("/reporter/task")
async def task_status(request: Request):
    """机器人任务状态反馈接口"""
    try:
        request_data = await request.json()
        logger.info("反馈任务状态")
        logger.info(f"【RCS回调请求】data={json.dumps(request_data, ensure_ascii=False)}")

        robot_task_code = request_data.get("robotTaskCode")
        single_robot_code = request_data.get("singleRobotCode")
        extra = request_data.get("extra", "")

        if extra:
            try:
                extra_data = json.loads(extra) if isinstance(extra, str) else extra
                # extra 可能是 dict {"values": {...}} 或 list [{"values": {...}}]
                if isinstance(extra_data, list):
                    for item in extra_data:
                        values = item.get("values", {})
                        method = values.get("method", "")
                        logger.info(f"处理method: {method}")
                        await update_robot_status(method, values)
                        if method == "start":
                            logger.info("任务开始")
                        elif method == "outbin":
                            logger.info("走出储位")
                        elif method == "end":
                            logger.info("任务完成")
                else:
                    values = extra_data.get("values", {})
                    method = values.get("method", "")
                    logger.info(f"处理method: {method}")
                    await update_robot_status(method, values)
                    if method == "start":
                        logger.info("任务开始")
                    elif method == "outbin":
                        logger.info("走出储位")
                    elif method == "end":
                        logger.info("任务完成")
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"无法解析extra字段: {extra}, error: {e}")

        return {
            "code": "SUCCESS",
            "message": "成功",
            "data": {"robotTaskCode": "ctu001"}
        }

    except Exception as e:
        logger.error(f"处理状态反馈失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理状态反馈失败: {str(e)}")
