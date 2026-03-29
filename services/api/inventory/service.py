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

# 添加项目根目录到路径
_project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from services.api.shared.models import (
    TaskStatus,
    BinLocationStatus,
)
from services.api.shared.config import (
    logger,
    project_root,
    RCS_BASE_URL,
    RCS_PREFIX,
    ENABLE_BARCODE,
    BARCODE_MODULE_AVAILABLE,
    DETECT_MODULE_AVAILABLE,
    ENABLE_DEBUG,
    ENABLE_VISUALIZATION,
)

# RCS_PREFIX 默认值
RCS_PREFIX = os.getenv("RCS_PREFIX", "")

# 任务状态存储
_inventory_tasks: Dict[str, TaskStatus] = {}
_inventory_task_bins: Dict[str, List[BinLocationStatus]] = {}
_inventory_task_details: Dict[str, Dict[str, Dict[str, Any]]] = {}

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
                "code": location,
            }
            target_route.append(route_item)

        # 构建请求体
        request_body = {
            "taskType": "PF-CTU-COMMON-TEST",
            "targetRoute": target_route
        }

        response = requests.post(url, json=request_body, headers=headers, timeout=30)

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("code") == "SUCCESS":
                logger.info(f"储位 {bin_locations} 已发送到机器人系统")
                return {"success": True, "message": "盘点任务已下发"}
        else:
            return {"success": False, "message": "盘点任务下发失败"}

    except Exception as e:
        logger.error(f"下发盘点任务失败: {str(e)}")
        raise


async def continue_inventory_task():
    """继续盘点任务"""
    try:
        logger.info(f"继续执行盘点任务")

        url = f"{RCS_BASE_URL}{RCS_PREFIX}/api/robot/controller/task/extend/continue"
        headers = {
            "X-lr-request-id": "ldui",
            "Content-Type": "application/json"
        }

        request_body = {
            "triggerType": "TASK",
            "triggerCode": "001"
        }

        response = requests.post(url, json=request_body, headers=headers, timeout=30)

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("code") == "SUCCESS":
                logger.info(f"继续执行盘点任务命令已发送到机器人系统")
                return {"success": True, "message": "盘点任务已继续"}
        else:
            return {"success": False, "message": "盘点任务下发失败"}

    except Exception as e:
        logger.error(f"继续盘点任务失败: {str(e)}")
        raise


# ==================== 机器人状态管理函数 ====================

async def update_robot_status(method: str, data: Optional[Dict] = None):
    """更新机器人状态并触发事件"""
    try:
        from services.api.state.robot_state import get_robot_state_manager
        manager = get_robot_state_manager()
        from services.api.config import ROBOT_STATUS_KEY

        manager._robot_status_store[ROBOT_STATUS_KEY] = {
            "method": method,
            "timestamp": time.time(),
            "data": data or {}
        }

        logger.info(f"更新机器人状态: {method}")
        manager._status_event.set()
    except ImportError:
        logger.warning("机器人状态管理器模块不存在，无法更新状态")


async def wait_for_robot_status(expected_method: str, timeout: int = 300):
    """等待特定机器人状态"""
    try:
        from services.api.state.robot_state import get_robot_state_manager
        from services.api.config import ROBOT_STATUS_KEY
        manager = get_robot_state_manager()

        logger.info(f"开始等待机器人状态: {expected_method}, 超时: {timeout}秒")
        start_time = time.time()

        manager._status_event.clear()

        # 检查是否已有期望状态
        if ROBOT_STATUS_KEY in manager._robot_status_store:
            current_status = manager._robot_status_store[ROBOT_STATUS_KEY]
            if current_status.get("method") == expected_method:
                logger.info(f"已存在期望状态: {expected_method}")
                return current_status

        while True:
            try:
                await asyncio.wait_for(manager._status_event.wait(), timeout=1.0)

                if ROBOT_STATUS_KEY in manager._robot_status_store:
                    current_status = manager._robot_status_store[ROBOT_STATUS_KEY]
                    logger.info(f"收到机器人状态: {current_status.get('method')}")

                    if current_status.get("method") == expected_method:
                        logger.info(f"收到期望状态: {expected_method}")
                        return current_status

                manager._status_event.clear()

            except asyncio.TimeoutError:
                elapsed_time = time.time() - start_time
                if elapsed_time >= timeout:
                    logger.error(f"等待机器人状态超时: {expected_method}")
                    raise asyncio.TimeoutError(f"等待 {expected_method} 状态超时")
                continue
    except ImportError:
        logger.error("机器人状态管理器模块不存在，无法等待状态")
        raise


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
            stderr=asyncio.subprocess.PIPE
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


async def capture_images_with_scripts(task_no: str, bin_location: str) -> Dict[str, Any]:
    """使用脚本抓取图片（带重试机制）"""
    from services.api.shared.config import CAPTURE_SCRIPTS

    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            logger.info(f"开始抓图: {task_no}/{bin_location}, 第 {retry_count + 1} 次尝试")

            # 执行所有抓图脚本
            for script_path in CAPTURE_SCRIPTS:
                if not os.path.exists(script_path):
                    logger.warning(f"抓图脚本不存在: {script_path}")
                    continue

                result = await execute_capture_script(script_path, task_no, bin_location)
                if not result["success"]:
                    raise Exception(f"抓图脚本执行失败: {result.get('error')}")

            # 等待图片生成
            await asyncio.sleep(2)

            # 检查图片是否存在
            image_dir = project_root / "capture_img" / task_no / bin_location / "3d_camera"
            if not image_dir.exists():
                raise Exception(f"图片目录不存在: {image_dir}")

            # 查找图片文件
            image_files = list(image_dir.glob("*.jpg")) + list(image_dir.glob("*.png"))
            if not image_files:
                raise Exception(f"未找到图片文件: {image_dir}")

            logger.info(f"抓图成功: {task_no}/{bin_location}")

            return {
                "success": True,
                "photo3dPath": f"/{task_no}/{bin_location}/3d_camera/main.jpg",
                "photoDepthPath": f"/{task_no}/{bin_location}/3d_camera/depth.jpg",
                "image_count": len(image_files)
            }

        except Exception as e:
            retry_count += 1
            logger.error(f"抓图失败 (尝试 {retry_count}/{max_retries}): {str(e)}")

            if retry_count < max_retries:
                await asyncio.sleep(5)  # 等待后重试
            else:
                return {"success": False, "error": str(e)}

    return {"success": False, "error": "超过最大重试次数"}


# ==================== 识别函数 ====================

async def run_barcode_and_detect(
    task_no: str,
    bin_location: str,
    image_dir: Path,
    pile_id: int = 1,
    code_type: str = "ucc128"
) -> Dict[str, Any]:
    """执行条码识别和数量检测"""
    result = {
        "barcode_result": None,
        "detect_result": None,
        "photos": []
    }

    # 条码识别
    if ENABLE_BARCODE and BARCODE_MODULE_AVAILABLE:
        try:
            from core.vision.barcode_recognizer import BarcodeRecognizer
            from services.api.shared.tobacco_resolver import get_tobacco_case_resolver

            recognizer = BarcodeRecognizer(code_type=code_type)
            barcode_results = recognizer.process_folder(input_dir=str(image_dir))
            resolver = get_tobacco_case_resolver()

            resolved_info = None
            for br in barcode_results:
                barcode_text = br.get('output') or br.get('text')
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

    # 数量检测
    if DETECT_MODULE_AVAILABLE:
        try:
            from core.detection import count_boxes

            image_files = []
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']

            for name in ['main', 'raw', 'image']:
                for ext in image_extensions:
                    common_file = image_dir / f"{name}{ext}"
                    if common_file.exists():
                        image_files.append(common_file)
                        break
                if image_files:
                    break

            if not image_files:
                for ext in image_extensions:
                    image_files.extend(list(image_dir.glob(f"*{ext}")))
                    if image_files:
                        break

            if image_files:
                depth_path = image_dir / "depth.jpg"
                total_count = count_boxes(
                    image_path=str(image_files[0]),
                    pile_id=pile_id,
                    depth_image_path=str(depth_path) if depth_path.exists() else None,
                    enable_debug=ENABLE_DEBUG,
                    enable_visualization=ENABLE_VISUALIZATION
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
            # 模拟模式
            logger.info(f"模拟模式：处理储位 {bin_location}")
            await asyncio.sleep(2)

            capture_img_dir = project_root / "capture_img" / task_no / bin_location

            if not capture_img_dir.exists():
                capture_img_dir.mkdir(parents=True, exist_ok=True)

                # 复制模拟图片
                public_dir = project_root / "web" / "src" / "public"
                image_mapping = [
                    ("1.jpg", "3d_camera", "main.jpg"),
                    ("2.jpg", "3d_camera", "depth.jpg"),
                    ("2.jpg", "3d_camera", "depth_color.jpg"),
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
            image_dir = capture_img_dir / "3d_camera"
            recognition_result = await run_barcode_and_detect(
                task_no=task_no,
                bin_location=bin_location,
                image_dir=image_dir,
                pile_id=1,
                code_type="ucc128"
            )

            detect_result = recognition_result.get("detect_result", {})
            barcode_result = recognition_result.get("barcode_result", {})

            # 获取数量
            if detect_result.get("status") == "success" and detect_result.get("total_count") is not None:
                result["actualQuantity"] = detect_result["total_count"]
            else:
                # 从库存数据获取备用数量
                inventory_item = None
                if task_no in _inventory_task_details and "inventoryItems" in _inventory_task_details[task_no]:
                    for item in _inventory_task_details[task_no]["inventoryItems"]:
                        if item.get("locationName") == bin_location:
                            inventory_item = item
                            break
                result["actualQuantity"] = inventory_item.get("systemQuantity", 0) if inventory_item else 0

            # 获取品规
            if barcode_result.get("status") == "success" and barcode_result.get("product_name"):
                result["actualSpec"] = barcode_result["product_name"]
            else:
                result["actualSpec"] = "未识别"

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

            if (index + 1) < total:
                logger.info(f"模拟模式：继续下一个储位")
                await asyncio.sleep(1)

        else:
            # 真实模式
            logger.info(f"============等待机器人就位信息: {bin_location}")
            try:
                ctu_status = await wait_for_robot_status("end", timeout=300)

                if ctu_status and ctu_status.get("method") == "end":
                    capture_results = await capture_images_with_scripts(task_no, bin_location)
                    result["captureResults"] = capture_results

                    if not capture_results.get("success"):
                        logger.error(f"抓图失败，跳过储位: {bin_location}")
                        result["status"] = "异常"
                        result["error"] = "抓图失败（重试3次后仍失败）"
                        result["endTime"] = datetime.now().isoformat()

                        if (index + 1) < total:
                            logger.info(f"跳过储位 {bin_location}，继续下一个储位")
                            continue_result = await continue_inventory_task()
                            logger.info(f"继续任务接口调用结果: {continue_result}")
                            result["continueResult"] = continue_result

                        return result

                    logger.info(f"抓图成功: {bin_location}")

                    result["photo3dPath"] = capture_results.get("photo3dPath")
                    result["photoDepthPath"] = capture_results.get("photoDepthPath")

                    capture_img_dir = project_root / "capture_img" / task_no / bin_location
                    image_dir = capture_img_dir / "3d_camera"

                    recognition_result = await run_barcode_and_detect(
                        task_no=task_no,
                        bin_location=bin_location,
                        image_dir=image_dir,
                        pile_id=1,
                        code_type="ucc128"
                    )

                    detect_result = recognition_result.get("detect_result", {})
                    barcode_result = recognition_result.get("barcode_result", {})

                    if detect_result.get("status") == "success" and detect_result.get("total_count") is not None:
                        result["actualQuantity"] = detect_result["total_count"]
                    else:
                        inventory_item = None
                        if task_no in _inventory_task_details and "inventoryItems" in _inventory_task_details[task_no]:
                            for item in _inventory_task_details[task_no]["inventoryItems"]:
                                if item.get("locationName") == bin_location:
                                    inventory_item = item
                                    break
                        result["actualQuantity"] = inventory_item.get("systemQuantity", 0) if inventory_item else 0

                    if barcode_result.get("status") == "success" and barcode_result.get("product_name"):
                        result["actualSpec"] = barcode_result["product_name"]
                    else:
                        result["actualSpec"] = "未识别"

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

                    if (index + 1) < total:
                        logger.info(f"收到机器人结束状态: {bin_location}")
                        continue_result = await continue_inventory_task()
                        logger.info(f"继续任务接口调用结果: {continue_result}")
                        result["continueResult"] = continue_result

                else:
                    logger.warning(f"未收到预期的结束状态，当前状态: {ctu_status}")

            except asyncio.TimeoutError as e:
                logger.error(f"等待机器人结束状态超时: {str(e)}")
                result["status"] = "异常"
                result["error"] = "等待机器人结束状态超时"
                result["endTime"] = datetime.now().isoformat()
                return result

    except Exception as e:
        result["status"] = "异常"
        result["error"] = str(e)
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

    # 整体下发盘点任务
    method = "start"
    await update_robot_status(method)

    submit_result = await submit_inventory_task(task_no, bin_locations)

    # 存储所有储位的盘点结果
    inventory_results = []

    try:
        logger.info(f"开始并行处理 {len(bin_locations)} 个储位")

        # 先将所有储位状态设为运行中
        if task_no in _inventory_task_bins:
            for bin_status in _inventory_task_bins[task_no]:
                bin_status.status = "running"

        # 并行执行所有 bin 的处理
        async def process_and_wrap(i: int, bin_location: str):
            result = await process_single_bin_location(
                task_no=task_no,
                bin_location=bin_location,
                index=i,
                total=len(bin_locations),
                is_sim=is_sim
            )
            return bin_location, result

        tasks = [
            process_and_wrap(i, bin_location)
            for i, bin_location in enumerate(bin_locations)
        ]
        bin_results = await asyncio.gather(*tasks)

        # 更新每个 bin 的状态并收集结果
        for bin_location, result in bin_results:
            if task_no in _inventory_task_bins:
                for bin_status in _inventory_task_bins[task_no]:
                    if bin_status.bin_location == bin_location:
                        bin_status.status = "completed" if result["status"] == "成功" else "failed"
                        break

            # 从原始盘点项中查找匹配的储位信息
            inventory_item = None
            if task_no in _inventory_task_details and "inventoryItems" in _inventory_task_details[task_no]:
                for item in _inventory_task_details[task_no]["inventoryItems"]:
                    if item.get("locationName") == bin_location:
                        inventory_item = item
                        break

            # 计算差异
            actual_qty = result.get("actualQuantity", 0)
            system_qty = inventory_item.get("systemQuantity", 0) if inventory_item else 0
            difference = actual_qty - system_qty

            # 收集盘点结果
            inventory_results.append({
                "binLocation": bin_location,
                "status": result["status"],
                "actualQuantity": result.get("actualQuantity"),
                "actualSpec": result.get("actualSpec"),
                "photo3dPath": result.get("photo3dPath"),
                "photoDepthPath": result.get("photoDepthPath"),
                "photoScan1Path": result.get("photoScan1Path", ""),
                "photoScan2Path": result.get("photoScan2Path", ""),
                "error": result.get("error"),
                "specName": inventory_item.get("productName", "") if inventory_item else "",
                "systemQuantity": system_qty,
                "difference": difference,
            })

        logger.info(f"所有 {len(bin_locations)} 个储位处理完成")

        # 更新任务状态为完成
        _inventory_tasks[task_no].status = "completed"
        _inventory_tasks[task_no].current_step = len(bin_locations)
        _inventory_tasks[task_no].end_time = datetime.now().isoformat()

        # 保存盘点结果到任务详情
        if task_no not in _inventory_task_details:
            _inventory_task_details[task_no] = {}

        _inventory_task_details[task_no]["inventoryResults"] = inventory_results

        logger.info(f"盘点任务完成: {task_no}, 成功处理 {len(bin_locations)} 个储位")
        logger.info(f"盘点结果: {inventory_results}")

        # 从任务详情中获取用户信息
        user_info = _inventory_task_details.get(task_no, {}).get("userInfo", {})

        # 记录任务完成
        log_operation(
            operation_type="inventory",
            action="盘点任务完成",
            user_id=user_info.get("userId"),
            user_name=user_info.get("userName"),
            target=task_no,
            status="completed",
            details={
                "task_no": task_no,
                "bin_locations": bin_locations,
                "completed_count": len(bin_locations),
            }
        )

    except Exception as e:
        if task_no in _inventory_tasks:
            _inventory_tasks[task_no].status = "failed"
            _inventory_tasks[task_no].end_time = datetime.now().isoformat()

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
