'''
Author: big box big box@qq.com
Date: 2025-10-20 23:13:24
LastEditors: big box big box@qq.com
LastEditTime: 2025-10-27 23:16:03
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
from typing import Dict
import logging
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import hashlib
import hmac
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RCS-2000",
    description="模拟RCS-2000系统处理盘点任务清单",
    version="1.0.0"
)

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

service_prefix = "/rcs/rtas"

# 存储任务组信息的内存数据库
task_groups_db = {}

# 请求和响应模型


class TargetRoute(BaseModel):
    type: str = Field(..., description="目标类型: SITE-站点别名, ZONE-目标所处区域编号")
    code: str = Field(..., description="目标编号")


class TaskData(BaseModel):
    robotTaskCode: str = Field(..., description="任务号，全局唯一")
    sequence: Optional[int] = Field(None, description="任务顺序(数字)，从1开始到9999")


class TaskGroupRequest(BaseModel):
    groupCode: Optional[str] = Field(None, description="任务组编号，全局唯一")
    strategy: str = Field(...,
                          description="执行策略: GROUP_SEQ, GROUP_ASSIGN, GROUP_CARRIER_ADJUST")
    strategyValue: Optional[str] = Field(None, description="策略值")
    groupSeq: Optional[int] = Field(None, description="组顺序(数字)，从1到9999999999")
    targetRoute: Optional[TargetRoute] = Field(
        None, description="执行任务的下一个目标位置")
    data: List[TaskData] = Field(..., description="任务数据列表")


class TaskGroupResponse(BaseModel):
    code: str = Field(..., description="消息码")
    message: str = Field(..., description="消息内容")

# 任务组接口


@app.post(service_prefix + "/api/robot/controller/task/group")
async def create_task_group(request: TaskGroupRequest):

    try:
        # 验证必要参数
        if not request.data:
            raise HTTPException(status_code=400, detail="任务数据不能为空")

        if not request.strategy:
            raise HTTPException(status_code=400, detail="执行策略不能为空")

        # 验证策略值
        valid_strategies = ["GROUP_SEQ",
                            "GROUP_ASSIGN", "GROUP_CARRIER_ADJUST"]
        if request.strategy not in valid_strategies:
            raise HTTPException(
                status_code=400, detail=f"不支持的策略类型: {request.strategy}")

        # 验证任务顺序
        sequences = [
            task.sequence for task in request.data if task.sequence is not None]
        if sequences and len(sequences) != len(set(sequences)):
            raise HTTPException(status_code=400, detail="任务顺序不能重复")

        # 生成任务组编号（如果未提供）
        group_code = request.groupCode or str(
            uuid.uuid4()).replace("-", "")[:32]

        # 存储任务组信息
        task_group_info = {
            "groupCode": group_code,
            "strategy": request.strategy,
            "strategyValue": request.strategyValue,
            "groupSeq": request.groupSeq,
            "targetRoute": request.targetRoute.model_dump() if request.targetRoute else None,
            "data": [task.model_dump() for task in request.data],
        }

        task_groups_db[group_code] = task_group_info

        # 返回成功响应
        return JSONResponse(
            status_code=200,
            content={
                "code": "SUCCESS",
                "message": "成功"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        # 记录错误日志
        print(f"创建任务组时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.get(service_prefix + "/api/robot/controller/task/progress/{task_no}")
async def get_task_progress(task_no: str):
    """查询任务进度"""
    try:
        # 模拟任务进度数据
        # 在实际场景中，这里应该查询真实的任务状态
        
        # 查找任务组（简化实现）
        task_info = None
        for group_code, group_info in task_groups_db.items():
            for task_data in group_info.get("data", []):
                if task_data.get("robotTaskCode") == task_no:
                    task_info = task_data
                    break
            if task_info:
                break
        
        if not task_info:
            raise HTTPException(status_code=404, detail=f"未找到任务: {task_no}")
        
        # 模拟任务进度（可以根据实际情况修改）
        import random
        progress = min(random.randint(70, 95), 100)  # 模拟进度在70-95%之间
        
        # 模拟已完成的任务列表（包含图片路径信息）
        completed_tasks = []
        # 假设每个任务都有对应的库位和图片
        # 这里模拟返回一些已完成的任务数据
        for i in range(min(3, len(task_groups_db.get(list(task_groups_db.keys())[0], {}).get("data", [])))):
            completed_tasks.append({
                "taskDetailId": f"DT{i+1}",
                "binCode": f"BIN00{i+1}",
                "imagePath": f"services/sim/cam_sys/camera_images/simulated_sd_{task_no}_BIN00{i+1}.png",  # 模拟图片路径
                "countedQty": random.randint(50, 100)
            })
        
        status = "COMPLETED" if progress >= 100 else "IN_PROGRESS"
        
        return {
            "success": True,
            "data": {
                "taskNo": task_no,
                "status": status,
                "progress": progress,
                "completedTasks": completed_tasks,
                "totalTasks": len(task_groups_db.get(list(task_groups_db.keys())[0], {}).get("data", [])) if task_groups_db else 0
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询任务进度异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询任务进度失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4001)
