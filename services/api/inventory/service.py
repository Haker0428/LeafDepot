"""
盘点任务服务 - 任务状态管理和工作流执行
"""
import os
import sys
import json
import time
import asyncio
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

import requests
import aiohttp

# 添加项目根目录到路径
_project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from services.api.shared.models import (
    TaskStatus,
    BinLocationStatus,
)
from services.api.shared.config import (
    logger,
    rcs_logger,
    project_root,
    logs_dir,
    RCS_BASE_URL,
    RCS_PREFIX,
    RCS_FULL_URL,
    RCS_REAL,
    RCS_CALLBACK_URL,
    ENABLE_BARCODE,
    BARCODE_MODULE_AVAILABLE,
    DETECT_MODULE_AVAILABLE,
    ENABLE_DEBUG,
    ENABLE_VISUALIZATION,
)
from services.api.shared.websocket_manager import ws_manager
from services.api.shared.excel_writer import build_excel_data, write_excel

# 从 robot/router 导入状态管理（避免与 services.api.state 混淆）
from services.api.robot.router import (
    clear_robot_status_queue,
    update_robot_status as _router_update_status,
    wait_for_robot_status as _router_wait_status,
)
from services.api.inventory.task_state import (
    mark_running,
    update_progress,
    mark_finished,
)

# RCS REQUEST-ID 递增计数器（持久化到文件，进程重启不丢失）
_COUNTER_FILE = str(logs_dir / "request_id_counter.txt")

def _get_next_request_id() -> str:
    """获取下一个递增的 REQUEST-ID，格式: TASK_ + 12位16进制大写（每进程互斥写）"""
    import fcntl
    os.makedirs(os.path.dirname(_COUNTER_FILE), exist_ok=True)
    with open(_COUNTER_FILE, "a+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.seek(0)
            current = f.read().strip()
            counter = int(current, 16) if current else 0
            counter += 1
            f.seek(0)
            f.truncate()
            f.write(f"{counter:012X}")
            return f"TASK_{counter:012X}"
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


# 盘点任务号计数器（按日递增，跨进程互斥写）
_TASKNO_COUNTER_FILE = str(logs_dir / "task_no_counter.txt")

def _get_next_task_no() -> str:
    """获取下一个盘点任务号，格式: HS{YYYYMMDD}{NN}，每日从1开始递增"""
    import fcntl
    today = datetime.now().strftime("%Y%m%d")
    os.makedirs(os.path.dirname(_TASKNO_COUNTER_FILE), exist_ok=True)
    with open(_TASKNO_COUNTER_FILE, "a+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.seek(0)
            current = f.read().strip()
            if current:
                parts = current.split(":", 1)
                saved_date = parts[0]
                counter = int(parts[1]) if len(parts) > 1 else 0
            else:
                saved_date = ""
                counter = 0
            if saved_date != today:
                counter = 0  # 新的一天，重置计数器
            counter += 1
            f.seek(0)
            f.truncate()
            f.write(f"{today}:{counter}")
            return f"HS{today}{counter:02d}"
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


# 任务状态存储
_inventory_tasks: Dict[str, TaskStatus] = {}
_inventory_task_bins: Dict[str, List[BinLocationStatus]] = {}
_inventory_task_details: Dict[str, Dict[str, Dict[str, Any]]] = {}

# 真实模式 END 处理全局锁：防止多任务同时处理队列导致回调被对方错误消费
_real_mode_lock = asyncio.Lock()

# 导出别名（供其他模块导入）
inventory_tasks = _inventory_tasks
inventory_task_bins = _inventory_task_bins
inventory_task_details = _inventory_task_details


def get_task_state_storage() -> Dict[str, Any]:
    """获取任务状态存储"""
    try:
        from services.api.state.task_state import get_task_state_manager
        manager = get_task_state_manager()
        return {
            "tasks": manager._inventory_tasks,
            "bins": manager._inventory_task_bins,
            "details": manager._inventory_task_details
        }
    except ImportError:
        return {
            "tasks": _inventory_tasks,
            "bins": _inventory_task_bins,
            "details": _inventory_task_details
        }


def get_inventory_service():
    """获取盘点服务实例"""
    from services.vision.box_count_service import get_box_count_service
    return get_box_count_service()


# ==================== 机器人任务下发函数 ====================

async def submit_inventory_task(task_no: str, bin_locations: List[str], is_sim: bool = True, max_retries: int = 3):
    """下发盘点任务，接收任务编号和储位名称列表，支持失败重试"""
    import time as time_module

    try:
        logger.info(f"下发盘点任务: {task_no}, 储位: {bin_locations}, 模拟模式: {is_sim}")

        last_error = None
        for attempt in range(max_retries):
            try:
                if is_sim:
                    # ====== 模拟模式：使用 aiohttp 异步下发，不阻塞事件循环 ======
                    # requests.post 阻塞期间 asyncio 无法处理回调，END 会丢失。
                    # aiohttp 不阻塞，END 回调到达时事件循环正常处理，不会丢失。
                    url = f"{RCS_FULL_URL}/api/robot/controller/task/submit"
                    headers = {
                        "X-lr-request-id": "ldui",
                        "Content-Type": "application/json"
                    }
                    async with aiohttp.ClientSession() as session:
                        captured_code = None
                        for i, loc in enumerate(bin_locations):
                            target_route = [{"seq": 0, "type": "ZONE", "code": loc}]
                            request_body = {
                                "taskType": "PF-CTU-COMMON-TEST",
                                "targetRoute": target_route
                            }
                            rcs_logger.info(f"【模拟RCS下发请求】url={url} headers={json.dumps(headers, ensure_ascii=False)} body={json.dumps(request_body, ensure_ascii=False)}")
                            async with session.post(url, json=request_body, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                                response_text = await response.text()
                                rcs_logger.info(f"【模拟RCS下发响应】code={response.status} body={response_text}")
                                if response.status == 200:
                                    try:
                                        data = json.loads(response_text)
                                        captured_code = data.get("data", {}).get("robotTaskCode", "")
                                    except Exception:
                                        pass
                            if i < len(bin_locations) - 1:
                                await asyncio.sleep(0.5)
                    return {"success": True, "message": "盘点任务已下发", "robotTaskCode": captured_code or "ctu001"}

                else:
                    # ====== 真实模式 ======
                    real_cfg = RCS_REAL or {}
                    protocol = "https" if real_cfg.get("use_ssl", True) else "http"
                    host = real_cfg.get("host", "localhost")
                    port = real_cfg.get("port", 443)
                    base_url = f"{protocol}://{host}:{port}"
                    url = f"{base_url}{RCS_PREFIX}/api/robot/controller/task/submit"

                    timestamp = str(int(time_module.time() * 1000))
                    headers = {
                        "X-App-Id": real_cfg.get("app_id", "1008"),
                        "X-Sign": real_cfg.get("sign", ""),
                        "X-Timestamp": timestamp,
                        "X-LR-REQUEST-ID": _get_next_request_id(),
                        "Content-Type": "application/json"
                    }
                    # 构建 targetRoute：STORAGE（储位）
                    target_route = [
                        {
                            "autoStart": 1,
                            "code": loc,
                            "seq": i,
                            "type": "STORAGE"
                        }
                        for i, loc in enumerate(bin_locations)
                    ]
                    request_body = {
                        "extra": {},
                        "groupCode": "",
                        "interrupt": 0,
                        "liftCode": "",
                        "robotTaskCode": "",
                        "robotType": "",
                        "targetRoute": target_route,
                        "taskType": "ABCDEFG"
                    }
                    rcs_logger.info(f"【真实RCS下发请求】url={url} headers={json.dumps(headers, ensure_ascii=False)} body={json.dumps(request_body, ensure_ascii=False)}")
                    response = requests.post(url, json=request_body, headers=headers, timeout=20, verify=False)
                    rcs_logger.info(f"【真实RCS下发响应】code={response.status_code} body={response.text}")

                if response.status_code == 200:
                    response_data = response.json()
                    # 兼容两种返回格式：code="SUCCESS" 或 success=true
                    is_success = response_data.get("success") is True or response_data.get("code") == "SUCCESS"
                    if is_success:
                        robot_task_code = ""
                        if is_sim:
                            robot_task_code = response_data.get("data", {}).get("robotTaskCode", "ctu001")
                        else:
                            robot_task_code = response_data.get("data", {}).get("robotTaskCode", "")
                        logger.info(f"储位 {bin_locations} 已发送到机器人系统, robotTaskCode={robot_task_code}")
                        return {"success": True, "message": "盘点任务已下发", "robotTaskCode": robot_task_code}
                    else:
                        last_error = f" RCS 返回错误: {response_data.get('message', '')} ({response_data.get('errorCode', '')})"
                        logger.warning(f"下发任务失败 (尝试 {attempt + 1}/{max_retries}){last_error}")
                else:
                    last_error = f" HTTP {response.status_code}"
                    logger.warning(f"下发任务失败 (尝试 {attempt + 1}/{max_retries}){last_error}")

            except requests.exceptions.Timeout:
                last_error = " 请求超时"
                logger.warning(f"下发任务超时 (尝试 {attempt + 1}/{max_retries})")
            except requests.exceptions.ConnectionError as conn_err:
                last_error = f" 连接失败: {conn_err}"
                logger.warning(f"下发任务连接失败 (尝试 {attempt + 1}/{max_retries}){last_error}")
            except Exception as req_err:
                last_error = f" 请求异常: {req_err}"
                logger.warning(f"下发任务异常 (尝试 {attempt + 1}/{max_retries}){last_error}")

            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                logger.info(f"等待 {wait_time} 秒后重试...")
                time_module.sleep(wait_time)

        logger.error(f"下发盘点任务失败，已达到最大重试次数 ({max_retries})")
        return {"success": False, "message": f"盘点任务下发失败，已重试{max_retries}次{last_error}"}

    except Exception as e:
        logger.error(f"下发盘点任务失败: {str(e)}")
        raise


async def continue_inventory_task(is_sim: bool = True, robot_task_code: str = "", max_retries: int = 3):
    """继续盘点任务，支持失败重试"""
    import time as time_module

    try:
        logger.info(f"继续执行盘点任务, 模拟模式: {is_sim}, robotTaskCode: {robot_task_code}")

        last_error = None
        for attempt in range(max_retries):
            try:
                if is_sim:
                    url = f"{RCS_FULL_URL}/api/robot/controller/task/extend/continue"
                    headers = {
                        "X-lr-request-id": "ldui",
                        "Content-Type": "application/json"
                    }
                    request_body = {
                        "robotTaskCode": robot_task_code or "ctu001"
                    }
                    rcs_logger.info(f"【模拟RCS继续请求】url={url} headers={json.dumps(headers, ensure_ascii=False)} body={json.dumps(request_body, ensure_ascii=False)}")
                    response = requests.post(url, json=request_body, headers=headers, timeout=30)
                    rcs_logger.info(f"【模拟RCS继续响应】code={response.status_code} body={response.text}")

                else:
                    # ====== 真实模式 ======
                    real_cfg = RCS_REAL or {}
                    protocol = "https" if real_cfg.get("use_ssl", True) else "http"
                    host = real_cfg.get("host", "localhost")
                    port = real_cfg.get("port", 443)
                    base_url = f"{protocol}://{host}:{port}"
                    continue_path = real_cfg.get("continue_url", "/rcs/rtas/api/robot/controller/task/extend/continue")
                    url = f"{base_url}{continue_path}"

                    timestamp = str(int(time_module.time() * 1000))
                    headers = {
                        "X-App-Id": real_cfg.get("app_id", "1008"),
                        "X-Sign": real_cfg.get("sign", ""),
                        "X-Timestamp": timestamp,
                        "X-LR-REQUEST-ID": _get_next_request_id(),
                        "Content-Type": "application/json"
                    }
                    request_body = {
                        "extra": {},
                        "triggerType": "TASK",
                        "triggerCode": robot_task_code
                    }
                    rcs_logger.info(f"【真实RCS继续请求】url={url} headers={json.dumps(headers, ensure_ascii=False)} body={json.dumps(request_body, ensure_ascii=False)}")
                    response = requests.post(url, json=request_body, headers=headers, timeout=20, verify=False)
                    rcs_logger.info(f"【真实RCS继续响应】code={response.status_code} body={response.text}")

                if response.status_code == 200:
                    response_data = response.json()
                    # 兼容两种返回格式：code="SUCCESS" 或 success=true
                    is_success = response_data.get("success") is True or response_data.get("code") == "SUCCESS"
                    if is_success:
                        logger.info(f"继续执行盘点任务命令已发送到机器人系统")
                        return {"success": True, "message": "盘点任务已继续"}
                    else:
                        last_error = f" RCS 返回错误: {response_data.get('message', '')} ({response_data.get('errorCode', '')})"
                        logger.warning(f"继续任务失败 (尝试 {attempt + 1}/{max_retries}){last_error}")
                else:
                    last_error = f" HTTP {response.status_code}"
                    logger.warning(f"继续任务失败 (尝试 {attempt + 1}/{max_retries}){last_error}")

            except requests.exceptions.Timeout:
                last_error = " 请求超时"
                logger.warning(f"继续任务超时 (尝试 {attempt + 1}/{max_retries})")
            except requests.exceptions.ConnectionError as conn_err:
                last_error = f" 连接失败: {conn_err}"
                logger.warning(f"继续任务连接失败 (尝试 {attempt + 1}/{max_retries}){last_error}")
            except Exception as req_err:
                last_error = f" 请求异常: {req_err}"
                logger.warning(f"继续任务异常 (尝试 {attempt + 1}/{max_retries}){last_error}")

            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                logger.info(f"等待 {wait_time} 秒后重试...")
                time_module.sleep(wait_time)

        logger.error(f"继续盘点任务失败，已达到最大重试次数 ({max_retries})")
        return {"success": False, "message": f"继续任务已重试{max_retries}次{last_error}"}

    except Exception as e:
        logger.error(f"继续盘点任务失败: {str(e)}")
        raise


# ==================== RCS 任务取消（终止）接口 ====================
# TODO: 等 RCS 提供 cancel API 后，在此填入真实接口地址和请求体格式
# abort_inventory_task 负责主动通知 RCS 停止所有进行中的任务
# 调用位置：router.py 的 cancel-inventory 接口中

async def abort_inventory_task(robot_task_code: str, is_sim: bool = True, max_retries: int = 3):
    """取消/终止 RCS 中的盘点任务

    等 RCS 提供 cancel API 后，在此填入：
    - 模拟模式：{RCS_FULL_URL}/api/robot/controller/task/cancel
    - 真实模式：{base_url}{RCS_PREFIX}/api/robot/controller/task/cancel

    请求体示例（待 RCS 确认）：
    {
        "robotTaskCode": robot_task_code,
        "extra": {}
    }
    """
    import time as time_module

    if not robot_task_code:
        logger.warning("[abort] robotTaskCode 为空，跳过 abort 调用")
        return {"success": False, "message": "robotTaskCode 为空"}

    try:
        logger.info(f"[abort] 发送取消任务指令, robotTaskCode={robot_task_code}, 模拟模式={is_sim}")

        last_error = None
        for attempt in range(max_retries):
            try:
                if is_sim:
                    url = f"{RCS_FULL_URL}/api/robot/controller/task/cancel"
                    headers = {
                        "X-lr-request-id": "ldui",
                        "Content-Type": "application/json"
                    }
                    request_body = {
                        "robotTaskCode": robot_task_code
                    }
                    rcs_logger.info(f"【模拟RCS取消请求】url={url} body={json.dumps(request_body, ensure_ascii=False)}")
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=request_body, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                            response_text = await response.text()
                            rcs_logger.info(f"【模拟RCS取消响应】code={response.status} body={response_text}")
                            if response.status == 200:
                                logger.info(f"[abort] 取消指令已发送至 RCS, robotTaskCode={robot_task_code}")
                                return {"success": True, "message": "取消指令已发送"}
                            last_error = f" HTTP {response.status}: {response_text}"
                else:
                    # ====== 真实模式 ======
                    real_cfg = RCS_REAL or {}
                    protocol = "https" if real_cfg.get("use_ssl", True) else "http"
                    host = real_cfg.get("host", "localhost")
                    port = real_cfg.get("port", 443)
                    base_url = f"{protocol}://{host}:{port}"
                    # TODO: 等 RCS 确认 cancel 接口路径，cancel_url 可在 config 中配置
                    cancel_path = real_cfg.get("cancel_url", "/rcs/rtas/api/robot/controller/task/cancel")
                    url = f"{base_url}{cancel_path}"

                    timestamp = str(int(time_module.time() * 1000))
                    headers = {
                        "X-App-Id": real_cfg.get("app_id", "1008"),
                        "X-Sign": real_cfg.get("sign", ""),
                        "X-Timestamp": timestamp,
                        "X-LR-REQUEST-ID": _get_next_request_id(),
                        "Content-Type": "application/json"
                    }
                    request_body = {
                        "extra": {},
                        "triggerType": "TASK",
                        "triggerCode": robot_task_code
                    }
                    rcs_logger.info(f"【真实RCS取消请求】url={url} body={json.dumps(request_body, ensure_ascii=False)}")
                    response = requests.post(url, json=request_body, headers=headers, timeout=20, verify=False)
                    rcs_logger.info(f"【真实RCS取消响应】code={response.status_code} body={response.text}")
                    if response.status_code == 200:
                        response_data = response.json()
                        is_success = response_data.get("success") is True or response_data.get("code") == "SUCCESS"
                        if is_success:
                            logger.info(f"[abort] 取消指令已发送至 RCS, robotTaskCode={robot_task_code}")
                            return {"success": True, "message": "取消指令已发送"}
                        last_error = f" RCS 返回: {response_data.get('message', '')}"
                    else:
                        last_error = f" HTTP {response.status_code}"

            except requests.exceptions.Timeout:
                last_error = " 请求超时"
            except requests.exceptions.ConnectionError as conn_err:
                last_error = f" 连接失败: {conn_err}"
            except Exception as req_err:
                last_error = f" 请求异常: {req_err}"

            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                logger.info(f"[abort] 重试中 ({attempt + 1}/{max_retries})，等待 {wait_time}s...")
                time_module.sleep(wait_time)

        logger.error(f"[abort] 取消任务失败，已重试{max_retries}次: {last_error}")
        return {"success": False, "message": f"取消任务已重试{max_retries}次{last_error}"}

    except Exception as e:
        logger.error(f"[abort] 取消任务异常: {str(e)}")
        raise


# ==================== 机器人状态管理函数 ====================

async def update_robot_status(method: str, data: Optional[Dict] = None):
    """更新机器人状态并触发事件（委托给 robot/router）"""
    await _router_update_status(method, data)


async def wait_for_robot_status(expected_method: str, timeout: int = 300, valid_robot_codes: set = None):
    """等待特定机器人状态（委托给 robot/router）"""
    return await _router_wait_status(expected_method, timeout, valid_robot_codes=valid_robot_codes)


# ==================== 系统在线状态检查 ====================

def check_service_online(host: str, port: int, timeout: int = 5) -> bool:
    """检查服务是否在线（TCP 连接检测）"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


async def check_systems_online(is_sim: bool, with_camera: bool) -> Dict[str, Any]:
    """
    检查 RCS 和相机系统是否在线

    :param is_sim: 是否模拟模式
    :param with_camera: 是否使用真实相机
    :return: {"online": bool, "details": {...}}
    """
    from services.api.shared.config import RCS_BASE_URL, CAPTURE_SCRIPTS, CAMERA_TEST_DIR
    import re

    results = {"rcs": {}, "cameras": {}}

    # 解析 RCS 地址
    rcs_match = re.match(r"http://([^:/]+):(\d+)", RCS_BASE_URL)
    if rcs_match:
        rcs_host = rcs_match.group(1)
        rcs_port = int(rcs_match.group(2))
        rcs_online = check_service_online(rcs_host, rcs_port)
        results["rcs"] = {"host": rcs_host, "port": rcs_port, "online": rcs_online}
    else:
        results["rcs"] = {"host": RCS_BASE_URL, "online": False, "error": "无法解析地址"}

    # 模拟模式且不启用相机，或使用本地测试图片目录 → 跳过相机检查
    if is_sim and (not with_camera or CAMERA_TEST_DIR):
        results["cameras"] = {
            "status": "跳过（本地测试图片）" if CAMERA_TEST_DIR else "跳过（模拟模式）",
            "online": True
        }
        all_online = results["rcs"].get("online", False)
        return {"online": all_online, "details": results}

    # 检查相机在线状态
    camera_ips = {
        "3d_camera": "10.16.82.180",
        "scan_camera_1": "10.16.82.181",
        "scan_camera_2": "10.16.82.182",
    }
    camera_port = 8000  # 海康威视相机默认管理端口

    all_cameras_online = True
    for cam_name, cam_ip in camera_ips.items():
        cam_online = check_service_online(cam_ip, camera_port)
        results["cameras"][cam_name] = {"ip": cam_ip, "online": cam_online}
        if not cam_online:
            all_cameras_online = False

    all_online = results["rcs"].get("online", False) and all_cameras_online
    results["all_online"] = all_online

    return {"online": all_online, "details": results}


# ==================== 图片检查和抓图函数 ====================

async def check_image_exists(task_no: str, bin_location: str, camera_type: str) -> bool:
    """检查指定相机类型的图片是否存在"""
    try:
        image_dir = project_root / "capture_img" / task_no / bin_location / camera_type

        if not image_dir.exists():
            logger.warning(f"图片目录不存在: {image_dir}")
            return False

        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        for ext in image_extensions:
            for common_name in ['main', 'MAIN', 'raw', 'RAW', 'image', 'IMAGE']:
                image_file = image_dir / f"{common_name}{ext}"
                if image_file.exists():
                    logger.info(f"找到图片文件: {image_file}")
                    return True

        for ext in image_extensions:
            image_files = list(image_dir.glob(f"*{ext}"))
            if image_files:
                logger.info(f"找到图片文件: {image_files[0]}")
                return True

        logger.warning(f"未找到图片文件: {image_dir}")
        return False

    except Exception as e:
        logger.error(f"检查图片存在性失败: {str(e)}")
        return False


async def execute_capture_script(script_path: str, task_no: str, bin_location: str) -> Dict[str, Any]:
    """执行单个抓图脚本"""
    conda_env = "tobacco_env"
    try:
        logger.info(f"在 Conda 环境 '{conda_env}' 中执行抓图脚本: {script_path}")

        cmd = ["conda", "run", "-n", conda_env, "python", script_path,
               "--task-no", task_no, "--bin-location", bin_location]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(project_root)  # 让子进程从项目根目录运行，C++ 相对路径才能解析正确
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            logger.info(f"抓图脚本执行成功: {script_path}")
            return {"success": True, "output": stdout.decode()}
        else:
            logger.error(f"抓图脚本执行失败: {script_path}, 错误: {stderr.decode()}")
            return {"success": False, "error": stderr.decode()}

    except Exception as e:
        logger.error(f"执行抓图脚本异常: {str(e)}")
        return {"success": False, "error": str(e)}


def _ping_camera(host: str, timeout: int = 3) -> bool:
    """检测相机是否网络可达"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, 8000))
        sock.close()
        return result == 0
    except Exception:
        return False


async def _capture_from_test_dir(task_no: str, bin_location: str, test_dir: str) -> Dict[str, Any]:
    """从本地测试目录复制图片到 capture_img，用于无相机环境调试"""
    import shutil

    CAMERA_NAMES = ["scan_1", "scan_2", "3d"]
    CAMERA_DIRS = ["scan_camera_1", "scan_camera_2", "3d_camera"]

    # 支持 ~ 展开为用户 home 目录
    base_src = Path(os.path.expanduser(test_dir))
    dest_base = project_root / "capture_img" / task_no / bin_location

    camera_results = {}

    for i, cam_dir in enumerate(CAMERA_DIRS):
        cam_name = CAMERA_NAMES[i]
        src_cam_dir = base_src / cam_dir
        dest_cam_dir = dest_base / cam_dir

        try:
            dest_cam_dir.mkdir(parents=True, exist_ok=True)

            if not src_cam_dir.exists():
                camera_results[cam_name] = {"success": False, "error": f"源目录不存在: {src_cam_dir}"}
                continue

            # 查找并复制目录中所有图片
            copied = False
            for ext in ["*.jpg", "*.png", "*.jpeg", "*.JPG", "*.PNG", "*.JPEG"]:
                for src_file in src_cam_dir.glob(ext):
                    shutil.copy2(src_file, dest_cam_dir / src_file.name)
                    copied = True

            if copied:
                logger.info(f"从测试目录复制 {cam_dir} 图片到: {dest_cam_dir}")
                camera_results[cam_name] = {"success": True, "image_count": len(list(dest_cam_dir.glob("*.jpg")) + list(dest_cam_dir.glob("*.png")))}
            else:
                camera_results[cam_name] = {"success": False, "error": f"目录 {cam_dir} 中未找到图片"}

        except Exception as e:
            camera_results[cam_name] = {"success": False, "error": str(e)}

    any_success = any(r.get("success") for r in camera_results.values())
    failed_cameras = [name for name, r in camera_results.items() if not r.get("success")]
    all_errors = [f"{name}: {r.get('error')}" for name, r in camera_results.items() if not r.get("success")]

    if any_success:
        logger.info(f"从测试目录复制图片完成: {task_no}/{bin_location}, 成功: {[n for n,r in camera_results.items() if r.get('success')]}, 失败: {failed_cameras}")
        return {
            "success": True,
            "partial": len(failed_cameras) > 0,
            "cameras": camera_results,
            "errors": all_errors,
            "photo3dPath": f"/{task_no}/{bin_location}/3d_camera/main.jpg" if camera_results.get("3d", {}).get("success") else None,
            "photoDepthPath": f"/{task_no}/{bin_location}/3d_camera/depth.jpg" if camera_results.get("3d", {}).get("success") else None,
            "photoScan1Path": f"/{task_no}/{bin_location}/scan_camera_1/main.jpg" if camera_results.get("scan_1", {}).get("success") else None,
            "photoScan2Path": f"/{task_no}/{bin_location}/scan_camera_2/main.jpg" if camera_results.get("scan_2", {}).get("success") else None,
            "image_count": camera_results.get("3d", {}).get("image_count", 0)
        }
    else:
        return {"success": False, "cameras": camera_results, "errors": all_errors}


async def capture_images_with_scripts(task_no: str, bin_location: str) -> Dict[str, Any]:
    """使用脚本抓取图片（带重试机制）

    如果配置了 CAMERA_TEST_DIR，则从本地目录复制图片用于测试；
    否则执行真实相机脚本。

    返回值包含:
    - success: bool, 至少有一个相机成功抓图
    - cameras: dict, 每个相机的成功/失败状态
    - errors: list, 失败的相机错误信息
    - photo3dPath / photoDepthPath / photoScan1Path / photoScan2Path: str, 已捕获的图片路径（可能为空）
    - image_count: int, 3d_camera 目录下的图片数量
    """
    from services.api.shared.config import CAPTURE_SCRIPTS, CAMERA_TEST_DIR

    # 如果配置了本地测试图片目录，直接从该目录复制
    if CAMERA_TEST_DIR:
        expanded = os.path.expanduser(CAMERA_TEST_DIR)
        logger.info(f"使用本地测试图片目录: {expanded}")
        return await _capture_from_test_dir(task_no, bin_location, CAMERA_TEST_DIR)

    # 相机名称映射: 脚本索引 → 名称/目录
    CAMERA_NAMES = ["scan_1", "scan_2", "3d"]
    CAMERA_DIRS = ["scan_camera_1", "scan_camera_2", "3d_camera"]

    max_retries = 5
    retry_count = 0

    # 成功的相机状态跨重试保留，只重试仍然失败的相机
    camera_results = {cam_name: {"success": False, "error": ""} for cam_name in CAMERA_NAMES}

    while retry_count < max_retries:
        # 检查仍然失败的相机
        failed_cameras = [name for name, r in camera_results.items() if not r.get("success")]
        if not failed_cameras:
            # 全部成功
            break

        try:
            if not _ping_camera("10.16.82.180"):
                logger.warning(f"相机 10.16.82.180 不可达，等待重试...")
                await asyncio.sleep(5)

            logger.info(f"开始抓图: {task_no}/{bin_location}, 第 {retry_count + 1} 次尝试，失败相机: {failed_cameras}")

            # 只对仍未成功的相机执行脚本
            for i, script_path in enumerate(CAPTURE_SCRIPTS):
                cam_name = CAMERA_NAMES[i]
                if camera_results[cam_name].get("success"):
                    # 已成功，跳过
                    continue
                if not os.path.exists(script_path):
                    camera_results[cam_name] = {"success": False, "error": "脚本不存在"}
                    logger.warning(f"抓图脚本不存在: {script_path}")
                    continue

                try:
                    result = await execute_capture_script(script_path, task_no, bin_location)
                    if result.get("success"):
                        camera_results[cam_name] = {"success": True}
                        logger.info(f"相机 {cam_name} 抓图成功")
                    else:
                        camera_results[cam_name] = {"success": False, "error": result.get("error", "未知错误")}
                        logger.warning(f"相机 {cam_name} 抓图失败: {result.get('error')}")
                except Exception as cam_err:
                    camera_results[cam_name] = {"success": False, "error": str(cam_err)}
                    logger.warning(f"相机 {cam_name} 抓图异常: {cam_err}")

            # 等待图片生成
            await asyncio.sleep(2)

            # 检查各目录下的图片（无论之前是否成功都检查，确保状态正确）
            for i, cam_name in enumerate(CAMERA_NAMES):
                cam_dir = project_root / "capture_img" / task_no / bin_location / CAMERA_DIRS[i]
                if cam_dir.exists():
                    image_files = list(cam_dir.glob("*.jpg")) + list(cam_dir.glob("*.png"))
                    if image_files:
                        camera_results[cam_name] = {"success": True, "image_count": len(image_files)}
                        logger.info(f"相机 {cam_name} 检测到图片文件 {len(image_files)} 张")
                    elif not camera_results[cam_name].get("success"):
                        camera_results[cam_name] = {"success": False, "error": "未生成图片文件"}
                elif not camera_results[cam_name].get("success"):
                    camera_results[cam_name] = {"success": False, "error": "目录不存在"}

            # 判断是否全部成功
            any_success = any(r.get("success") for r in camera_results.values())
            if any_success:
                logger.info(f"抓图完成: {task_no}/{bin_location}, 状态: {[n + ':' + ('成功' if r.get('success') else '失败:' + r.get('error', '')) for n, r in camera_results.items()]}")

            retry_count += 1
            if not any_success and retry_count < max_retries:
                await asyncio.sleep(5)

        except Exception as e:
            retry_count += 1
            logger.error(f"抓图失败 (尝试 {retry_count}/{max_retries}): {str(e)}")
            if retry_count < max_retries:
                await asyncio.sleep(5)

    # 组装返回结果
    any_success = any(r.get("success") for r in camera_results.values())
    failed_cameras = [name for name, r in camera_results.items() if not r.get("success")]
    all_errors = [f"{name}: {r.get('error', '未知错误')}" for name, r in camera_results.items() if not r.get("success")]

    if any_success:
        return {
            "success": True,
            "partial": len(failed_cameras) > 0,
            "cameras": camera_results,
            "errors": all_errors,
            "photo3dPath": f"/{task_no}/{bin_location}/3d_camera/main.jpg" if camera_results.get("3d", {}).get("success") else None,
            "photoDepthPath": f"/{task_no}/{bin_location}/3d_camera/depth.jpg" if camera_results.get("3d", {}).get("success") else None,
            "photoScan1Path": f"/{task_no}/{bin_location}/scan_camera_1/main.jpg" if camera_results.get("scan_1", {}).get("success") else None,
            "photoScan2Path": f"/{task_no}/{bin_location}/scan_camera_2/main.jpg" if camera_results.get("scan_2", {}).get("success") else None,
            "image_count": camera_results.get("3d", {}).get("image_count", 0)
        }
    else:
        return {"success": False, "cameras": camera_results, "errors": all_errors}


# ==================== 识别函数 ====================

def _extract_barcode_text_from_recognizer_result(br: dict) -> str | None:
    """从 barcode recognizer 返回的结果中提取真正的条码字符串

    BarcodeReaderCLI 返回的 output 是原始 JSON 字符串，形如：
    {"sessions": [{"barcodes": [{"text": "912503...", ...}]}]}
    需要先解析 JSON，再取 sessions[0].barcodes[0].text 才是真正的条码。
    """
    import json

    raw = br.get('output')
    if not raw:
        return br.get('text')

    try:
        data = json.loads(raw)
        sessions = data.get('sessions', [])
        for session in sessions:
            barcodes = session.get('barcodes', [])
            for bc in barcodes:
                text = bc.get('text')
                if text:
                    return text
    except Exception:
        pass

    return br.get('text')


async def run_barcode_and_detect(
    task_no: str,
    bin_location: str,
    scan_dirs: list[Path],
    detect_dir: Path,
    pile_id: int = 1,
    code_type: str = "ucc128"
) -> Dict[str, Any]:
    """执行条码识别和数量检测"""
    result = {
        "barcode_result": None,
        "detect_result": None,
        "photos": []
    }

    # 前置检查：相机拍照目录不能为空
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']

    # 检查 3d_camera 目录：必须同时有 main.jpg 和 depth.jpg 才算抓图成功
    has_main = False
    has_depth = False
    if detect_dir is not None and detect_dir.exists():
        has_main = (detect_dir / "main.jpg").exists()
        has_depth = (detect_dir / "depth.jpg").exists()
        # 兜底：也接受 main_rotated.jpg 和 raw.jpg
        if not has_main:
            for name in ['main_rotated', 'raw', 'image']:
                for ext in image_extensions:
                    if (detect_dir / f"{name}{ext}").exists():
                        has_main = True
                        break
                if has_main:
                    break
    if not has_main:
        result["detect_result"] = {"status": "failed", "error": "3D相机抓图失败：未找到main.jpg"}
        return result
    if not has_depth:
        result["detect_result"] = {"status": "failed", "error": "3D相机抓图失败：未找到depth.jpg"}
        return result

    # 检查 scan_camera 目录（至少有一个有图片即可）
    scan_ok = False
    for sd in scan_dirs:
        if sd is None or not sd.exists():
            continue
        try:
            for f in sd.iterdir():
                if f.is_file() and f.suffix.lower().lstrip('.') in [e.lstrip('.') for e in image_extensions]:
                    scan_ok = True
                    break
        except Exception:
            continue
        if scan_ok:
            break
    if not scan_ok:
        result["detect_result"] = {"status": "failed", "error": "扫码相机拍照失败：未找到图片"}
        return result

    # 条码识别：处理 scan_camera_1 和 scan_camera_2 目录
    if ENABLE_BARCODE and BARCODE_MODULE_AVAILABLE:
        try:
            from core.vision.barcode_recognizer import BarcodeRecognizer
            from services.api.shared.tobacco_resolver import get_tobacco_case_resolver

            recognizer = BarcodeRecognizer(code_type=code_type)
            all_barcode_results = []
            for scan_dir in scan_dirs:
                if scan_dir.exists():
                    barcode_results = recognizer.process_folder(input_dir=str(scan_dir))
                    all_barcode_results.extend(barcode_results)
            resolver = get_tobacco_case_resolver()

            resolved_info = None
            for br in all_barcode_results:
                barcode_text = _extract_barcode_text_from_recognizer_result(br)
                if barcode_text:
                    resolved_info = resolver.resolve(barcode_text)
                    if resolved_info['success']:
                        break

            if resolved_info and resolved_info['success']:
                pile_id = resolved_info['pile_id']
                result["barcode_result"] = {
                    "status": "success",
                    "six_digit_code": resolved_info['six_digit_code'],
                    "product_name": resolved_info['product_name'],
                    "tobacco_code": resolved_info['tobacco_code'],
                    "mapped_pile_id": pile_id
                }
            else:
                result["barcode_result"] = {
                    "status": "no_match",
                    "message": "未匹配到烟箱信息"
                }

            # 更新 pile_id
            result["pile_id"] = pile_id

        except Exception as e:
            logger.error(f"条码识别失败: {str(e)}")
            result["barcode_result"] = {"status": "failed", "error": str(e)}
    else:
        result["barcode_result"] = {"status": "disabled"}

    # 数量检测：处理 3d_camera 目录
    if DETECT_MODULE_AVAILABLE:
        try:
            from core.detection import count_boxes

            image_files = []

            for name in ['main', 'raw', 'image']:
                for ext in image_extensions:
                    common_file = detect_dir / f"{name}{ext}"
                    if common_file.exists():
                        image_files.append(common_file)
                        break
                if image_files:
                    break

            if not image_files:
                for ext in image_extensions:
                    image_files.extend(list(detect_dir.glob(f"*{ext}")))
                    if image_files:
                        break

            if image_files:
                depth_path = detect_dir / "depth.jpg"
                debug_output_dir = project_root / "debug" / task_no / bin_location
                debug_output_dir.mkdir(parents=True, exist_ok=True)
                total_count = count_boxes(
                    image_path=str(image_files[0]),
                    pile_id=pile_id,
                    depth_image_path=str(depth_path) if depth_path.exists() else None,
                    enable_debug=ENABLE_DEBUG,
                    enable_visualization=ENABLE_VISUALIZATION,
                    output_dir=str(debug_output_dir)
                )

                result["detect_result"] = {
                    "status": "success",
                    "total_count": total_count,
                    "pile_id": pile_id
                }
            else:
                result["detect_result"] = {"status": "failed", "error": "未找到图片"}

        except Exception as e:
            logger.error(f"数量检测失败: {str(e)}")
            result["detect_result"] = {"status": "failed", "error": str(e)}
    else:
        result["detect_result"] = {"status": "disabled"}

    return result


def _get_actual_spec(barcode_result: dict, inventory_item: dict | None) -> str:
    """根据扫码识别结果和系统库存决定实际品规

    优先级：
    1. 识别成功且有品名 → 用识别的品名
    2. 其他情况（识别失败/无匹配/无识别模块）→ "未识别"
    """
    if barcode_result.get("status") == "success" and barcode_result.get("product_name"):
        return barcode_result["product_name"]
    return "未识别"


# ==================== 单个储位处理函数 ====================

async def process_single_bin_location(
    task_no: str,
    bin_location: str,
    index: int,
    total: int,
    is_sim: bool = False
) -> Dict[str, Any]:
    """处理单个储位的完整流程"""
    result = {
        "binLocation": bin_location,
        "sequence": index + 1,
        "startTime": datetime.now().isoformat(),
        "endTime": None,
        "status": None,
        "actualQuantity": None,
        "actualSpec": None,
        "photo3dPath": None,
        "photoDepthPath": None,
        "photoScan1Path": "",
        "photoScan2Path": "",
        "error": None
    }

    try:
        if is_sim:
            # 模拟模式：END 等待由 execute_inventory_workflow 统一处理，此处直接拍照
            logger.info(f"模拟模式：处理储位 {bin_location}")

            from services.api.shared.config import WITH_CAMERA

            if WITH_CAMERA:
                # 不等待机器人，直接执行相机脚本
                logger.info(f"模拟模式 with_camera：执行相机脚本 for {bin_location}")
                capture_results = await capture_images_with_scripts(task_no, bin_location)

                # 全部相机失败 → 直接返回错误
                if not capture_results.get("success"):
                    result["status"] = "异常"
                    result["error"] = f"抓图失败: {capture_results.get('error', '所有相机抓图失败')}"
                    result["actualQuantity"] = 0
                    result["actualSpec"] = "无"
                    result["endTime"] = datetime.now().isoformat()
                    return result

                # 部分相机失败 → 记录警告，继续处理
                partial_errors = []
                if capture_results.get("partial"):
                    partial_errors = capture_results.get("errors", [])
                    logger.warning(f"部分相机抓图失败: {partial_errors}")

                # 先设置图片路径（即使后续识别失败，路径也已准备好）
                result["photo3dPath"] = f"/{task_no}/{bin_location}/3d_camera/main.jpg"
                result["photoDepthPath"] = f"/{task_no}/{bin_location}/3d_camera/depth.jpg"
                result["photoScan1Path"] = f"/{task_no}/{bin_location}/scan_camera_1/main.jpg"
                result["photoScan2Path"] = f"/{task_no}/{bin_location}/scan_camera_2/main.jpg"

                result["captureResults"] = capture_results

                # 执行识别
                capture_img_dir = project_root / "capture_img" / task_no / bin_location
                recognition_result = await run_barcode_and_detect(
                    task_no=task_no,
                    bin_location=bin_location,
                    scan_dirs=[capture_img_dir / "scan_camera_1", capture_img_dir / "scan_camera_2"],
                    detect_dir=capture_img_dir / "3d_camera",
                    pile_id=1,
                    code_type="ucc128"
                )

                detect_result = (recognition_result or {}).get("detect_result")
                barcode_result = (recognition_result or {}).get("barcode_result") or {}

                # 识别成功 → 更新为旋转/彩色后的路径
                if detect_result.get("status") == "success":
                    result["photo3dPath"] = f"/{task_no}/{bin_location}/3d_camera/main_rotated.jpg"
                    result["photoDepthPath"] = f"/{task_no}/{bin_location}/3d_camera/depth_color.jpg"

                # 识别失败（3D相机主图没找到）→ 仍返回已拍到的照片，quantity回退
                if detect_result.get("status") == "failed":
                    result["status"] = "异常"
                    # 优先报告部分抓图失败信息，其次报告检测失败信息
                    if partial_errors:
                        result["error"] = "相机抓图失败：" + "；".join(partial_errors)
                    else:
                        result["error"] = f"抓图失败：{detect_result.get('error', '未找到图片')}"
                    inventory_item = None
                    if task_no in _inventory_task_details and "inventoryItems" in _inventory_task_details[task_no]:
                        for item in _inventory_task_details[task_no]["inventoryItems"]:
                            if item.get("locationName") == bin_location:
                                inventory_item = item
                                break
                    result["actualSpec"] = _get_actual_spec(barcode_result, inventory_item)
                    result["actualQuantity"] = int(inventory_item.get("systemQuantity", 0) or 0) if inventory_item else 0
                    result["barcodeResult"] = barcode_result
                    result["detectResult"] = detect_result
                    result["photos"] = recognition_result.get("photos", [])
                    result["endTime"] = datetime.now().isoformat()
                    return result

                result["actualSpec"] = _get_actual_spec(barcode_result, None)

                result["status"] = "成功"
                result["actualQuantity"] = detect_result.get("total_count", 0)
                result["barcodeResult"] = barcode_result
                result["detectResult"] = detect_result
                result["photos"] = recognition_result.get("photos", [])
                result["endTime"] = datetime.now().isoformat()

                logger.info(f"模拟模式 with_camera：识别完成，数量: {result['actualQuantity']}, 品规: {result['actualSpec']}")

                # 更新任务状态
                if task_no in _inventory_task_bins:
                    for bin_status in _inventory_task_bins[task_no]:
                        if bin_status.bin_location == bin_location:
                            bin_status.image_data = {
                                "success": True,
                                "photo3dPath": result["photo3dPath"],
                                "photoDepthPath": result["photoDepthPath"]
                            }
                            bin_status.compute_result = {
                                "actualQuantity": result["actualQuantity"],
                                "actualSpec": result["actualSpec"]
                            }
                            bin_status.capture_time = result["startTime"]
                            bin_status.compute_time = datetime.now().isoformat()
                            bin_status.detect_result = detect_result
                            bin_status.barcode_result = barcode_result
                            break

                if task_no not in _inventory_task_details:
                    _inventory_task_details[task_no] = {}
                if bin_location not in _inventory_task_details[task_no]:
                    _inventory_task_details[task_no][bin_location] = {}
                _inventory_task_details[task_no][bin_location] = {
                    "binLocation": bin_location,
                    "actualQuantity": result["actualQuantity"],
                    "actualSpec": result["actualSpec"],
                    "photo3dPath": result["photo3dPath"],
                    "photoDepthPath": result["photoDepthPath"],
                    "photos": recognition_result.get("photos", [])
                }

                return result

            await asyncio.sleep(2)

            capture_img_dir = project_root / "capture_img" / task_no / bin_location

            if not capture_img_dir.exists():
                capture_img_dir.mkdir(parents=True, exist_ok=True)

                # 复制模拟图片
                public_dir = project_root / "web" / "src" / "public"
                image_mapping = [
                    ("1.jpg", "3d_camera", "main.jpg"),
                    ("2.jpg", "3d_camera", "depth.jpg"),
                    ("3.jpg", "scan_camera_1", "main.jpg"),
                    ("4.jpg", "scan_camera_2", "main.jpg")
                ]

                for img_file, camera_dir, dest_filename in image_mapping:
                    src_file = public_dir / img_file
                    dest_dir = capture_img_dir / camera_dir
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_file = dest_dir / dest_filename

                    if src_file.exists():
                        shutil.copy(src_file, dest_file)
                        logger.info(f"模拟模式：复制图片 {src_file} -> {dest_file}")
                    else:
                        logger.warning(f"模拟图片不存在: {src_file}")

            result["photo3dPath"] = f"/{task_no}/{bin_location}/3d_camera/main_rotated.jpg"
            result["photoDepthPath"] = f"/{task_no}/{bin_location}/3d_camera/depth_color.jpg"
            result["photoScan1Path"] = f"/{task_no}/{bin_location}/scan_camera_1/main.jpg"
            result["photoScan2Path"] = f"/{task_no}/{bin_location}/scan_camera_2/main.jpg"

            logger.info(f"模拟模式：抓图成功: {bin_location}")

            # 执行识别
            recognition_result = await run_barcode_and_detect(
                task_no=task_no,
                bin_location=bin_location,
                scan_dirs=[capture_img_dir / "scan_camera_1", capture_img_dir / "scan_camera_2"],
                detect_dir=capture_img_dir / "3d_camera",
                pile_id=1,
                code_type="ucc128"
            )

            detect_result = (recognition_result or {}).get("detect_result") or {}
            barcode_result = (recognition_result or {}).get("barcode_result") or {}

            # 抓图失败（未找到图片）或识别异常 → 报错，标记为异常
            # 识别成功（即使数量为0）→ 成功，使用检测数量
            if detect_result.get("status") == "failed":
                result["status"] = "异常"
                result["error"] = f"抓图失败：{detect_result.get('error', '未找到图片')}"
                # 回退到系统数量作为备用
                inventory_item = None
                if task_no in _inventory_task_details and "inventoryItems" in _inventory_task_details[task_no]:
                    for item in _inventory_task_details[task_no]["inventoryItems"]:
                        if item.get("locationName") == bin_location:
                            inventory_item = item
                            break
                result["actualSpec"] = _get_actual_spec(barcode_result, inventory_item)
                result["actualQuantity"] = int(inventory_item.get("systemQuantity", 0) or 0) if inventory_item else 0
                result["barcodeResult"] = barcode_result
                result["detectResult"] = detect_result
                result["photos"] = recognition_result.get("photos", [])
                result["endTime"] = datetime.now().isoformat()
                return result

            result["actualSpec"] = _get_actual_spec(barcode_result, None)

            result["status"] = "成功"
            result["actualQuantity"] = detect_result.get("total_count", 0)
            result["barcodeResult"] = barcode_result
            result["detectResult"] = detect_result
            result["photos"] = recognition_result.get("photos", [])

            logger.info(f"模拟模式：识别完成，数量: {result['actualQuantity']}, 品规: {result['actualSpec']}")

            # 更新任务状态
            if task_no in _inventory_task_bins:
                for bin_status in _inventory_task_bins[task_no]:
                    if bin_status.bin_location == bin_location:
                        bin_status.image_data = {
                            "success": True,
                            "photo3dPath": result["photo3dPath"],
                            "photoDepthPath": result["photoDepthPath"]
                        }
                        bin_status.compute_result = {
                            "actualQuantity": result["actualQuantity"],
                            "actualSpec": result["actualSpec"]
                        }
                        bin_status.capture_time = result["startTime"]
                        bin_status.compute_time = datetime.now().isoformat()
                        bin_status.detect_result = detect_result
                        bin_status.barcode_result = barcode_result
                        break

            # 存储详细结果
            if task_no not in _inventory_task_details:
                _inventory_task_details[task_no] = {}

            _inventory_task_details[task_no][bin_location] = {
                "image_data": {
                    "success": True,
                    "photo3dPath": result["photo3dPath"],
                    "photoDepthPath": result["photoDepthPath"]
                },
                "compute_result": {
                    "actualQuantity": result["actualQuantity"],
                    "actualSpec": result["actualSpec"]
                },
                "capture_time": result["startTime"],
                "compute_time": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "recognition": recognition_result
            }

            result["status"] = "成功"
            result["endTime"] = datetime.now().isoformat()

        else:
            # 真实模式：wait_for_robot_status 已在 execute_inventory_workflow 层处理，此处直接拍照
            logger.info(f"============拍照: {bin_location}")
            try:
                capture_results = await capture_images_with_scripts(task_no, bin_location)
                result["captureResults"] = capture_results

                if not capture_results.get("success"):
                    logger.error(f"抓图失败，跳过储位: {bin_location}")
                    result["status"] = "异常"
                    result["error"] = f"抓图失败: {capture_results.get('error', '所有相机抓图失败')}"
                    result["actualQuantity"] = 0
                    result["actualSpec"] = "无"
                    result["endTime"] = datetime.now().isoformat()
                    return result

                # 部分相机失败 → 记录警告，继续处理
                if capture_results.get("partial"):
                    logger.warning(f"部分相机抓图失败: {capture_results.get('errors', [])}")

                logger.info(f"抓图成功: {bin_location}")

                # 先用原始抓图路径；检测成功后会被旋转/彩色路径替代
                result["photo3dPath"] = f"/{task_no}/{bin_location}/3d_camera/main.jpg"
                result["photoDepthPath"] = f"/{task_no}/{bin_location}/3d_camera/depth.jpg"
                result["photoScan1Path"] = f"/{task_no}/{bin_location}/scan_camera_1/main.jpg"
                result["photoScan2Path"] = f"/{task_no}/{bin_location}/scan_camera_2/main.jpg"

                capture_img_dir = project_root / "capture_img" / task_no / bin_location

                recognition_result = await run_barcode_and_detect(
                    task_no=task_no,
                    bin_location=bin_location,
                    scan_dirs=[capture_img_dir / "scan_camera_1", capture_img_dir / "scan_camera_2"],
                    detect_dir=capture_img_dir / "3d_camera",
                    pile_id=1,
                    code_type="ucc128"
                )

                detect_result = (recognition_result or {}).get("detect_result") or {}
                barcode_result = (recognition_result or {}).get("barcode_result") or {}

                # 识别成功 → 更新为旋转/彩色后的路径
                if detect_result.get("status") == "success":
                    result["photo3dPath"] = f"/{task_no}/{bin_location}/3d_camera/main_rotated.jpg"
                    result["photoDepthPath"] = f"/{task_no}/{bin_location}/3d_camera/depth_color.jpg"

                # 识别失败（3D相机主图没找到）→ 仍返回已拍到的照片
                if detect_result.get("status") == "failed":
                    result["status"] = "异常"
                    if capture_results.get("partial"):
                        result["error"] = "相机抓图失败：" + "；".join(capture_results.get("errors", []))
                    else:
                        result["error"] = f"抓图失败：{detect_result.get('error', '未找到图片')}"
                    inventory_item = None
                    if task_no in _inventory_task_details and "inventoryItems" in _inventory_task_details[task_no]:
                        for item in _inventory_task_details[task_no]["inventoryItems"]:
                            if item.get("locationName") == bin_location:
                                inventory_item = item
                                break
                    result["actualSpec"] = _get_actual_spec(barcode_result, inventory_item)
                    result["actualQuantity"] = int(inventory_item.get("systemQuantity", 0) or 0) if inventory_item else 0
                    result["barcodeResult"] = barcode_result
                    result["detectResult"] = detect_result
                    result["photos"] = recognition_result.get("photos", [])
                    result["endTime"] = datetime.now().isoformat()
                    return result

                result["actualSpec"] = _get_actual_spec(barcode_result, None)

                result["status"] = "成功"
                result["actualQuantity"] = detect_result.get("total_count", 0)
                result["barcodeResult"] = barcode_result
                result["detectResult"] = detect_result
                result["photos"] = recognition_result.get("photos", [])

                # 更新任务状态
                if task_no in _inventory_task_bins:
                    for bin_status in _inventory_task_bins[task_no]:
                        if bin_status.bin_location == bin_location:
                            bin_status.image_data = capture_results
                            bin_status.compute_result = {
                                "actualQuantity": result["actualQuantity"],
                                "actualSpec": result["actualSpec"]
                            }
                            bin_status.capture_time = result["startTime"]
                            bin_status.compute_time = datetime.now().isoformat()
                            bin_status.detect_result = detect_result
                            bin_status.barcode_result = barcode_result
                            break

                if task_no not in _inventory_task_details:
                    _inventory_task_details[task_no] = {}

                _inventory_task_details[task_no][bin_location] = {
                    "image_data": capture_results,
                    "compute_result": {
                        "actualQuantity": result["actualQuantity"],
                        "actualSpec": result["actualSpec"]
                    },
                    "capture_time": result["startTime"],
                    "compute_time": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "recognition": recognition_result
                }

                result["status"] = "成功"
                result["endTime"] = datetime.now().isoformat()

            except Exception as e:
                logger.error(f"真实模式拍照/识别异常: {str(e)}")
                result["status"] = "异常"
                result["error"] = str(e)
                result["actualQuantity"] = 0
                result["actualSpec"] = "无"
                result["endTime"] = datetime.now().isoformat()

    except Exception as e:
        result["status"] = "异常"
        result["error"] = str(e)
        result["actualQuantity"] = 0
        result["actualSpec"] = "无"
        result["endTime"] = datetime.now().isoformat()
        logger.error(f"处理储位失败 {bin_location}: {str(e)}")

    return result


# ==================== 完整工作流执行函数 ====================

async def execute_inventory_workflow(task_no: str, bin_locations: List[str], is_sim: bool = False):
    """执行完整的盘点工作流"""
    from services.api.shared.operation_log import log_operation

    logger.info(f"开始执行盘点工作流: {task_no}, 共 {len(bin_locations)} 个储位, 模拟模式: {is_sim}")

    # 初始化任务状态
    task_status = TaskStatus(
        task_no=task_no,
        status="init",
        current_step=0,
        total_steps=len(bin_locations),
        start_time=datetime.now().isoformat()
    )

    _inventory_tasks[task_no] = task_status

    # 初始化每个储位的状态
    bin_statuses = [
        BinLocationStatus(
            bin_location=location,
            status="pending",
            sequence=index + 1
        )
        for index, location in enumerate(bin_locations)
    ]
    _inventory_task_bins[task_no] = bin_statuses

    # 更新任务状态为运行中
    _inventory_tasks[task_no].status = "running"
    _inventory_tasks[task_no].current_step = 0

    # 写入持久化状态，服务器重启后可识别中断任务
    mark_running(task_no, len(bin_locations))

    # 预检：检查 RCS 和相机系统是否在线
    from services.api.shared.config import WITH_CAMERA
    check_result = await check_systems_online(is_sim, WITH_CAMERA)
    details = check_result.get("details", {})

    cam_status_str = details.get('cameras', {}).get('status', '')
    cam_online = details.get('cameras', {}).get('online', False)
    if '跳过' in cam_status_str:
        cam_display = cam_status_str
    else:
        cam_display = f"在线" if cam_online else str(details.get('cameras', {}))
    logger.info(f"系统在线检查: RCS={'在线' if details.get('rcs',{}).get('online') else '离线'}, 相机={cam_display}")

    if not check_result.get("online"):
        rcs_status = details.get("rcs", {})
        cam_status = details.get("cameras", {})
        rcs_info = f"RCS ({rcs_status.get('host','?')})" + ("在线" if rcs_status.get("online") else "离线")
        cam_info = cam_status.get("status", str(cam_status))

        offline_parts = []
        if not rcs_status.get("online"):
            offline_parts.append("RCS")
        if isinstance(cam_status, dict):
            for cam_name, cam_info in cam_status.items():
                if isinstance(cam_info, dict) and not cam_info.get("online"):
                    offline_parts.append(f"{cam_name} ({cam_info.get('ip','?')})")

        error_msg = f"系统离线，无法发起盘点：" + "、".join(offline_parts)
        logger.error(error_msg)
        offline_types = set()
        if not rcs_status.get("online"):
            offline_types.add("rcs")
        if isinstance(cam_status, dict):
            for cam_name, cam_detail in cam_status.items():
                if isinstance(cam_detail, dict) and not cam_detail.get("online"):
                    offline_types.add("camera")
                    break
        error_type = "rcs" if "rcs" in offline_types else ("camera" if "camera" in offline_types else "other")
        _inventory_tasks[task_no].status = "failed"
        _inventory_tasks[task_no].end_time = datetime.now().isoformat()
        _inventory_tasks[task_no].error_message = error_msg
        _inventory_tasks[task_no].error_type = error_type
        return {
            "success": False,
            "message": error_msg,
            "errorType": error_type,
            "task_no": task_no,
            "check_details": details
        }

    # 存储所有储位的盘点结果
    inventory_results = []

    try:
        logger.info(f"开始处理 {len(bin_locations)} 个储位")

        # 先将所有储位状态设为运行中
        if task_no in _inventory_task_bins:
            for bin_status in _inventory_task_bins[task_no]:
                bin_status.status = "running"

        if is_sim:
            # ====== 模拟模式：aiohttp 批量下发（不阻塞） → 逐个等待 END → 拍照 → 发 continue ======
            # aiohttp 不阻塞事件循环，END 回调到达时能正常处理，不会丢失。
            logger.info(f"模拟模式：aiohttp 批量下发 {len(bin_locations)} 个库位（间隔 0.5s）")
            submit_result = await submit_inventory_task(task_no, bin_locations, is_sim=True)
            # 保存 robot_task_code，供取消时使用
            if task_no in _inventory_tasks:
                _inventory_tasks[task_no].robot_task_code = submit_result.get("robotTaskCode", "ctu001")
            if not submit_result.get("success"):
                error_msg = submit_result.get("message", "盘点任务下发失败")
                _inventory_tasks[task_no].status = "failed"
                _inventory_tasks[task_no].end_time = datetime.now().isoformat()
                _inventory_tasks[task_no].error_message = error_msg
                _inventory_tasks[task_no].error_type = "rcs"
                return {"success": False, "message": error_msg, "errorType": "rcs", "task_no": task_no}
            logger.info(f"全部 {len(bin_locations)} 个库位已下发完毕，等待 END 回调...")

            # 逐个等待 END：收到 END → 拍照 → 发 continue
            for i in range(len(bin_locations)):
                # 清空队列中的旧状态，防止上一轮残留的 END 干扰
                clear_robot_status_queue()

                # 检查任务是否已被取消
                if task_no in _inventory_tasks and _inventory_tasks[task_no].status == "cancelled":
                    logger.warning(f"任务 {task_no} 已被取消，退出等待循环")
                    break

                # 等待 END（队列支持多 END 并发到达，不会丢失）
                resolved_bin = bin_locations[i]
                timeout_occurred = False
                try:
                    ctu_status = await wait_for_robot_status("end", timeout=600)
                    bin_code = ctu_status.get("binCode", "")
                    resolved_bin = bin_code or bin_locations[i]
                    if bin_code:
                        logger.info(f"END 回调携带 binCode: {bin_code}")
                except asyncio.TimeoutError:
                    logger.error(f"等待 END 超时，跳过库位: {resolved_bin}")
                    inventory_results.append({
                        "binLocation": resolved_bin, "status": "异常",
                        "actualQuantity": None, "actualSpec": "无",
                        "error": "等待 END 超时",
                        "photo3dPath": None, "photoDepthPath": None,
                        "photoScan1Path": "", "photoScan2Path": "",
                        "specName": "", "systemQuantity": 0, "difference": 0,
                    })
                    update_progress(task_no, len(inventory_results))
                    timeout_occurred = True

                # 取消后不再发送 continue，避免 RCS 卡在等待继续指令的状态
                if task_no in _inventory_tasks and _inventory_tasks[task_no].status == "cancelled":
                    logger.warning(f"任务 {task_no} 已被取消，跳过 continue，退出等待循环")
                    break
                try:
                    await continue_inventory_task(is_sim=True, robot_task_code=submit_result.get("robotTaskCode", "ctu001"))
                except Exception as e:
                    logger.error(f"发送 continue 失败: {str(e)}")

                if timeout_occurred:
                    continue

                # 拍照
                # 更新进度：反映实际已收到 END 的数量
                _inventory_tasks[task_no].current_step = len(inventory_results) + 1
                logger.info(f"已收到 END: {resolved_bin}，拍照...")
                try:
                    result = await process_single_bin_location(task_no, resolved_bin, i, len(bin_locations), is_sim=True)
                except Exception as e:
                    logger.error(f"处理库位 {resolved_bin} 时发生异常: {str(e)}")
                    result = {
                        "status": "异常", "error": f"处理库位异常: {str(e)}",
                        "actualQuantity": None, "actualSpec": "无",
                        "photo3dPath": None, "photoDepthPath": None,
                        "photoScan1Path": "", "photoScan2Path": "",
                    }

                # 更新 bin 状态 & 收集结果
                if task_no in _inventory_task_bins:
                    for bs in _inventory_task_bins[task_no]:
                        if bs.bin_location == resolved_bin:
                            bs.status = "completed" if result.get("status") == "成功" else "failed"
                            break

                inventory_item = None
                if task_no in _inventory_task_details and "inventoryItems" in _inventory_task_details[task_no]:
                    for item in _inventory_task_details[task_no]["inventoryItems"]:
                        if item.get("locationName") == resolved_bin:
                            inventory_item = item
                            break

                actual_qty = int(result.get("actualQuantity", 0) or 0)
                system_qty = int(inventory_item.get("systemQuantity", 0) or 0) if inventory_item else 0
                inventory_results.append({
                    "binLocation": resolved_bin,
                    "status": result.get("status"),
                    "actualQuantity": result.get("actualQuantity"),
                    "actualSpec": result.get("actualSpec"),
                    "photo3dPath": result.get("photo3dPath"),
                    "photoDepthPath": result.get("photoDepthPath"),
                    "photoScan1Path": result.get("photoScan1Path", ""),
                    "photoScan2Path": result.get("photoScan2Path", ""),
                    "error": result.get("error"),
                    "specName": inventory_item.get("productName", "") if inventory_item else "",
                    "systemQuantity": system_qty,
                    "difference": actual_qty - system_qty,
                })
                update_progress(task_no, len(inventory_results))

        else:
            async with _real_mode_lock:
                # ====== 真实模式：批量下发 → 逐个等待 END → 拍照 → 发 continue ======
                logger.info(f"真实模式：批量下发 {len(bin_locations)} 个库位（间隔 0.5s）")
                submitted_bins: List[str] = []
                # 记录每个 bin_location 对应的 robot_task_code，等待 END 时需要用它发 continue
                bin_to_task_code: Dict[str, str] = {}
                for i, bin_location in enumerate(bin_locations):
                    submit_result = await submit_inventory_task(task_no, [bin_location], is_sim=False)
                    robot_task_code = submit_result.get("robotTaskCode", "")
                    # 保存 robot_task_code，供取消时使用
                    if task_no in _inventory_tasks:
                        _inventory_tasks[task_no].robot_task_code = robot_task_code
                    bin_to_task_code[bin_location] = robot_task_code
                    submitted_bins.append(bin_location)
                    logger.info(f"第 {i+1}/{len(bin_locations)} 个库位已下发: {bin_location}, robotTaskCode={robot_task_code}")
                    if i < len(bin_locations) - 1:
                        await asyncio.sleep(0.5)
                logger.info(f"全部 {len(submitted_bins)} 个库位已下发完毕，等待 END 回调...")
    
                # 逐个等待 END：每次收到 END → 拍照 → 发 continue
                # 用 set 记录已处理过的 bin 和 robotTaskCode，防止 RCS 重复发 END 导致重复处理和重复发 continue
                completed_bins: set = set()
                completed_robot_codes: set = set()
                pending_count = len(submitted_bins)
                for _ in range(pending_count):
                    # 检查任务是否已被取消，避免在用户取消后继续空等 END
                    if task_no in _inventory_tasks and _inventory_tasks[task_no].status == "cancelled":
                        logger.warning(f"任务 {task_no} 已被取消，退出等待循环")
                        break
                    # 初始化，防止 timeout 时变量未定义
                    bin_location = ""
                    rt_code = ""
                    result = None
                    timeout_occurred = False
                    # 传入当前任务的所有有效 robotTaskCode，过滤掉上一个任务残留的旧回调
                    valid_robot_codes = set(bin_to_task_code.values())
                    try:
                        ctu_status = await wait_for_robot_status("end", timeout=600, valid_robot_codes=valid_robot_codes)
                        bin_code = ctu_status.get("binCode", "")
                        # 优先用回调中的 binCode，若取不到则按顺序匹配
                        if not bin_code:
                            idx = len(inventory_results)
                            bin_location = submitted_bins[idx] if idx < len(submitted_bins) else ""
                            logger.warning(f"END 回调未含 binCode，按顺序匹配为: {bin_location}")
                        else:
                            bin_location = bin_code
                            logger.info(f"END 回调携带 binCode: {bin_location}")
    
                        # robotTaskCode 始终从 bin_to_task_code 映射中取，不信任回调里的值
                        expected_rt_code = bin_to_task_code.get(bin_location, "")
                        callback_rt_code = ctu_status.get("robotTaskCode", "")
                        logger.info(f"[END 校验] bin={bin_location}，映射 rt_code={expected_rt_code}，回调 rt_code={callback_rt_code}")
    
                        # 校验 1：bin 去重
                        if bin_location in completed_bins:
                            logger.warning(f"[END 校验] bin={bin_location} 已处理过，跳过本次 END 回调，不发 continue")
                            continue
    
                        # 校验 2：robotTaskCode 去重
                        if expected_rt_code and expected_rt_code in completed_robot_codes:
                            logger.warning(f"[END 校验] rt_code={expected_rt_code} 已响应过，跳过本次 END 回调，不发 continue")
                            continue
    
                        # 校验 3：回调中的 robotTaskCode 与映射中的 expected_rt_code 校验一致性
                        if callback_rt_code and expected_rt_code and callback_rt_code != expected_rt_code:
                            logger.warning(f"[END 校验] 回调 rt_code={callback_rt_code} 与映射 rt_code={expected_rt_code} 不一致，以映射为准，继续处理")
    
                        rt_code = expected_rt_code
                        logger.info(f"[END 校验] 校验通过，bin={bin_location}，rt_code={rt_code}，开始处理")
    
                        # 标记为已处理，防止 RCS 重复 END 导致重复处理
                        completed_bins.add(bin_location)
                        completed_robot_codes.add(rt_code)
    
                        # 更新进度：反映实际已收到 END 的数量
                        _inventory_tasks[task_no].current_step = len(inventory_results) + 1
    
                        logger.info(f"等待库位 END 完成: {bin_location}，拍照...")
                        result = await process_single_bin_location(task_no, bin_location, 0, len(bin_locations), is_sim=False)
                    except asyncio.TimeoutError:
                        logger.error(f"等待 END 超时，跳过库位")
                        _inventory_tasks[task_no].current_step = len(inventory_results)
                        # 超时时按顺序推算 bin_location（用 bin_to_task_code 的第一个未完成项兜底）
                        idx = len(inventory_results)
                        bin_location = submitted_bins[idx] if idx < len(submitted_bins) else ""
                        rt_code = bin_to_task_code.get(bin_location, "")
                        result = {
                            "status": "异常", "error": "等待 END 超时",
                            "actualQuantity": None, "actualSpec": "无",
                            "photo3dPath": None, "photoDepthPath": None,
                            "photoScan1Path": "", "photoScan2Path": "",
                        }
                        timeout_occurred = True
                    except Exception as e:
                        logger.error(f"处理库位 {bin_location} 时发生异常: {str(e)}")
                        result = {
                            "status": "异常", "error": f"处理库位异常: {str(e)}",
                            "actualQuantity": None, "actualSpec": "无",
                            "photo3dPath": None, "photoDepthPath": None,
                            "photoScan1Path": "", "photoScan2Path": "",
                        }
    
                    # 更新 bin 状态
                    if bin_location and task_no in _inventory_task_bins:
                        for bs in _inventory_task_bins[task_no]:
                            if bs.bin_location == bin_location:
                                bs.status = "completed" if result and result.get("status") == "成功" else "failed"
                                break
    
                    # 取消后不再发送 continue，避免 RCS 卡在等待继续指令的状态
                    if task_no in _inventory_tasks and _inventory_tasks[task_no].status == "cancelled":
                        logger.warning(f"任务 {task_no} 已被取消，跳过 continue，退出等待循环")
                        break
                    # 拍照完成后，用该 bin 对应的 robot_task_code 发送 continue
                    # 发 continue 前再次确认 rt_code 与当前任务有效集合一致，防止旧任务代码残留
                    if not rt_code:
                        logger.error(f"[continue 校验] rt_code 为空，拒绝发送 continue（bin={bin_location}）")
                    elif rt_code not in valid_robot_codes:
                        logger.error(f"[continue 校验] rt_code={rt_code} 不在当前任务有效集合中，拒绝发送 continue（bin={bin_location}）")
                    else:
                        logger.info(f"[continue 校验] 校验通过，发送 continue → bin={bin_location}, rt_code={rt_code}")
                        try:
                            continue_result = await continue_inventory_task(is_sim=False, robot_task_code=rt_code)
                            logger.info(f"continue 调用结果 (bin={bin_location}, robotTaskCode={rt_code}): {continue_result}")
                        except Exception as e:
                            logger.error(f"发送 continue 失败: {str(e)}")
    
                    if timeout_occurred:
                        continue
    
                    # 查找匹配储位信息
                    inventory_item = None
                    if task_no in _inventory_task_details and "inventoryItems" in _inventory_task_details[task_no]:
                        for item in _inventory_task_details[task_no]["inventoryItems"]:
                            if item.get("locationName") == bin_location:
                                inventory_item = item
                                break
    
                    actual_qty = int(result.get("actualQuantity", 0) or 0)
                    system_qty = int(inventory_item.get("systemQuantity", 0) or 0) if inventory_item else 0
                    inventory_results.append({
                        "binLocation": bin_location,
                        "status": result.get("status"),
                        "actualQuantity": result.get("actualQuantity"),
                        "actualSpec": result.get("actualSpec"),
                        "photo3dPath": result.get("photo3dPath"),
                        "photoDepthPath": result.get("photoDepthPath"),
                        "photoScan1Path": result.get("photoScan1Path", ""),
                        "photoScan2Path": result.get("photoScan2Path", ""),
                        "error": result.get("error"),
                        "specName": inventory_item.get("productName", "") if inventory_item else "",
                        "systemQuantity": system_qty,
                        "difference": actual_qty - system_qty,
                    })
                    update_progress(task_no, len(inventory_results))
                    logger.info(f"库位 {bin_location} 处理完毕，已处理 {len(inventory_results)}/{pending_count} 个")
    
                # 主循环结束后，强制等待所有剩余 END 回调到达，确保最后一个 bin 的 continue 真正被 RCS 响应后再标记完成
                # 防止 END 还在队列里未被消费时任务就标记 completed，导致 RCS 收不到最后一个 END 而一直等待
                remaining = pending_count - len(inventory_results)
                if remaining > 0:
                    logger.info(f"主循环结束，已处理 {len(inventory_results)}/{pending_count} 个，"
                                f"还有 {remaining} 个 END 未收到，等待它们到达...")
                    valid_robot_codes = set(bin_to_task_code.values())
                    waited_count = 0
                    while waited_count < remaining:
                        try:
                            ctu_status = await wait_for_robot_status("end", timeout=120, valid_robot_codes=valid_robot_codes)
                            bin_code = ctu_status.get("binCode", "")
                            if not bin_code:
                                bin_code = submitted_bins[len(inventory_results)] if len(inventory_results) < len(submitted_bins) else ""
                            expected_rt_code = bin_to_task_code.get(bin_code, "")
                            callback_rt_code = ctu_status.get("robotTaskCode", "")
                            logger.info(f"[END 校验-尾声] bin={bin_code}，映射 rt_code={expected_rt_code}，回调 rt_code={callback_rt_code}")
                            # 校验 1：bin 去重
                            if bin_code in completed_bins:
                                logger.warning(f"[END 校验-尾声] bin={bin_code} 已处理过，跳过")
                                continue
                            # 校验 2：robotTaskCode 去重
                            if expected_rt_code and expected_rt_code in completed_robot_codes:
                                logger.warning(f"[END 校验-尾声] rt_code={expected_rt_code} 已响应过，跳过")
                                continue
                            logger.info(f"[END 校验-尾声] 校验通过，bin={bin_code}，rt_code={expected_rt_code}，追加结果")
                            completed_bins.add(bin_code)
                            completed_robot_codes.add(expected_rt_code)
                            # 最后一轮的 END 不再拍照，直接追加成功状态
                            inventory_results.append({
                                "binLocation": bin_code,
                                "status": "成功",
                                "actualQuantity": 0,
                                "actualSpec": "",
                                "photo3dPath": None,
                                "photoDepthPath": None,
                                "photoScan1Path": "",
                                "photoScan2Path": "",
                                "error": None,
                                "specName": "",
                                "systemQuantity": 0,
                                "difference": 0,
                            })
                            waited_count += 1
                            update_progress(task_no, len(inventory_results))
                            logger.info(f"追加 END 结果，已处理 {len(inventory_results)}/{pending_count} 个")
                        except asyncio.TimeoutError:
                            logger.warning(f"等待尾声 END 超时（{remaining - waited_count} 个未收到），跳过")
                            break
    
                logger.info(f"所有 {len(bin_locations)} 个储位处理完成")

        # 判断任务整体状态：全部成功 / 部分失败 / 全部失败
        success_count = sum(1 for r in inventory_results if r.get("status") == "成功")
        failed_count = len(inventory_results) - success_count

        if failed_count == 0:
            task_status = "completed"
        elif success_count == 0:
            task_status = "failed"
        else:
            task_status = "partial"

        _inventory_tasks[task_no].status = task_status
        _inventory_tasks[task_no].current_step = len(bin_locations)
        _inventory_tasks[task_no].end_time = datetime.now().isoformat()
        mark_finished(task_no, task_status)

        # 广播任务状态变更通知，所有连接的客户端都会收到（用于其他用户的任务完成提示）
        user_info = _inventory_task_details.get(task_no, {}).get("userInfo", {})
        broadcast_data = {
            "taskNo": task_no,
            "status": task_status,
            "operatorName": user_info.get("userName", ""),
            "successCount": success_count,
            "failedCount": failed_count,
        }
        await ws_manager.broadcast_task_event(
            f"task_{task_status}",
            task_no,
            broadcast_data
        )

        # 全部失败时，聚合各库位错误原因
        if task_status == "failed" and inventory_results:
            failed_errors = [r.get("error") or "未知错误" for r in inventory_results if r.get("status") in ("异常", "失败")]
            if failed_errors:
                _inventory_tasks[task_no].error_message = "；".join(failed_errors)

        # 保存盘点结果到任务详情
        if task_no not in _inventory_task_details:
            _inventory_task_details[task_no] = {}

        _inventory_task_details[task_no]["inventoryResults"] = inventory_results

        logger.info(f"盘点任务{task_status}: {task_no}, 成功 {success_count}/{len(bin_locations)} 个库位")
        logger.info(f"盘点结果: {inventory_results}")

        # 从任务详情中获取用户信息
        user_info = _inventory_task_details.get(task_no, {}).get("userInfo", {})

        # 记录任务完成
        log_operation(
            operation_type="inventory",
            action="盘点任务完成" if task_status == "completed" else ("盘点任务部分完成" if task_status == "partial" else "盘点任务失败"),
            user_id=user_info.get("userId"),
            user_name=user_info.get("userName"),
            target=task_no,
            status=task_status,
            details={
                "task_no": task_no,
                "bin_locations": bin_locations,
                "completed_count": success_count,
                "failed_count": failed_count,
            }
        )

        # 自动保存：只要相机拍了照片（capture_img 目录存在），就将结果写入历史 Excel
        capture_img_dir = project_root / "capture_img" / task_no
        if capture_img_dir.exists() and inventory_results:
            try:
                # 从任务详情中获取操作员信息
                user_info = _inventory_task_details.get(task_no, {}).get("userInfo", {})
                operator_name = user_info.get("userName", "")

                df = build_excel_data(
                    task_no=task_no,
                    inventory_results=inventory_results,
                    operator_name=operator_name,
                    is_valid=False,
                )
                write_excel(task_no, df)
                logger.info(f"自动保存盘点结果到历史: {task_no}")
            except Exception as save_err:
                logger.error(f"自动保存失败 {task_no}: {save_err}")

    except Exception as e:
        if task_no in _inventory_tasks:
            _inventory_tasks[task_no].status = "failed"
            _inventory_tasks[task_no].end_time = datetime.now().isoformat()
        mark_finished(task_no, "failed")

        # 广播任务失败通知
        user_info = _inventory_task_details.get(task_no, {}).get("userInfo", {})
        await ws_manager.broadcast_task_event(
            "task_failed",
            task_no,
            {
                "taskNo": task_no,
                "status": "failed",
                "operatorName": user_info.get("userName", ""),
                "error": str(e),
            }
        )

        # 从任务详情中获取用户信息
        user_info = _inventory_task_details.get(task_no, {}).get("userInfo", {})

        log_operation(
            operation_type="inventory",
            action="盘点任务失败",
            user_id=user_info.get("userId"),
            user_name=user_info.get("userName"),
            target=task_no,
            status="failed",
            details={
                "task_no": task_no,
                "error": str(e),
                "failed_at_step": _inventory_tasks[task_no].current_step if task_no in _inventory_tasks else 0
            }
        )

        logger.error(f"盘点任务失败: {task_no}, 错误: {str(e)}")
