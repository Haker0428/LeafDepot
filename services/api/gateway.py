# gateway.py
from fastapi.security import APIKeyHeader
from pathlib import Path
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi import FastAPI, Request, HTTPException, status, Header, BackgroundTasks
from fastapi.responses import JSONResponse, Response
import requests
import json
import logging
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import custom_utils
import uuid
import time
import asyncio
from typing import Dict, List, Optional, Any, Union
import base64
from datetime import datetime
from pydantic import BaseModel, Field
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 模拟服务的地址
LMS_BASE_URL = "http://localhost:6000"
RCS_BASE_URL = "http://localhost:4001"
CAMERA_BASE_URL = "http://localhost:5000"
RCS_PREFIX = "/rcs/rtas"
REAL_RCS_BASE_URL = "http://10.4.180.190:80/rcs/rtas"

app = FastAPI(title="Gateway", version="1.0.0")

# 定义允许的源列表
origins = [
    "http://localhost",
    "http://localhost:3000",  # UI
    "http://localhost:4001",  # RCS
    "http://localhost:5000",  # CamSys
    "http://localhost:6000"  # LMS
]

# 将 CORS 中间件添加到应用
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

robot_status_store = {}
status_events = {}
task_timeouts = {}


STATUS_KEY = "ldui_2025"  # 固定状态键
status_event = asyncio.Event()  # 单个事件对象
robot_status_store: Dict[str, Any] = {}  # 状态存储
TASK_TIMEOUT = 300  # 超时时间（秒）


# 抓图脚本路径配置
CAPTURE_SCRIPTS = [
    "../cam_sys_ok/build/3d_capture.py",  # 第一个抓图脚本
    "../cam_sys_ok/build/scan_1_capture.py",  # 第二个抓图脚本
    "../cam_sys_ok/build/scan_2_capture.py"   # 第三个抓图脚本
]


class TaskStatus(BaseModel):
    task_no: str
    status: str  # init, running, completed, failed
    current_step: int
    total_steps: int


# 全局任务状态存储（生产环境建议使用数据库或Redis）
inventory_tasks: Dict[str, TaskStatus] = {}

######################################### 盘点任务接口 #########################################


@app.post("/api/inventory/start-inventory")
async def start_inventory(request: Request, background_tasks: BackgroundTasks):
    """启动盘点任务，接收任务编号和储位名称列表"""
    try:
        data = await request.json()
        task_no = data.get("taskNo")
        bin_locations = data.get("binLocations", [])

        if not task_no or not bin_locations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="任务编号和储位名称列表不能为空"
            )

        logger.info(f"启动盘点任务: {task_no}, 包含 {len(bin_locations)} 个储位")

        # 检查任务是否已存在
        target_route = []
        for index, location in enumerate(bin_locations):
            if location in inventory_tasks:
                existing_task = inventory_tasks[location]
                if existing_task.status in ["running"]:
                    return JSONResponse(
                        status_code=status.HTTP_200_OK,
                        content={
                            "code": 200,
                            "message": "任务已在执行中",
                            "data": {
                                "taskNo": existing_task.task_no,
                                "status": existing_task.status,
                            }
                        }
                    )

        # 在后台异步执行盘点任务
        background_tasks.add_task(
            execute_inventory_workflow,
            task_no=task_no,
            bin_locations=bin_locations
        )

        # 1.调用盘点任务下发接口

        # 2.实时接收盘点任务执行状态

        # 3.机器人就位后调用抓图接口

        # 4.抓图成功后调用计算接口，向前端发送图片

        # 5.计算完成后向前端反馈状态，并向前端发送图片

        # 6.调用继续任务接口，重复上述过程，直到全部任务完成

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": 200,
                "message": "盘点任务已启动",
                "data": {
                    "taskNo": task_no,
                    "bin_locations": bin_locations
                }
            }
        )

    except Exception as e:
        logger.error(f"启动盘点任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动盘点任务失败: {str(e)}"
        )


async def execute_inventory_workflow(task_no: str, bin_locations: List[str]):
    """执行完整的盘点工作流"""
    logger.info(f"开始执行盘点工作流: {task_no}, 共 {len(bin_locations)} 个储位")

    # 初始化任务状态
    task_status = TaskStatus(
        task_no=task_no,
        status="init",
        current_step=1,
        total_steps=len(bin_locations)
    )

    for index, location in enumerate(bin_locations):
        inventory_tasks[location] = task_status

    # 整体下发盘点任务
    method = "start"
    await update_robot_status(method)

    submit_result = await submit_inventory_task(task_no, bin_locations)

    try:
        # 循环处理每个储位
        for i, bin_location in enumerate(bin_locations):
            logger.info(f"开始处理储位 {i+1}/{len(bin_locations)}: {bin_location}")

            # 处理单个储位
            result = await process_single_bin_location(
                task_no=task_no,
                bin_location=bin_location,
                index=i,
                total=len(bin_locations)
            )

            # 保存结果
            if (result["status"] == "success"):
                inventory_tasks[bin_location].status = "completed"
            else:
                inventory_tasks[bin_location].status = "failed"
                raise Exception("储位处理失败，终止任务")

        logger.info(f"盘点任务完成: {task_no}, 成功处理 {len(bin_locations)} 个储位")

        # 发送任务完成通知
        # try:
        #     async with APIClient(SERVICE_CONFIG["notification_service"]) as client:
        #         completion_payload = {
        #             "taskNo": task_no,
        #             "status": "COMPLETED",
        #             "totalBins": len(bin_locations),
        #             "successfulBins": sum(1 for r in inventory_tasks[task_no].results
        #                                   if r.get("status") == "completed"),
        #             "failedBins": sum(1 for r in inventory_tasks[task_no].results
        #                               if r.get("status") == "failed"),
        #             "completionTime": datetime.now().isoformat(),
        #             "messageType": "TASK_COMPLETED"
        #         }
        #         await client.post("/api/notification/task-complete", json=completion_payload)
        # except Exception as e:
        #     logger.warning(f"发送任务完成通知失败: {str(e)}")

    except Exception as e:
        # 任务执行过程中出现异常
        logger.error(f"盘点任务失败: {task_no}, 错误: {str(e)}")

        # 发送任务失败通知
        # try:
        #     async with APIClient(SERVICE_CONFIG["notification_service"]) as client:
        #         error_payload = {
        #             "taskNo": task_no,
        #             "status": "FAILED",
        #             "error": str(e),
        #             "failedAtBin": inventory_tasks[task_no].current_bin,
        #             "completedBins": len(inventory_tasks[task_no].results),
        #             "timestamp": datetime.now().isoformat(),
        #             "messageType": "TASK_FAILED"
        #         }
        #         await client.post("/api/notification/task-error", json=error_payload)
        # except Exception as e2:
        #     logger.error(f"发送任务失败通知失败: {str(e2)}")


async def process_single_bin_location(task_no: str, bin_location: str, index: int, total: int):
    """处理单个储位的完整流程"""
    result = {
        "binLocation": bin_location,
        "sequence": index + 1,
        "startTime": datetime.now().isoformat(),
        "endTime": None,
        "status": None
    }

    try:
        # 更新任务状态
        if bin_location in inventory_tasks:
            inventory_tasks[bin_location].status = "running"
            inventory_tasks[bin_location].current_step = index + 1

            # 等待机器人就位
            logger.info(f"============等待机器人就位信息: {bin_location}")
            try:
                ctu_status = await wait_for_robot_status("end", timeout=300)

                # 这个判断一定会执行，因为wait_for_robot_status会阻塞直到收到end状态或超时
                if ctu_status and ctu_status.get("method") == "end":

                    # 执行抓图脚本
                    capture_results = await capture_images_with_scripts(task_no, bin_location)
                    result["captureResults"] = capture_results

                    # 检查抓图结果
                    successful_scripts = sum(
                        1 for r in capture_results if r.get("success"))
                    if successful_scripts < len(CAPTURE_SCRIPTS):
                        logger.warning(
                            f"部分抓图脚本执行失败: {successful_scripts}/{len(CAPTURE_SCRIPTS)}")
                    else:
                        logger.info(f"所有抓图脚本执行成功: {bin_location}")

                    if ((index + 1) < total):
                        logger.info(f"收到机器人结束状态: {bin_location}")

                        # 只有在收到end状态后才调用继续任务接口
                        continue_result = await continue_inventory_task()
                        logger.info(f"继续任务接口调用结果: {continue_result}")
                        result["continueResult"] = continue_result

                else:
                    # 正常情况下不会执行到这里，除非wait_for_robot_status返回了非end状态
                    logger.warning(f"未收到预期的结束状态，当前状态: {ctu_status}")

            except asyncio.TimeoutError as e:
                logger.error(f"等待机器人结束状态超时: {str(e)}")
                result["error"] = "等待机器人结束状态超时"
                raise

            # # 2. 机器人就位后调用抓图接口
            # image_data = await capture_image(task_no, bin_location)
            # result["imageData"] = image_data
            # result["captureTime"] = image_data.get("captureTime")

            # # 3. 抓图成功后调用计算接口
            # compute_result = await compute_inventory(task_no, bin_location, image_data)
            # result["computeResult"] = compute_result
            # result["computeTime"] = datetime.now().isoformat()

            # # 4. 向前端发送图片和计算结果
            # await send_to_frontend(task_no, bin_location, image_data, compute_result)

            result["status"] = "success"
            result["endTime"] = datetime.now().isoformat()

    except Exception as e:
        result["status"] = "failed"
        result["endTime"] = datetime.now().isoformat()
        logger.error(f"处理储位失败 {bin_location}: {str(e)}")

        # 记录错误但继续处理下一个储位（根据业务需求决定是否中断）
        # 可以发送错误通知到前端
        # try:
        #     async with APIClient(SERVICE_CONFIG["notification_service"]) as client:
        #         error_payload = {
        #             "taskNo": task_no,
        #             "binLocation": bin_location,
        #             "error": str(e),
        #             "timestamp": datetime.now().isoformat(),
        #             "messageType": "ERROR"
        #         }
        #         await client.post("/api/notification/error", json=error_payload)
        # except:
        #     pass

    return result
######################################### 盘点任务接口 #########################################


######################################### LMS #########################################


@app.post("/login")
async def login(request: Request):
    """处理前端登录请求，调用LMS的login接口"""
    try:
        # 从前端获取用户名和密码
        data = await request.json()
        username = data.get("username")
        password = data.get("password")

        # 验证输入
        if not username or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名和密码不能为空"
            )

        # 调用LMS的login接口
        lms_login_url = f"{LMS_BASE_URL}/login"
        headers = {
            "userCode": username,
            "password": password
        }
        response = requests.get(lms_login_url, headers=headers)

        if response.status_code == 200:
            # 获取LMS返回的token
            lms_response = response.json()
            token = lms_response.get("authToken")

            if not token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="登录成功但未返回authToken"
                )

            # 返回给前端的响应
            return {
                "success": True,
                "data": {
                    "userId": lms_response.get("userId"),
                    "userCode": lms_response.get("userCode"),
                    "userName": lms_response.get("userName"),
                    "authToken": token
                }
            }
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"LMS登录失败: {response.text}"
            )
    except Exception as e:
        logger.error(f"登录请求失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录请求处理失败"
        )


@app.get("/auth/token")
async def auth_token(token: str):
    """处理前端获取用户信息请求，调用LMS的authToken接口"""
    try:
        # 调用LMS的authToken接口
        lms_auth_url = f"{LMS_BASE_URL}/auth/token?token={token}"
        response = requests.get(lms_auth_url)

        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"LMS获取用户信息失败: {response.text}"
            )
    except Exception as e:
        logger.error(f"获取用户信息请求失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息请求处理失败"
        )


@app.get("/lms/getLmsBin")
async def get_lms_bin(authToken: str):
    """获取库位信息，调用LMS的getLmsBin接口"""
    try:
        # 调用LMS的getLmsBin接口
        lms_bin_url = f"{LMS_BASE_URL}/third/api/v1/lmsToRcsService/getLmsBin"
        headers = {
            "authToken": authToken
        }
        response = requests.get(lms_bin_url, headers=headers)

        if response.status_code == 200:
            # 关键修复：处理LMS返回的压缩编码字符串
            try:
                uncompressed_data = custom_utils.decompress_and_decode(
                    response.text)

                logger.info("成功解压缩并解析库位数据")
                return JSONResponse(uncompressed_data)
            except Exception as e:
                logger.error(f"解压缩库位数据失败: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="库位数据解压缩失败"
                )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"LMS获取库位信息失败: {response.text}"
            )
    except Exception as e:
        logger.error(f"获取库位信息请求失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取库位信息请求处理失败"
        )


@app.get("/lms/getCountTasks")
async def get_count_tasks(authToken: str):
    """获取盘点任务，调用LMS的getCountTasks接口"""
    try:
        logger.info(f"收到获取盘点任务请求，authToken: {authToken[:20]}...")

        lms_tasks_url = f"{LMS_BASE_URL}/third/api/v1/lmsToRcsService/getCountTasks"
        logger.info(f"准备调用LMS接口: {lms_tasks_url}")

        headers = {"authToken": authToken}
        logger.info("发送请求到LMS服务...")
        response = requests.get(lms_tasks_url, headers=headers, timeout=30)
        logger.info(f"LMS响应状态码: {response.status_code}")

        if response.status_code == 200:
            # 关键修复：处理LMS返回的压缩编码字符串
            try:
                uncompressed_data = custom_utils.decompress_and_decode(
                    response.text)

                logger.info("成功解压缩并解析盘点任务数据")
                return JSONResponse(uncompressed_data)
            except Exception as e:
                logger.error(f"解压缩盘点任务数据失败: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="盘点任务数据解压缩失败"
                )
        else:
            logger.error(
                f"LMS获取盘点任务失败: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"LMS获取盘点任务失败: {response.text}"
            )
    except requests.exceptions.Timeout:
        logger.error("LMS服务请求超时")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="LMS服务响应超时"
        )
    except requests.exceptions.ConnectionError:
        logger.error("无法连接到LMS服务")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="无法连接到LMS服务"
        )
    except Exception as e:
        logger.error(f"获取盘点任务请求失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取盘点任务请求处理失败"
        )


@app.post("/lms/setTaskResults")
async def set_task_results(request: Request):
    """提交盘点任务结果，调用LMS的setTaskResults接口"""
    try:
        # 1. 从请求头获取authToken
        auth_token = request.headers.get('authToken')
        if not auth_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized"
            )

        # 2. 从请求体获取JSON数据（前端发送的是标准JSON）
        data = await request.json()
        encoded_data = custom_utils.compress_and_encode(data)

        # 6. 调用LMS接口（使用压缩后的数据）
        lms_results_url = f"{LMS_BASE_URL}/third/api/v1/RcsToLmsService/setTaskResults"
        headers = {
            "authToken": auth_token,  # 传递给LMS的认证令牌
            "Content-Type": "text/plain"  # 关键：必须是text/plain
        }

        # 发送压缩后的base64字符串
        response = requests.post(
            lms_results_url, data=encoded_data, headers=headers)

        if response.status_code == 200:
            return {"success": True, "message": "盘点结果已提交"}
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"LMS提交盘点结果失败: {response.text}"
            )
    except Exception as e:
        logger.error(f"提交盘点结果请求失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="提交盘点结果请求处理失败"
        )

######################################### RCS #########################################
# @app.post("/api/inventory/submit-task")
# async def submit_inventory_task(request: Request):


async def submit_inventory_task(task_no: str, bin_locations: List[str]):
    """下发盘点任务，接收任务编号和储位名称列表"""
    try:

        logger.info(f"下发盘点任务: {task_no}, 储位: {bin_locations}")

        url = f"{RCS_BASE_URL}{RCS_PREFIX}/api/robot/controller/task/submit"
        headers = {
            "X-lr-request-id": "ldui",
            "Content-Type": "application/json"
        }

        # 构建targetRoute数组
        target_route = []
        for index, location in enumerate(bin_locations):
            route_item = {
                "seq": index,
                "type": "ZONE",
                "code": location,  # 使用储位名称作为目标区域
            }
            target_route.append(route_item)

        # 构建请求体 - 单个任务对象
        request_body = {
            "taskType": "PF-CTU-COMMON-TEST",
            "targetRoute": target_route
        }

        response = requests.post(
            url, json=request_body, headers=headers, timeout=30)

        if response.status_code == 200:
            response_data = response.json()

            if response_data.get("code") == "SUCCESS":
                logger.info(f"储位 {bin_locations} 已发送到机器人系统")
                return {"success": True, "message": "盘点任务已下发"}
        else:
            return {"success": False, "message": "盘点任务下发失败"}

    except Exception as e:
        logger.error(f"下发盘点任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下发盘点任务失败: {str(e)}"
        )


# @app.post("/api/inventory/continue-task")
# async def continue_inventory_task(request: Request):
async def continue_inventory_task():
    """继续盘点任务"""
    try:
        logger.info(f"继续执行盘点任务")

        url = f"{RCS_BASE_URL}{RCS_PREFIX}/api/robot/controller/task/extend/continue"
        headers = {
            "X-lr-request-id": "ldui",
            "Content-Type": "application/json"
        }

        # 构建请求体
        request_body = {
            "triggerType": "TASK",
            "triggerCode": "001"
        }

        response = requests.post(
            url, json=request_body, headers=headers, timeout=30)

        if response.status_code == 200:
            response_data = response.json()

            if response_data.get("code") == "SUCCESS":
                logger.info(f"继续执行盘点任务命令已发送到机器人系统")
                return {"success": True, "message": "盘点任务已继续"}
        else:
            return {"success": False, "message": "盘点任务下发失败"}

    except Exception as e:
        logger.error(f"继续盘点任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"继续盘点任务失败: {str(e)}"
        )


@app.post("/api/robot/reporter/task")
async def task_status(request: Request):
    try:
        # 获取请求数据
        request_data = await request.json()

        logger.info("反馈任务状态")
        logger.info(
            f"请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")

        # 提取任务信息
        robot_task_code = request_data.get("robotTaskCode")
        single_robot_code = request_data.get("singleRobotCode")
        extra = request_data.get("extra", "")

        # 解析extra字段
        if extra:
            try:
                extra_list = json.loads(extra)
                if isinstance(extra_list, list):
                    for item in extra_list:
                        method = item.get("method", "")
                        logger.info(f"处理method: {method}")
                        await update_robot_status(method, item)

                        if method == "start":
                            logger.info("任务开始")

                        elif method == "outbin":
                            logger.info("走出储位")

                        elif method == "end":
                            logger.info("任务完成")

                        # 根据不同的method更新您的任务状态...
            except json.JSONDecodeError:
                logger.error(f"无法解析extra字段: {extra}")

        # 返回响应
        return {
            "code": "SUCCESS",
            "message": "成功",
            "data": {
                "robotTaskCode": "ctu001"
            }
        }

    except Exception as e:
        logger.error(f"处理状态反馈失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理状态反馈失败: {str(e)}")


async def update_robot_status(method: str, data: Optional[Dict] = None):
    """更新机器人状态并触发事件"""
    # 保存状态信息
    robot_status_store[STATUS_KEY] = {
        "method": method,
        "timestamp": time.time(),
        "data": data or {}
    }

    logger.info(f"更新机器人状态: {method}")

    # 设置事件，通知等待的进程
    status_event.set()


async def wait_for_robot_status(expected_method: str, timeout: int = 300):
    """
    等待特定机器人状态的同步函数

    这个函数会阻塞直到收到期望的状态或超时
    """
    logger.info(f"开始等待机器人状态: {expected_method}, 超时: {timeout}秒")

    start_time = time.time()

    # 清除事件，确保我们等待的是新的事件
    status_event.clear()

    # 检查是否已经有期望的状态
    if STATUS_KEY in robot_status_store:
        current_status = robot_status_store[STATUS_KEY]
        if current_status.get("method") == expected_method:
            logger.info(f"已存在期望状态: {expected_method}")
            return current_status

    while True:
        try:
            # 等待事件被设置
            await asyncio.wait_for(status_event.wait(), timeout=1.0)

            # 检查状态
            if STATUS_KEY in robot_status_store:
                current_status = robot_status_store[STATUS_KEY]
                logger.info(f"收到机器人状态: {current_status.get('method')}")

                if current_status.get("method") == expected_method:
                    logger.info(f"收到期望状态: {expected_method}")
                    return current_status

            # 重置事件，准备下一次等待
            status_event.clear()

        except asyncio.TimeoutError:
            # 检查是否总时间超时
            elapsed_time = time.time() - start_time
            if elapsed_time >= timeout:
                logger.error(f"等待机器人状态超时: {expected_method}")
                raise asyncio.TimeoutError(f"等待 {expected_method} 状态超时")

            # 继续等待
            continue

######################################### 抓图 #########################################


async def execute_capture_script(script_path: str, task_no: str, bin_location: str) -> Dict[str, Any]:
    """
    在指定 Conda 环境中执行单个抓图脚本

    Args:
        script_path: 脚本路径
        task_no: 任务编号
        bin_location: 储位名称
        conda_env: Conda 环境名称，默认为 'your_env_name'

    Returns:
        脚本执行结果
    """
    conda_env = "tobacco_env"
    try:
        logger.info(f"在 Conda 环境 '{conda_env}' 中执行抓图脚本: {script_path}")

        # 方法1: 使用 conda run 命令
        # 构建命令行参数
        cmd = ["conda", "run", "-n", conda_env, "python", script_path,
               "--task-no", task_no, "--bin-location", bin_location]

        # 方法2: 直接使用 conda 环境中的 python 路径（如果知道路径）
        # 假设你的 conda 环境路径是已知的
        # conda_python_path = f"/home/user/anaconda3/envs/{conda_env}/bin/python"
        # cmd = [conda_python_path, script_path, "--task-no", task_no, "--bin-location", bin_location]

        # 执行脚本
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # 等待脚本完成
        stdout, stderr = await process.communicate()

        # 解析结果
        result = {
            "script": os.path.basename(script_path),
            "conda_env": conda_env,
            "returncode": process.returncode,
            "stdout": stdout.decode('utf-8') if stdout else "",
            "stderr": stderr.decode('utf-8') if stderr else "",
            "success": process.returncode == 0
        }

        if process.returncode == 0:
            logger.info(f"脚本执行成功: {script_path} (环境: {conda_env})")
        else:
            logger.error(
                f"脚本执行失败: {script_path}, 错误: {stderr.decode('utf-8')}")

        return result

    except FileNotFoundError as e:
        logger.error(f"conda 命令未找到或 Conda 环境 '{conda_env}' 不存在: {str(e)}")
        return {
            "script": os.path.basename(script_path),
            "conda_env": conda_env,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Conda 环境 '{conda_env}' 未找到或 conda 命令不可用",
            "success": False
        }
    except Exception as e:
        logger.error(f"执行脚本失败 {script_path}: {str(e)}")
        return {
            "script": os.path.basename(script_path),
            "conda_env": conda_env,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "success": False
        }


async def capture_images_with_scripts(task_no: str, bin_location: str) -> List[Dict[str, Any]]:
    """
    按顺序执行三个抓图脚本

    Args:
        task_no: 任务编号
        bin_location: 储位名称

    Returns:
        所有脚本的执行结果
    """
    results = []

    for i, script_path in enumerate(CAPTURE_SCRIPTS, 1):
        logger.info(f"开始执行第 {i} 个抓图脚本: {script_path}")

        try:
            # 检查脚本文件是否存在
            if not os.path.exists(script_path):
                logger.error(f"脚本文件不存在: {script_path}")
                results.append({
                    "script": script_path,
                    "success": False,
                    "error": "脚本文件不存在"
                })
                continue

            # 执行脚本
            result = await execute_capture_script(script_path, task_no, bin_location)
            results.append(result)

            # 如果脚本执行失败，可以选择是否继续执行后续脚本
            if not result["success"]:
                logger.warning(f"第 {i} 个抓图脚本执行失败，继续执行下一个脚本")
                # 可以根据业务需求决定是否中断
                # continue

            # 脚本之间的短暂延迟（可选）
            if i < len(CAPTURE_SCRIPTS):
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"执行第 {i} 个抓图脚本时发生异常: {str(e)}")
            results.append({
                "script": script_path,
                "success": False,
                "error": str(e)
            })

    return results

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
