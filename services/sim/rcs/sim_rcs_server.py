'''
Author: big box big box@qq.com
Date: 2025-10-20 23:13:24
LastEditors: big box big box@qq.com
LastEditTime: 2026-03-14 16:44:18
FilePath: /Leafdepot/services/sim/rcs/sim_rcs_server.py
Description: 

Copyright (c) 2025 by lizh, All Rights Reserved. 
'''
# main.py
from fastapi import FastAPI, BackgroundTasks, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import uuid
import time
import logging
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import hashlib
import hmac
import json
import aiohttp
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from services.api.shared.config import _HOST, GATEWAY_PORT, CAMSYS_PORT, CORS_ORIGINS

app = FastAPI(
    title="RCS-2000",
    description="模拟RCS-2000系统处理盘点任务清单",
    version="1.0.0"
)

GATEWAY_URL = f"http://{_HOST}:{GATEWAY_PORT}"


# 允许的源（从共享配置读取）
origins = CORS_ORIGINS

# 将 CORS 中间件添加到应用
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RobotTaskSimulator:
    """机器人任务模拟器"""

    # 任务组记录（robot_task_code → task_group）
    task_groups: Dict[str, dict] = {}

    # 全局顺序 Event：每次 gateway 发 continue，触发等待中的最早 END
    _pending_continue_event: asyncio.Event = asyncio.Event()

    # 回调地址
    callback_url = f"http://{_HOST}:{GATEWAY_PORT}/api/robot/reporter/task"

    @classmethod
    async def submit_and_run(cls, robot_task_code: str, target_route: List[dict], task_type: str):
        """
        提交并执行任务：每个 submit 独立运行，互不阻塞。
        内部用 asyncio.create_task 启动 bin 执行（第一个 bin 立即发 END，后续等 continue）。
        """
        if robot_task_code not in cls.task_groups:
            cls.task_groups[robot_task_code] = {
                "robot_task_code": robot_task_code,
                "target_route": target_route,
                "task_type": task_type,
                "current_index": 0,
                "total_tasks": len(target_route),
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "completed_tasks": [],
                "last_update": datetime.now().isoformat()
            }

        task_group = cls.task_groups[robot_task_code]

        # 用 create_task 启动，不阻塞 HTTP 响应
        asyncio.create_task(cls._run_task(robot_task_code))

    @classmethod
    async def _run_task(cls, robot_task_code: str):
        """逐个 bin 执行：第一个立即 END，后续等 continue"""
        if robot_task_code not in cls.task_groups:
            return
        task_group = cls.task_groups[robot_task_code]

        for i in range(task_group["total_tasks"]):
            route_item = task_group["target_route"][i]
            location = route_item.get("code", "")

            # START
            await cls.send_callback(robot_task_code, "start", {
                "location": location,
                "task_index": i,
                "total_tasks": task_group["total_tasks"]
            })

            # 模拟移动到目标
            await asyncio.sleep(0.1)

            # OUTBIN
            await cls.send_callback(robot_task_code, "outbin", {
                "location": location,
                "progress": "moving_to_location"
            })

            # 模拟执行任务
            await asyncio.sleep(0.1)

            task_group["current_index"] = i + 1
            task_group["last_update"] = datetime.now().isoformat()

            if i == 0:
                # 第一个 bin：直接发 END（不等 continue）
                await cls.send_callback(robot_task_code, "end", {
                    "location": location,
                    "task_index": i,
                    "result": "success"
                })
                logger.info(f"任务 {robot_task_code} bin 1 ({location}) END 已发（不等 continue）")
                # 等 continue 才触发下一个 bin
                if task_group["total_tasks"] > 1:
                    cls._pending_continue_event.clear()
                    await cls._pending_continue_event.wait()
            else:
                # 后续 bin：等 continue 才发 END
                logger.info(f"任务 {robot_task_code} bin {i+1} ({location}) 完成，等 continue...")
                cls._pending_continue_event.clear()
                await cls._pending_continue_event.wait()
                await cls.send_callback(robot_task_code, "end", {
                    "location": location,
                    "task_index": i,
                    "result": "success"
                })
                logger.info(f"任务 {robot_task_code} bin {i+1} ({location}) END 已发")
                # 发完 END 继续等 continue
                if i < task_group["total_tasks"] - 1:
                    cls._pending_continue_event.clear()
                    await cls._pending_continue_event.wait()

        task_group["status"] = "completed"
        logger.info(f"任务 {robot_task_code} 全部 {task_group['total_tasks']} 个 bin 执行完毕")

    @classmethod
    async def continue_task(cls, robot_task_code: str):
        """收到 continue，触发全局顺序信号（如果任务已完成则忽略）"""
        task_group = cls.task_groups.get(robot_task_code)
        if task_group and task_group.get("status") == "completed":
            logger.info(f"收到 continue，但任务 {robot_task_code} 已完成，忽略")
            return
        cls._pending_continue_event.set()
        logger.info(f"收到 continue，触发下一 bin")

    @classmethod
    async def send_callback(cls, robot_task_code: str, method: str, data: dict):
        """
        发送状态回调到您的系统
        """
        extra_data = {
            "method": method,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        callback_payload = {
            "robotTaskCode": robot_task_code,
            "singleRobotCode": "ROBOT001",  # 模拟机器人编号
            "extra": json.dumps([extra_data])
        }

        try:
           # 使用aiohttp发送异步请求
            connector = aiohttp.TCPConnector(ssl=False)  # 对于本地开发，可以禁用SSL验证

            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    cls.callback_url,
                    json=callback_payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10.0)
                ) as response:
                    if response.status == 200:
                        logger.info(f"成功发送回调: {method} - 任务 {robot_task_code}")
                    else:
                        response_text = await response.text()
                        logger.error(
                            f"回调发送失败: {response.status} - {response_text}")

        except Exception as e:
            logger.error(f"发送回调时发生错误: {str(e)}")

    @classmethod
    def get_task_status(cls, robot_task_code: str) -> Optional[dict]:
        """获取任务状态"""
        if robot_task_code in cls.task_groups:
            return cls.task_groups[robot_task_code]
        return None

    @classmethod
    def get_all_tasks(cls) -> dict:
        """获取所有任务状态"""
        return {
            "all_task_groups": cls.task_groups
        }


service_prefix = "/rcs/rtas"


@app.post(service_prefix + "/api/robot/controller/task/submit")
async def submit_inventory_task(request: Request):
    """专门处理盘点任务提交"""
    try:
        # 获取请求数据
        request_data = await request.json()

        logger.info("收到盘点任务提交请求")
        logger.info(
            f"请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")

        # 提取任务信息 - 单个任务对象
        task_type = request_data.get("taskType", "")
        target_route = request_data.get("targetRoute", [])

        if not target_route:
            raise HTTPException(status_code=400, detail="targetRoute不能为空")

        # 模拟处理延时
        logger.info(
            f"处理盘点任务: taskType={task_type}, 包含 {len(target_route)} 个储位")
        # 生成唯一的机器人任务代码
        robot_task_code = f"ROBOT-TASK-{uuid.uuid4().hex[:8].upper()}"

        logger.info(f"生成机器人任务代码: {robot_task_code}")

        # 立即返回响应（不阻塞 gateway 的 HTTP 请求）
        # 每个 submit 独立执行，互不阻塞
        await RobotTaskSimulator.submit_and_run(robot_task_code, target_route, task_type)

        # 返回响应（立即返回，不等待任务执行完成）
        return {
            "code": "SUCCESS",
            "message": "成功",
            "data": {
                "robotTaskCode": robot_task_code,
                "extra": None
            }
        }

    except Exception as e:
        logger.error(f"处理盘点任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理盘点任务失败: {str(e)}")


@app.post(service_prefix + "/api/robot/controller/task/extend/continue")
async def continue_inventory_task(request: Request):
    try:
        # 获取请求数据
        request_data = await request.json()

        logger.info("收到盘点任务继续请求")
        logger.info(
            f"请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")

        # 获取机器人任务代码
        robot_task_code = request_data.get("robotTaskCode", "ctu001")

        # 调用继续任务方法
        success = await RobotTaskSimulator.continue_task(robot_task_code)

        # 返回响应
        return {
            "code": "SUCCESS",
            "message": "成功",
            "data": {
                "robotTaskCode": robot_task_code,
                "nextSeq": 1,
                "extra": None
            }
        }

    except Exception as e:
        logger.error(f"继续盘点任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"继续盘点任务失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4001)
