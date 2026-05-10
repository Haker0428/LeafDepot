"""
Detection runner: 封装拍照+识别逻辑，供 gateway 和 worker 共用。
worker 通过此模块执行 Phase 2 的重量级检测任务。
"""
import os
import sys
import asyncio
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

# project_root 需要在 import 前就设置
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent.parent  # services/api/shared/detection_runner.py → LeafDepot 根目录
sys.path.insert(0, str(_project_root))


async def capture_images(task_no: str, bin_location: str, is_sim: bool) -> Dict[str, Any]:
    """拍照入口（兼容 sim/real 模式）"""
    from services.api.shared.config import WITH_CAMERA

    if WITH_CAMERA:
        from services.api.inventory.service import capture_images_with_scripts
        return await capture_images_with_scripts(task_no, bin_location)

    # sim without camera: 复制模拟图片
    await asyncio.sleep(2)
    capture_dir = _project_root / "capture_img" / task_no / bin_location
    if not capture_dir.exists():
        capture_dir.mkdir(parents=True, exist_ok=True)
        public_dir = _project_root / "web" / "src" / "public"
        image_mapping = [
            ("1.jpg", "3d_camera", "main.jpg"),
            ("2.jpg", "3d_camera", "depth.jpg"),
            ("3.jpg", "scan_camera_1", "main.jpg"),
            ("4.jpg", "scan_camera_2", "main.jpg")
        ]
        for img_file, camera_dir, dest_filename in image_mapping:
            src = public_dir / img_file
            dest_dir = capture_dir / camera_dir
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / dest_filename
            if src.exists():
                shutil.copy(src, dest)
                logger.info(f"[DetectionRunner] sim copy: {src} -> {dest}")
            else:
                logger.warning(f"[DetectionRunner] sim image not found: {src}")
    return {"success": True}


def _get_actual_spec(barcode_result: dict) -> str:
    if barcode_result and barcode_result.get("status") == "success" and barcode_result.get("product_name"):
        return barcode_result["product_name"]
    return "未识别"


def _make_recognition_result(bin_location: str, capture_dir: Path, is_sim: bool) -> Dict[str, Any]:
    """在 sim 模式下，通过检测目录中的已有图片做识别"""
    from services.api.inventory.service import run_barcode_and_detect

    capture_dir = _project_root / "capture_img"
    return run_barcode_and_detect(
        task_no="",
        bin_location=bin_location,
        scan_dirs=[capture_dir / bin_location / "scan_camera_1", capture_dir / bin_location / "scan_camera_2"],
        detect_dir=capture_dir / bin_location / "3d_camera",
        pile_id=1,
        code_type="ucc128"
    )


async def run_detection(task_no: str, bin_location: str, is_sim: bool) -> Dict[str, Any]:
    """
    执行单个库位的检测：拍照 + 识别，返回原始结果 dict。
    供 worker 调用，结果写回 Redis 由 gateway 消费。
    """
    result = {
        "binLocation": bin_location,
        "status": None,
        "actualQuantity": None,
        "actualSpec": "无",
        "photo3dPath": None,
        "photoDepthPath": None,
        "photoScan1Path": "",
        "photoScan2Path": "",
        "error": None,
        "barcode_result": None,
        "detect_result": None,
    }

    capture_dir = _project_root / "capture_img" / task_no / bin_location

    # 1. 拍照
    logger.info(f"[DetectionRunner] 拍照: {task_no}/{bin_location}, is_sim={is_sim}")
    try:
        capture_results = await capture_images(task_no, bin_location, is_sim)
    except Exception as e:
        logger.error(f"[DetectionRunner] 拍照异常: {e}")
        result["status"] = "异常"
        result["error"] = f"拍照异常: {str(e)}"
        return result

    if not capture_results.get("success"):
        result["status"] = "异常"
        partial_errors = capture_results.get("errors", [])
        if partial_errors:
            result["error"] = "相机抓图失败：" + "；".join(partial_errors)
        else:
            result["error"] = "所有相机抓图失败"
        result["actualQuantity"] = 0
        return result

    # 设置图片路径
    result["photo3dPath"] = f"/{task_no}/{bin_location}/3d_camera/main.jpg"
    result["photoDepthPath"] = f"/{task_no}/{bin_location}/3d_camera/depth.jpg"
    result["photoScan1Path"] = f"/{task_no}/{bin_location}/scan_camera_1/main.jpg"
    result["photoScan2Path"] = f"/{task_no}/{bin_location}/scan_camera_2/main.jpg"

    # 2. 条码 + 数量识别
    logger.info(f"[DetectionRunner] 识别: {task_no}/{bin_location}, capture_dir={capture_dir}")
    try:
        recognition_result = await run_detection_async(
            task_no=task_no,
            bin_location=bin_location,
            capture_dir=capture_dir,
        )
    except Exception as e:
        logger.error(f"[DetectionRunner] 识别异常: {e}")
        result["status"] = "异常"
        result["error"] = f"识别异常: {str(e)}"
        return result

    detect_result = (recognition_result or {}).get("detect_result") or {}
    barcode_result = (recognition_result or {}).get("barcode_result") or {}

    result["barcode_result"] = barcode_result
    result["detect_result"] = detect_result

    if detect_result.get("status") == "success":
        result["photo3dPath"] = f"/{task_no}/{bin_location}/3d_camera/main_rotated.jpg"
        result["photoDepthPath"] = f"/{task_no}/{bin_location}/3d_camera/depth_color.jpg"
        result["actualSpec"] = _get_actual_spec(barcode_result)
        result["status"] = "成功"
        if result["actualSpec"] == "未识别":
            result["actualQuantity"] = 0
        else:
            result["actualQuantity"] = detect_result.get("total_count", 0)
        logger.info(f"[DetectionRunner] 识别成功: qty={result['actualQuantity']}, spec={result['actualSpec']}")
    else:
        result["status"] = "异常"
        result["error"] = f"检测失败: {detect_result.get('error', '未找到图片')}"
        result["actualSpec"] = _get_actual_spec(barcode_result)
        result["actualQuantity"] = 0

    return result


async def run_detection_async(task_no: str, bin_location: str, capture_dir: Path) -> Dict[str, Any]:
    """执行条码和数量识别（调用 service 中的同步函数）"""
    # run_barcode_and_detect is an async function in service.py
    from services.api.inventory.service import run_barcode_and_detect
    return await run_barcode_and_detect(
        task_no=task_no,
        bin_location=bin_location,
        scan_dirs=[capture_dir / "scan_camera_1", capture_dir / "scan_camera_2"],
        detect_dir=capture_dir / "3d_camera",
        pile_id=1,
        code_type="ucc128"
    )
