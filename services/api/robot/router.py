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
from services.api.shared.config import debug_logger

from services.api.shared.config import logger, rcs_logger

router = APIRouter(prefix="/api/robot", tags=["robot"])

# 机器人状态队列（deque，支持多 END 并发到达不丢失）
_robot_status_queue: deque = deque()
_status_event = asyncio.Event()

# Sim 模式：binCode → robotTaskCode 映射（START 回调时建立，END 时查表）
_bin_to_robot_code: Dict[str, str] = {}

# robotTaskCode → task_no 映射（用于 END 路由到正确的 workflow）
_robot_code_to_task: Dict[str, str] = {}


def get_robot_code_for_bin(bin_code: str) -> Optional[str]:
    """根据 binCode 查找对应的 robotTaskCode（sim 模式使用）"""
    return _bin_to_robot_code.get(bin_code)


def clear_bin_robot_code_map():
    """清空 bin → robotTaskCode 映射表（任务开始前调用）"""
    _bin_to_robot_code.clear()


def register_task_for_robot_code(robot_code: str, task_no: str):
    """注册 robotTaskCode → task_no 映射（submit 时调用）"""
    _robot_code_to_task[robot_code] = task_no


def get_task_for_robot_code(robot_code: str) -> Optional[str]:
    """根据 robotTaskCode 查找对应的 task_no"""
    return _robot_code_to_task.get(robot_code)


def clear_robot_code_to_task_map():
    """清空 robotTaskCode → task_no 映射表"""
    _robot_code_to_task.clear()


def inject_cancel_end(bin_location: str, robot_task_code: str, task_no: str):
    """注入假 END，唤醒 wait_for_robot_status，立即退出取消任务的等待循环。

    Args:
        bin_location: 当前等待的库位
        robot_task_code: 当前等待的 robotTaskCode
        task_no: 任务号
    """
    store = {
        "method": "end",
        "timestamp": time.time(),
        "data": {"binCode": bin_location, "slotName": bin_location},
        "robotTaskCode": robot_task_code,
        "binCode": bin_location,
        "task_no": task_no,
    }
    _robot_status_queue.append(store)
    _status_event.set()
    logger.info(f"[取消] 注入假 END，唤醒 wait: bin={bin_location}, rt_code={robot_task_code}, 队列长度: {len(_robot_status_queue)}")


def clear_robot_status_queue():
    """清空状态队列（模拟模式循环开始时调用，防止旧状态残留）
    如果队列已有 END 则不清，避免丢失已到达的 END
    """
    if not _robot_status_queue:
        _robot_status_queue.clear()
        _status_event.clear()


def prune_robot_status_queue(valid_robot_codes: set):
    """从队列中移除不属于当前任务的旧 END 回调，释放内存。

    Args:
        valid_robot_codes: 当前任务有效的 robotTaskCode 集合。
    """
    original_len = len(_robot_status_queue)
    new_queue = deque(item for item in _robot_status_queue
                      if item.get("method") != "end"
                      or not item.get("robotTaskCode")
                      or item.get("robotTaskCode") in valid_robot_codes)
    _robot_status_queue.clear()
    _robot_status_queue.extend(new_queue)
    pruned = original_len - len(_robot_status_queue)
    if pruned > 0:
        logger.info(f"清理旧 END 回调 {pruned} 条，队列剩余 {len(_robot_status_queue)} 条")


async def update_robot_status(method: str, data: Optional[Dict] = None, robot_task_code: str = ""):
    """更新机器人状态。END 入队并触发事件；OUTBIN 只入队不触发事件。

    原因：Real RCS 只发 END；Sim RCS 先发 OUTBIN（不触发）再等 continue 才发 END（触发）。
    """
    if method not in ("end", "outbin"):
        return
    store = {
        "method": method,
        "timestamp": time.time(),
        "data": data or {},
        "robotTaskCode": robot_task_code,
    }
    # 提取 binCode（真实 RCS 用 slotName，模拟 RCS 用 data.binCode）
    if data:
        bin_code = data.get("slotName") or data.get("binCode") or data.get("code") or data.get("location") or ""
        if bin_code:
            store["binCode"] = bin_code
    # 根据 robotTaskCode 查找对应的 task_no，填入 store
    task_no = _robot_code_to_task.get(robot_task_code, "")
    if task_no:
        store["task_no"] = task_no
    # END 入队并触发事件，让 gateway 能及时响应；OUTBIN 只入队不触发事件
    # 原因：Real RCS 只发 END；Sim RCS 先发 OUTBIN（不触发）再等 continue 才发 END（触发）
    _robot_status_queue.append(store)
    logger.info(f"更新机器人状态: {method}，队列长度: {len(_robot_status_queue)}")
    if method == "end":
        _status_event.set()


async def wait_for_robot_status(expected_method: str, timeout: int = 300, valid_robot_codes: set = None, task_no: str = "", start_time: float = None):
    """等待特定机器人状态，从队列中弹出匹配的条目。

    Args:
        expected_method: 期望的方法名（如 "end"）
        timeout: 超时时间（秒）
        valid_robot_codes: 当前任务有效的 robotTaskCode 集合。
                         若传入，队列中 robotTaskCode 不在集合内的 END 会被跳过（保留在队列中）。
        task_no: 当前任务号。END 必须匹配此 task_no 才消费，不匹配则保留在队列中供其他 workflow 使用。
        start_time: 已累计的等待开始时间戳（由外部传入，避免重复计时）
    """
    if start_time is None:
        start_time = time.time()
    logger.info(f"[DEBUG router.wait_for_robot_status] expected={expected_method}, timeout={timeout}, task_no={task_no}")
    logger.debug(f"开始等待机器人状态: {expected_method}, 超时: {timeout}秒, task_no={task_no}")

    while True:
        # 先从队列中查找匹配的 END（防止已有 END 在队列中等待）
        for j in range(len(_robot_status_queue) - 1, -1, -1):
            item = _robot_status_queue[j]
            if item.get("method") != expected_method:
                continue
            # 按 task_no 过滤：不属于当前任务的 END 保留在队列中，不消费
            # task_no 不匹配时直接跳过，不检查 valid_robot_codes
            if task_no:
                item_task_no = item.get("task_no", "")
                if item_task_no and item_task_no != task_no:
                    logger.debug(f"跳过队列中的非本任务 END (task_no={item_task_no}, binCode={item.get('binCode', '')}), 保留在队列")
                    continue
            # task_no 匹配（或未提供），才按 robotTaskCode 过滤（兼容旧逻辑）
            if valid_robot_codes is not None:
                item_code = item.get("robotTaskCode", "")
                if item_code and item_code not in valid_robot_codes:
                    debug_logger.debug(f"[RCS回调] END的robotTaskCode不匹配！期望={valid_robot_codes}，实际={item_code}，slotName={item.get('binCode', '')}，保留在队列等待")
                    continue
            # 命中，弹出并返回
            del _robot_status_queue[j]
            logger.info(f"从队列中取出期望状态: {expected_method}，binCode={item.get('binCode', '')}，task_no={item.get('task_no', '')}，剩余: {len(_robot_status_queue)}")
            # 队列非空时不清除事件，让下一轮立即处理剩余 END
            if not _robot_status_queue:
                _status_event.clear()
            return item

        elapsed = time.time() - start_time
        remaining = timeout - elapsed
        if remaining <= 0:
            raise asyncio.TimeoutError(f"等待 {expected_method} 状态超时")

        try:
            # 等待剩余全部时间（不再固定 1 秒），避免长处理期间漏掉回调
            await asyncio.wait_for(_status_event.wait(), timeout=remaining)
        except asyncio.TimeoutError:
            # 只有队列空时才清除事件，防止已到达的回调被漏掉
            if not _robot_status_queue:
                _status_event.clear()
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise asyncio.TimeoutError(f"等待 {expected_method} 状态超时")
            # 正常轮询超时（sim 模式下 RCS 移动需要 15 秒），不打印日志直接继续
            continue
            # 只有队列空时才清除事件，防止已到达的回调被漏掉
            if not _robot_status_queue:
                _status_event.clear()
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise asyncio.TimeoutError(f"等待 {expected_method} 状态超时")
            continue



@router.post("/reporter/task")
async def task_status(request: Request):
    """机器人任务状态反馈接口"""
    try:
        request_data = await request.json()
        logger.info("反馈任务状态")
        rcs_logger.info(f"【RCS回调请求】data={json.dumps(request_data, ensure_ascii=False)}")
        logger.info(f"【RCS回调请求】data={json.dumps(request_data, ensure_ascii=False)}")

        robot_task_code = request_data.get("robotTaskCode")
        single_robot_code = request_data.get("singleRobotCode")
        extra = request_data.get("extra", "")

        # extra 字段完整打印（不管有没有值）
        if extra:
            if isinstance(extra, str):
                logger.info(f"RCS extra（字符串）: {extra}")
            else:
                logger.info(f"RCS extra（对象）: {json.dumps(extra, ensure_ascii=False)}")
        else:
            logger.info("RCS extra 字段为空，无额外信息")

        if extra:
            try:
                # extra 可能是 dict（真实RCS）或 JSON 字符串（模拟RCS）
                if isinstance(extra, str):
                    extra_data = json.loads(extra)
                else:
                    extra_data = extra

                # 真实 RCS: extra_data 是 {"async": "0", "values": {...}}
                # 模拟 RCS: extra_data 是 [{"method": ..., "data": {...}}]
                if isinstance(extra_data, list):
                    for item in extra_data:
                        values = item.get("values") or item
                        method = values.get("method", "")
                        location_data = item.get("data") or {}
                        if location_data and "location" in location_data:
                            values["location"] = location_data["location"]
                        logger.info(f"处理method: {method}")
                        await update_robot_status(method, values, robot_task_code=robot_task_code)
                        if method == "start":
                            location = values.get("location", "")
                            if location and robot_task_code:
                                _bin_to_robot_code[location] = robot_task_code
                            logger.info("任务开始")
                        elif method == "outbin":
                            logger.info("走出储位")
                        elif method == "end":
                            logger.info("任务完成")
                elif isinstance(extra_data, dict):
                    values = extra_data.get("values") or extra_data
                    method = values.get("method", "")
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
            except Exception as e:
                logger.error(f"处理 RCS 回调失败: {e}")

        response_body = {
            "code": "SUCCESS",
            "message": "成功",
            "data": {"robotTaskCode": robot_task_code or "ctu001"}
        }
        rcs_logger.info(f"【RCS回调响应】body={json.dumps(response_body, ensure_ascii=False)}")
        logger.info(f"【RCS回调响应】body={json.dumps(response_body, ensure_ascii=False)}")
        return response_body

    except Exception as e:
        logger.error(f"处理状态反馈失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理状态反馈失败: {str(e)}")
