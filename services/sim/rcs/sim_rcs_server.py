'''
Author: big box big box@qq.com
Date: 2025-10-20 23:13:24
LastEditors: big box big box@qq.com
LastEditTime: 2025-12-14 12:51:25
FilePath: /rcs/sim_rcs_server.py
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

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RCS-2000",
    description="模拟RCS-2000系统处理盘点任务清单",
    version="1.0.0"
)

GATEWAY_URL = "http://localhost:8000"


# 定义允许的源列表
origins = [
    "http://localhost",
    "http://localhost:8000",  # 内部网关端口
    "http://localhost:5000",  # CamSys
]

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

    # 存储所有任务组
    task_groups: Dict[str, dict] = {}

    # 存储当前执行中的任务
    active_tasks: Dict[str, dict] = {}

    # 等待继续的任务队列
    paused_tasks: Dict[str, dict] = {}

    # 回调地址（假设您的系统地址）
    callback_url = "http://localhost:8000/api/robot/reporter/task"

    @classmethod
    async def simulate_task_execution(cls, robot_task_code: str, target_route: List[dict], task_type: str):
        """
        模拟机器人任务执行
        """
        if robot_task_code not in cls.task_groups:
            cls.task_groups[robot_task_code] = {
                "robot_task_code": robot_task_code,
                "target_route": target_route,
                "task_type": task_type,
                "current_index": 0,
                "total_tasks": len(target_route),
                "status": "initialized",  # initialized, running, paused, completed
                "start_time": datetime.now().isoformat(),
                "completed_tasks": [],
                "current_location": None,
                "last_update": datetime.now().isoformat()
            }

        task_group = cls.task_groups[robot_task_code]
        task_group["status"] = "running"

        # 开始执行第一个任务
        await cls.execute_single_task(robot_task_code, 0)

    @classmethod
    async def execute_single_task(cls, robot_task_code: str, task_index: int):
        """
        执行单个任务
        """
        if robot_task_code not in cls.task_groups:
            return

        task_group = cls.task_groups[robot_task_code]

        # 检查索引是否有效
        if task_index >= len(task_group["target_route"]):
            # 所有任务完成
            task_group["status"] = "completed"
            await cls.send_callback(robot_task_code, "end", task_group)
            return

        # 更新当前任务索引
        task_group["current_index"] = task_index
        route_item = task_group["target_route"][task_index]
        location = route_item.get("code", "")

        # 存储当前活动任务
        cls.active_tasks[robot_task_code] = {
            "task_index": task_index,
            "location": location,
            "start_time": datetime.now().isoformat(),
            "status": "starting"
        }

        # 任务开始 - 反馈状态
        await cls.send_callback(robot_task_code, "start", {
            "location": location,
            "task_index": task_index,
            "total_tasks": task_group["total_tasks"]
        })

        # 等待一段时间（模拟移动到目标）
        await asyncio.sleep(1)

        # 任务进行中 - 反馈状态
        await cls.send_callback(robot_task_code, "outbin", {
            "location": location,
            "progress": "moving_to_location"
        })

        # 模拟执行任务（总共5秒）
        await asyncio.sleep(3)

        # 任务完成 - 反馈状态
        await cls.send_callback(robot_task_code, "end", {
            "location": location,
            "task_index": task_index,
            "result": "success"
        })

        # 记录完成的任务
        if "completed_tasks" not in task_group:
            task_group["completed_tasks"] = []
        task_group["completed_tasks"].append({
            "location": location,
            "index": task_index,
            "completion_time": datetime.now().isoformat()
        })

        # 从活动任务中移除
        if robot_task_code in cls.active_tasks:
            del cls.active_tasks[robot_task_code]

        # 将任务组放入暂停队列，等待继续指令
        task_group["status"] = "paused"
        task_group["last_update"] = datetime.now().isoformat()
        cls.paused_tasks[robot_task_code] = task_group

        logger.info(f"任务 {robot_task_code} 的第 {task_index + 1} 个任务已完成，等待继续指令")

        await cls.continue_task(robot_task_code)

    @classmethod
    async def continue_task(cls, robot_task_code: str):
        """
        继续执行下一个任务
        """
        if robot_task_code not in cls.paused_tasks:
            logger.warning(f"任务 {robot_task_code} 不在暂停队列中")
            return False

        task_group = cls.paused_tasks[robot_task_code]

        # 计算下一个任务索引
        next_index = task_group["current_index"] + 1

        # 如果所有任务都已完成
        if next_index >= task_group["total_tasks"]:
            logger.info(f"任务 {robot_task_code} 所有任务已完成")
            task_group["status"] = "completed"
            # 发送最终完成回调
            # await cls.send_callback(robot_task_code, "end", {
            #     "total_tasks": task_group["total_tasks"],
            #     "completed_tasks": len(task_group["completed_tasks"])
            # })
            del cls.paused_tasks[robot_task_code]
            return True

        # 从暂停队列中移除
        del cls.paused_tasks[robot_task_code]

        # 执行下一个任务
        await cls.execute_single_task(robot_task_code, next_index)
        return True

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
            "active_tasks": cls.active_tasks,
            "paused_tasks": cls.paused_tasks,
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
        timestamp = int(time.time())
        robot_task_code = f"ROBOT-TASK-{timestamp}"

        logger.info(f"生成机器人任务代码: {robot_task_code}")

        # 异步启动任务模拟
        asyncio.create_task(
            RobotTaskSimulator.simulate_task_execution(
                robot_task_code, target_route, task_type)
        )

        # 返回响应
        return {
            "code": "SUCCESS",
            "message": "成功",
            "data": {
                "robotTaskCode": "ctu001",
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

        # 返回响应
        return {
            "code": "SUCCESS",
            "message": "成功",
            "data": {
                "robotTaskCode": "ctu001",
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
