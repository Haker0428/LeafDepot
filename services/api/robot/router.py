"""
机器人接口路由
"""
import json
import time
import asyncio
import logging
from collections import deque
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException

from services.api.shared.config import logger, rcs_logger

router = APIRouter(prefix="/api/robot", tags=["robot"])

# 机器人状态队列（deque，支持多 END 并发到达不丢失）
_robot_status_queue: deque = deque()
_status_event = asyncio.Event()


def clear_robot_status_queue():
    """清空状态队列（模拟模式循环开始时调用，防止旧状态残留）
    如果队列已有 END 则不清，避免丢失已到达的 END
    """
    if not _robot_status_queue:
        _robot_status_queue.clear()
        _status_event.clear()


async def update_robot_status(method: str, data: Optional[Dict] = None, robot_task_code: str = ""):
    """更新机器人状态并触发事件"""
    store = {
        "method": method,
        "timestamp": time.time(),
        "data": data or {},
        "robotTaskCode": robot_task_code,
    }
    # END 回调中提取 binCode（真实 RCS 用 slotName，模拟 RCS 用 data.binCode）
    if method == "end" and data:
        bin_code = data.get("slotName") or data.get("binCode") or data.get("code") or data.get("location") or ""
        if bin_code:
            store["binCode"] = bin_code
            rcs_logger.info(f"END 回调提取 binCode: {bin_code}, robotTaskCode: {robot_task_code}")
    _robot_status_queue.append(store)
    logger.info(f"更新机器人状态: {method}，队列长度: {len(_robot_status_queue)}")
    _status_event.set()


async def wait_for_robot_status(expected_method: str, timeout: int = 300):
    """等待特定机器人状态，从队列中弹出匹配的条目"""
    logger.info(f"开始等待机器人状态: {expected_method}, 超时: {timeout}秒")
    start_time = time.time()

    while True:
        # 先从队列中查找匹配的 END（防止已有 END 在队列中等待）
        for j in range(len(_robot_status_queue) - 1, -1, -1):
            if _robot_status_queue[j].get("method") == expected_method:
                item = _robot_status_queue[j]
                del _robot_status_queue[j]
                logger.info(f"从队列中取出期望状态: {expected_method}，binCode={item.get('binCode', '')}，剩余: {len(_robot_status_queue)}")
                return item

        elapsed = time.time() - start_time
        remaining = timeout - elapsed
        if remaining <= 0:
            logger.error(f"等待机器人状态超时: {expected_method}")
            raise asyncio.TimeoutError(f"等待 {expected_method} 状态超时")

        try:
            await asyncio.wait_for(_status_event.wait(), timeout=min(1.0, remaining))
            _status_event.clear()
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.error(f"等待机器人状态超时: {expected_method}")
                raise asyncio.TimeoutError(f"等待 {expected_method} 状态超时")
            continue



@router.post("/reporter/task")
async def task_status(request: Request):
    """机器人任务状态反馈接口"""
    try:
        request_data = await request.json()
        logger.info("反馈任务状态")
        rcs_logger.info(f"【RCS回调请求】data={json.dumps(request_data, ensure_ascii=False)}")

        robot_task_code = request_data.get("robotTaskCode")
        single_robot_code = request_data.get("singleRobotCode")
        extra = request_data.get("extra", "")

        if extra:
            try:
                extra_data = json.loads(extra) if isinstance(extra, str) else extra
                # extra 可能是 list [{"values": {...}}]（真实RCS）或 list [{"method":..., "data":{...}}]（模拟RCS）
                if isinstance(extra_data, list):
                    for item in extra_data:
                        # 真实 RCS 格式: {"values": {"method": "end", ...}}
                        # 模拟 RCS 格式: {"method": "end", "data": {...}}
                        values = item.get("values") or item
                        method = values.get("method", "")
                        # 提取位置信息：真实 RCS 用 location，模拟 RCS 用 data.location
                        location_data = item.get("data") or {}
                        if location_data and "location" in location_data:
                            values["location"] = location_data["location"]
                        logger.info(f"处理method: {method}")
                        await update_robot_status(method, values, robot_task_code=robot_task_code)
                        if method == "start":
                            logger.info("任务开始")
                        elif method == "outbin":
                            logger.info("走出储位")
                        elif method == "end":
                            logger.info("任务完成")
                else:
                    values = extra_data.get("values") or extra_data
                    method = values.get("method", "")
                    # 提取位置信息
                    location_data = extra_data.get("data") or {}
                    if location_data and "location" in location_data:
                        values["location"] = location_data["location"]
                    logger.info(f"处理method: {method}")
                    await update_robot_status(method, values, robot_task_code=robot_task_code)
                    if method == "start":
                        logger.info("任务开始")
                    elif method == "outbin":
                        logger.info("走出储位")
                    elif method == "end":
                        logger.info("任务完成")
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"无法解析extra字段: {extra}, error: {e}")

        response_body = {
            "code": "SUCCESS",
            "message": "成功",
            "data": {"robotTaskCode": robot_task_code or "ctu001"}
        }
        rcs_logger.info(f"【RCS回调响应】body={json.dumps(response_body, ensure_ascii=False)}")
        return response_body

    except Exception as e:
        logger.error(f"处理状态反馈失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理状态反馈失败: {str(e)}")
