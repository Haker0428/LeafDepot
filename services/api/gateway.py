# gateway.py
from fastapi.security import APIKeyHeader
from pathlib import Path
from fastapi.responses import StreamingResponse
from fastapi import WebSocket, WebSocketDisconnect
from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi import FastAPI, Request, HTTPException, status, Header, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from fastapi.responses import FileResponse
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
import csv
import aiohttp
from typing import Optional, Set, List

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 模拟服务的地址
LMS_BASE_URL = "http://localhost:6000"
RCS_BASE_URL = "http://localhost:4001"
CAMERA_BASE_URL = "http://localhost:5000"
RCS_PREFIX = "/rcs/rtas"
REAL_RCS_BASE_URL = "http://10.4.180.190:80/rcs/rtas"

BASE_PATH = "/home/ubuntu/Projects/LeafDepot/output"

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


class ConnectionManager:
    def __init__(self):
        # 使用字典存储每个任务对应的多个连接
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # 连接心跳跟踪
        self.connection_heartbeats: Dict[str, Dict[str, float]] = {}
        # 连接锁，防止竞争条件
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, task_no: str):
        """接受并注册 WebSocket 连接"""
        try:
            # 设置合理的超时和消息大小限制
            await websocket.accept()

            async with self._lock:
                # 初始化该任务的连接集合
                if task_no not in self.active_connections:
                    self.active_connections[task_no] = set()
                    self.connection_heartbeats[task_no] = {}

                # 生成连接ID用于心跳跟踪
                connection_id = f"{task_no}_{id(websocket)}_{time.time()}"

                # 将连接添加到集合
                self.active_connections[task_no].add(websocket)
                # 初始化心跳时间
                self.connection_heartbeats[task_no][connection_id] = time.time(
                )

                logger.info(
                    f"✅ WebSocket 连接已建立: task_no={task_no}, connection_id={connection_id}")
                logger.info(
                    f"当前任务 {task_no} 的连接数: {len(self.active_connections[task_no])}")

                # 返回连接ID，用于后续心跳跟踪
                return connection_id

        except Exception as e:
            logger.error(f"❌ WebSocket 连接失败: {e}")
            raise

    async def disconnect(self, task_no: str, websocket: WebSocket):
        """断开并清理 WebSocket 连接"""
        try:
            async with self._lock:
                if task_no in self.active_connections:
                    # 从连接集合中移除
                    if websocket in self.active_connections[task_no]:
                        self.active_connections[task_no].remove(websocket)

                        # 清理心跳记录
                        connection_id = None
                        for cid, ws in [(cid, ws) for cid, ws in self.connection_heartbeats[task_no].items()]:
                            if ws == websocket:
                                connection_id = cid
                                break

                        if connection_id and task_no in self.connection_heartbeats:
                            self.connection_heartbeats[task_no].pop(
                                connection_id, None)

                        logger.info(f"❌ WebSocket 连接已关闭: task_no={task_no}")

                    # 如果该任务没有活跃连接了，清理相关资源
                    if not self.active_connections[task_no]:
                        del self.active_connections[task_no]
                        if task_no in self.connection_heartbeats:
                            del self.connection_heartbeats[task_no]

        except Exception as e:
            logger.error(f"❌ WebSocket 断开连接时出错: {e}")

    async def send_csv_data(self, task_no: str, data: dict):
        """向指定任务的所有连接发送数据"""
        success_count = 0
        failed_count = 0

        if task_no not in self.active_connections:
            logger.warning(f"⚠️ 没有找到 task_no={task_no} 的活跃连接")
            return False

        # 复制一份连接集合，避免在迭代时修改
        connections_to_send = list(self.active_connections[task_no])

        if not connections_to_send:
            logger.warning(f"⚠️ 任务 {task_no} 没有活跃连接")
            return False

        for websocket in connections_to_send:
            try:
                # 检查连接是否仍然活跃
                if websocket.client_state.name != "CONNECTED":
                    logger.warning(f"⚠️ 连接已断开，跳过发送: task_no={task_no}")
                    await self.disconnect(task_no, websocket)
                    failed_count += 1
                    continue

                # 发送数据
                await websocket.send_json(data)
                success_count += 1

                # 更新心跳时间
                connection_id = None
                for cid, ws in [(cid, ws) for cid, ws in self.connection_heartbeats.get(task_no, {}).items()]:
                    if ws == websocket:
                        connection_id = cid
                        break

                if connection_id and task_no in self.connection_heartbeats:
                    self.connection_heartbeats[task_no][connection_id] = time.time(
                    )

            except (WebSocketDisconnect, RuntimeError) as e:
                logger.warning(f"❌ 发送数据时连接断开: {e}")
                await self.disconnect(task_no, websocket)
                failed_count += 1
            except Exception as e:
                logger.error(f"❌ 发送数据到前端失败: {e}")
                failed_count += 1

        logger.info(
            f"📤 已发送数据到任务 {task_no}: 成功 {success_count} 个连接，失败 {failed_count} 个连接")
        return success_count > 0

    async def broadcast_to_task(self, task_no: str, data: dict):
        """向指定任务的所有连接广播数据（send_csv_data 的别名）"""
        return await self.send_csv_data(task_no, data)

    async def send_ping_to_all(self):
        """向所有连接发送心跳 ping"""
        current_time = time.time()
        disconnected_tasks = []

        for task_no, connections in list(self.active_connections.items()):
            disconnected_connections = []

            for websocket in list(connections):
                try:
                    # 发送 ping
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": current_time
                    })
                except (WebSocketDisconnect, RuntimeError) as e:
                    logger.warning(
                        f"❌ 心跳检测发现断开连接: task_no={task_no}, error={e}")
                    disconnected_connections.append(websocket)
                except Exception as e:
                    logger.error(f"❌ 发送心跳失败: {e}")

            # 清理断开连接
            for websocket in disconnected_connections:
                await self.disconnect(task_no, websocket)

            # 检查心跳超时
            if task_no in self.connection_heartbeats:
                timeout_connections = []
                timeout_seconds = 60  # 60秒超时

                for connection_id, last_heartbeat in list(self.connection_heartbeats[task_no].items()):
                    if current_time - last_heartbeat > timeout_seconds:
                        logger.warning(
                            f"⚠️ 连接心跳超时: task_no={task_no}, connection_id={connection_id}")
                        # 找到对应的 websocket 并断开
                        for websocket in list(self.active_connections.get(task_no, [])):
                            # 这里简化处理，实际应该根据 connection_id 找到对应的 websocket
                            timeout_connections.append(websocket)

                for websocket in timeout_connections:
                    await self.disconnect(task_no, websocket)

            # 如果任务没有连接了，标记为清理
            if task_no not in self.active_connections or not self.active_connections[task_no]:
                disconnected_tasks.append(task_no)

        # 清理没有连接的任务
        for task_no in disconnected_tasks:
            if task_no in self.active_connections:
                del self.active_connections[task_no]
            if task_no in self.connection_heartbeats:
                del self.connection_heartbeats[task_no]

    def get_connection_count(self, task_no: str) -> int:
        """获取连接数量"""
        if task_no:
            return len(self.active_connections.get(task_no, set()))
        else:
            return sum(len(conns) for conns in self.active_connections.values())


# 创建全局连接管理器实例
manager = ConnectionManager()


@app.websocket("/ws/inventory/{task_no}")
async def websocket_endpoint(websocket: WebSocket, task_no: str):
    """WebSocket 端点，支持任务特定连接"""
    connection_id = None

    try:
        # 连接到管理器
        connection_id = await manager.connect(websocket, task_no)

        # 发送欢迎消息
        await websocket.send_json({
            "type": "welcome",
            "message": f"已连接到任务 {task_no}",
            "connection_id": connection_id,
            "timestamp": datetime.now().isoformat()
        })

        # 等待并处理消息
        while True:
            try:
                # 设置接收超时
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                try:
                    message = json.loads(data)
                    message_type = message.get("type")

                    if message_type == "ping":
                        # 处理 ping 请求，更新心跳
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": time.time()
                        })

                        if task_no in manager.connection_heartbeats and connection_id:
                            manager.connection_heartbeats[task_no][connection_id] = time.time(
                            )

                    elif message_type == "subscribe":
                        # 处理订阅特定事件
                        events = message.get("events", [])
                        await websocket.send_json({
                            "type": "subscribed",
                            "events": events,
                            "timestamp": datetime.now().isoformat()
                        })

                    else:
                        logger.info(f"📥 收到前端消息: {data}")
                        # 可以响应前端消息
                        await websocket.send_json({
                            "type": "acknowledge",
                            "received": True,
                            "timestamp": datetime.now().isoformat()
                        })

                except json.JSONDecodeError:
                    logger.warning(f"❌ 收到非 JSON 格式消息: {data[:100]}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "消息格式错误，必须是有效的 JSON",
                        "timestamp": datetime.now().isoformat()
                    })

            except asyncio.TimeoutError:
                # 发送 ping 以保持连接活跃
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": time.time()
                    })
                except:
                    break  # 连接已断开

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket 连接主动断开: task_no={task_no}")

    except Exception as e:
        logger.error(f"❌ WebSocket 异常: {e}", exc_info=True)

    finally:
        # 确保清理连接
        if websocket and task_no:
            await manager.disconnect(task_no, websocket)


robot_status_store = {}
status_events = {}
task_timeouts = {}


STATUS_KEY = "ldui_2025"  # 固定状态键
status_event = asyncio.Event()  # 单个事件对象
robot_status_store: Dict[str, Any] = {}  # 状态存储
TASK_TIMEOUT = 300  # 超时时间（秒）


# 抓图脚本路径配置
CAPTURE_SCRIPTS = [
    "/home/ubuntu/Projects/LeafDepot/hardware/cam_sys/build/3d_capture.py",  # 第一个抓图脚本
    "/home/ubuntu/Projects/LeafDepot/hardware/cam_sys/build/scan_1_capture.py",  # 第二个抓图脚本
    "/home/ubuntu/Projects/LeafDepot/hardware/cam_sys/build/scan_2_capture.py"   # 第三个抓图脚本
]


class TaskStatus(BaseModel):
    task_no: str
    status: str  # init, running, completed, failed
    current_step: int
    total_steps: int
    tobaccoCode: str
    rcsCode: str


# 全局任务状态存储（生产环境建议使用数据库或Redis）
inventory_tasks: Dict[str, TaskStatus] = {}

######################################### 盘点任务接口 #########################################


@app.post("/api/inventory/start-inventory")
async def start_inventory(request: Request, background_tasks: BackgroundTasks):
    """启动盘点任务，接收任务编号和储位名称列表"""
    try:
        data = await request.json()
        task_no = data.get("taskNo")
        # 采用RCS站点
        bin_locations = data.get("binLocations", [])
        tobaccoCode = data.get("tobaccoCode", [])
        rcs_code = data.get("rcsCode", [])

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
                                "tobaccoCode": existing_task.tobaccoCode
                            }
                        }
                    )

        # 在后台异步执行盘点任务
        # background_tasks.add_task(
        #     execute_inventory_workflow,
        #     task_no=task_no,
        #     bin_locations=bin_locations,
        #     tobaccoCode=tobaccoCode,
        #     rcs_code=rcs_code
        # )

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


async def execute_inventory_workflow(task_no: str, bin_locations: List[str], tobaccoCode: List[str], rcs_code: List[str]):
    """执行完整的盘点工作流"""
    logger.info(f"开始执行盘点工作流: {task_no}, 共 {len(bin_locations)} 个储位")

    # 初始化任务状态
    task_status = TaskStatus(
        task_no=task_no,
        status="init",
        current_step=1,
        total_steps=len(bin_locations),
        tobaccoCode="101",
        rcsCode="rcs101"
    )

    for index, location in enumerate(bin_locations):
        inventory_tasks[location] = task_status

    # 整体下发盘点任务
    method = "start"
    await update_robot_status(method)

    submit_result = await submit_inventory_task(task_no, rcs_code)

    try:
        # 循环处理每个储位
        for i, bin_location in enumerate(bin_locations):
            logger.info(f"开始处理储位 {i+1}/{len(bin_locations)}: {tobaccoCode[i]}")

            # 处理单个储位
            result = await process_single_bin_location(
                task_no=task_no,
                bin_location=bin_location,
                index=i,
                total=len(bin_locations),
                rcs_code=rcs_code[i]
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


async def process_single_bin_location(task_no: str, bin_location: str, index: int, total: int, rcs_code: str):
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

                await read_and_validate_csv(task_no, bin_location)

                # 这个判断一定会执行，因为wait_for_robot_status会阻塞直到收到end状态或超时
                # if ctu_status and ctu_status.get("method") == "end":

                #     # 执行抓图脚本
                #     capture_results = await capture_images_with_scripts(task_no, bin_location)
                #     result["captureResults"] = capture_results

                #     # 检查抓图结果
                #     successful_scripts = sum(
                #         1 for r in capture_results if r.get("success"))
                #     if successful_scripts < len(CAPTURE_SCRIPTS):
                #         logger.warning(
                #             f"部分抓图脚本执行失败: {successful_scripts}/{len(CAPTURE_SCRIPTS)}")
                #     else:
                #         logger.info(f"所有抓图脚本执行成功: {bin_location}")

                #     if ((index + 1) < total):
                #         logger.info(f"收到机器人结束状态: {bin_location}")

                #         # 只有在收到end状态后才调用继续任务接口
                #         continue_result = await continue_inventory_task()
                #         logger.info(f"继续任务接口调用结果: {continue_result}")
                #         result["continueResult"] = continue_result

                #     # await read_and_validate_csv(task_no, bin_location)

                # else:
                #     # 正常情况下不会执行到这里，除非wait_for_robot_status返回了非end状态
                #     logger.warning(f"未收到预期的结束状态，当前状态: {ctu_status}")

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


async def read_and_validate_csv(task_no: str, bin_location: str):
    """读取并验证 CSV 文件，然后通过 WebSocket 发送数据到前端"""
    try:
        # 构建文件路径
        csv_file_path = f"/home/ubuntu/Projects/LeafDepot/output/{task_no}/{bin_location}/counting_output.csv"

        if not os.path.exists(csv_file_path):
            logger.error(f"CSV 文件不存在: {csv_file_path}")
            await send_csv_data_via_websocket(task_no, bin_location, None, None, False, "CSV 文件不存在")
            return

        # 读取 CSV 文件 - 尝试多种编码
        rows = None
        encodings_to_try = ['utf-8', 'gbk', 'utf-8-sig', 'latin-1', 'cp1252']

        for encoding in encodings_to_try:
            try:
                with open(csv_file_path, 'r', encoding=encoding) as file:
                    reader = csv.reader(file)
                    rows = list(reader)
                    logger.info(f"成功使用 {encoding} 编码读取文件，共 {len(rows)} 行")
                    break
            except UnicodeDecodeError as e:
                logger.warning(f"使用 {encoding} 编码读取失败: {e}")
                continue
            except Exception as e:
                logger.error(f"读取文件时发生其他错误: {e}")
                break

        if rows is None:
            logger.error("所有编码尝试都失败了")
            await send_csv_data_via_websocket(task_no, bin_location, None, None, False, "无法读取文件编码")
            return

        # 检查文件是否有足够的数据
        if len(rows) < 2:  # 至少需要表头+数据行
            logger.error(f"CSV 文件数据行数不足: {len(rows)} 行")
            await send_csv_data_via_websocket(task_no, bin_location, None, None, False, "CSV 文件数据行数不足")
            return

        # 打印表头信息用于调试
        if len(rows[0]) > 0:
            logger.info(f"表头列数: {len(rows[0])}")
            logger.info(f"表头内容: {rows[0]}")

        # 按照列校验：查找匹配 task_no 和 bin_location 的行
        found_index = -1
        number_value = None
        text_value = None

        # 遍历数据行（跳过表头）
        for i, row in enumerate(rows[1:], start=1):  # i 从1开始，对应实际行号
            # 确保行有足够的列
            if len(row) >= 5:
                # 获取当前行的各个列值
                current_task_no = row[1] if len(row) > 1 else ""
                current_bin_location = row[2] if len(row) > 2 else ""

                # 去掉可能的空格
                current_task_no = current_task_no.strip()
                current_bin_location = current_bin_location.strip()

                logger.info(
                    f"第 {i+1} 行: task_no='{current_task_no}', bin_location='{current_bin_location}'")

                # 检查是否匹配传入的参数
                if current_task_no == task_no and current_bin_location == bin_location:
                    found_index = i
                    number_value = row[3] if len(row) > 3 else ""
                    text_value = row[4] if len(row) > 4 else ""
                    logger.info(f"在第 {i+1} 行找到匹配数据")
                    break

        # 检查是否找到匹配行
        if found_index >= 0:
            logger.info(f"CSV 数据校验成功: 任务号={task_no}, 库位号={bin_location}")
            logger.info(f"提取到数据: 数值={number_value}, 文本={text_value}")

            # 尝试将 number_value 转换为数字
            try:
                # 先去除可能的逗号、空格等
                number_str = str(number_value).replace(',', '').strip()
                number_int = int(number_str)
            except (ValueError, AttributeError) as e:
                logger.warning(f"无法将 '{number_value}' 转换为数字: {e}")
                number_int = None

            # 发送数据到前端
            await send_csv_data_via_websocket(task_no, bin_location, number_int, text_value, True, "校验成功")
        else:
            logger.warning(
                f"CSV 文件中未找到匹配的数据: task_no={task_no}, bin_location={bin_location}")
            logger.warning(f"搜索了 {len(rows)-1} 行数据")
            await send_csv_data_via_websocket(task_no, bin_location, None, None, False, "未找到匹配的数据")

    except Exception as e:
        logger.error(f"读取 CSV 文件失败: {str(e)}", exc_info=True)
        await send_csv_data_via_websocket(task_no, bin_location, None, None, False, f"读取失败: {str(e)}")


async def send_csv_data_via_websocket(task_no: str, bin_location: str, number_value: Optional[int],
                                      text_value: Optional[str], success: bool, message: str):
    """通过 WebSocket 发送 CSV 数据到前端"""
    try:
        # 构建数据对象，确保类型正确
        data = {
            "type": "csv_data",
            "taskNo": task_no,
            "binLocation": bin_location,
            "number": number_value,  # 直接使用，Python的None在前端会是null
            "text": text_value,      # 直接使用，不要强制转换为字符串
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

        # 通过 WebSocket 连接管理器发送数据
        sent = await manager.send_csv_data(task_no, data)

        if sent:
            logger.info(f"✅ CSV 数据已发送到前端: {task_no}, {bin_location}")
            logger.info(f"📊 数据内容: 实际品规={text_value}, 数量={number_value}")
        else:
            logger.warning(
                f"⚠️ CSV 数据发送失败，可能没有活跃连接: {task_no}, {bin_location}")

    except Exception as e:
        logger.error(f"❌ 发送 CSV 数据到前端失败: {str(e)}")

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
        cmd = ["python", script_path,
               "--task-no", task_no, "--bin-location", bin_location]

        script_dir = os.path.dirname(os.path.abspath(script_path))

        # 方法2: 直接使用 conda 环境中的 python 路径（如果知道路径）
        # 假设你的 conda 环境路径是已知的
        # conda_python_path = f"/home/user/anaconda3/envs/{conda_env}/bin/python"
        # cmd = [conda_python_path, script_path, "--task-no", task_no, "--bin-location", bin_location]

        # 执行脚本，并通过 cwd 参数指定工作目录
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=script_dir,  # 关键修改：切换到脚本所在目录运行
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
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"执行第 {i} 个抓图脚本时发生异常: {str(e)}")
            results.append({
                "script": script_path,
                "success": False,
                "error": str(e)
            })

    return results

#######################################################


@app.post("/api/get-image-original")
async def get_image_original(data: dict):

    task_no = data.get('taskNo')

    bin_desc = data.get('binDesc')

    if not task_no or not bin_desc:

        raise HTTPException(status_code=400, detail="Invalid parameters")

    image_path = os.path.join(
        BASE_PATH, task_no, bin_desc, "3d_camera", "main.jpg")

    if not os.path.exists(image_path):

        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(image_path, media_type='image/jpeg', filename=os.path.basename(image_path))


@app.post("/api/get-image-postprocess")
async def get_image_postprocess(data: dict):

    task_no = data.get('taskNo')

    bin_desc = data.get('binDesc')

    if not task_no or not bin_desc:

        raise HTTPException(status_code=400, detail="Invalid parameters")

    image_path = os.path.join(
        BASE_PATH, task_no, bin_desc, "3d_camera", "depth.jpg")

    if not os.path.exists(image_path):

        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(image_path, media_type='image/jpeg', filename=os.path.basename(image_path))
#######################################################

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
