"""
盘点任务路由
"""
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, status, Body
from fastapi.responses import JSONResponse, Response
import pandas as pd

from services.api.shared.config import (
    logger,
    project_root,
    ENABLE_BARCODE,
    DETECT_MODULE_AVAILABLE,
    BARCODE_MODULE_AVAILABLE,
    IS_SIM,
    ENABLE_DEBUG,
    ENABLE_VISUALIZATION,
)
from services.api.shared.models import (
    TaskStatus,
    BinLocationStatus,
    InventoryTaskProgress,
    ScanAndRecognizeRequest,
)
from services.api.shared.operation_log import log_operation
from services.api.shared.tobacco_resolver import get_tobacco_case_resolver

# 从 service.py 导入核心函数和状态存储
from services.api.inventory.service import (
    execute_inventory_workflow,
    get_task_state_storage,
    inventory_tasks,
    inventory_task_bins,
    inventory_task_details,
)

from services.api.auth.router import get_user_info_from_token

# 条形码识别模块（条件导入）
if ENABLE_BARCODE and BARCODE_MODULE_AVAILABLE:
    from core.vision.barcode_recognizer import BarcodeRecognizer
else:
    BarcodeRecognizer = None

# 检测模块（条件导入）
if DETECT_MODULE_AVAILABLE:
    from core.detection import count_boxes
else:
    count_boxes = None

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


# ==================== 任务进度接口 ====================

@router.post("/start-inventory")
async def start_inventory(request: Request, background_tasks: BackgroundTasks):
    """启动盘点任务，接收任务编号和储位名称列表"""
    try:
        data = await request.json()
        task_no = data.get("taskNo")
        bin_locations = data.get("binLocations", [])
        is_sim = IS_SIM  # 使用配置文件中的值
        inventory_items = data.get("inventoryItems", [])

        if not task_no or not bin_locations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="任务编号和储位名称列表不能为空"
            )

        logger.info(f"启动盘点任务: {task_no}, 包含 {len(bin_locations)} 个储位, 模拟模式: {is_sim}")

        # 检查任务是否已存在
        if task_no in inventory_tasks:
            existing_task = inventory_tasks[task_no]
            if existing_task.status in ["running", "init"]:
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

        # 保存原始盘点项信息
        if task_no not in inventory_task_details:
            inventory_task_details[task_no] = {}
        inventory_task_details[task_no]["inventoryItems"] = inventory_items

        # 记录盘点任务启动
        auth_token = request.headers.get("authToken")
        logger.info(f"收到 authToken: {auth_token}")
        user_info = await get_user_info_from_token(auth_token) if auth_token else {}
        logger.info(f"获取到的 user_info: {user_info}")

        # 保存用户信息到任务详情，供后台任务使用
        inventory_task_details[task_no]["userInfo"] = user_info

        log_operation(
            operation_type="inventory",
            action="启动盘点任务",
            user_id=user_info.get("userId"),
            user_name=user_info.get("userName"),
            target=task_no,
            status="running",
            details={
                "task_no": task_no,
                "bin_locations": bin_locations,
                "bin_count": len(bin_locations),
                "is_sim": is_sim
            }
        )

        # 在后台异步执行盘点任务
        background_tasks.add_task(
            execute_inventory_workflow,
            task_no=task_no,
            bin_locations=bin_locations,
            is_sim=is_sim
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": 200,
                "message": "盘点任务已启动",
                "data": {
                    "taskNo": task_no,
                    "bin_locations": bin_locations,
                    "is_sim": is_sim
                }
            }
        )

    except Exception as e:
        logger.error(f"启动盘点任务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动盘点任务失败: {str(e)}"
        )


@router.get("/progress")
async def get_inventory_progress(taskNo: str):
    """获取盘点任务进度"""
    try:
        if taskNo not in inventory_tasks:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "code": 404,
                    "message": "任务不存在",
                    "data": None
                }
            )

        task_status = inventory_tasks[taskNo]
        bin_statuses = inventory_task_bins.get(taskNo, [])

        completed_count = sum(1 for bin in bin_statuses if bin.status == "completed")
        progress_percentage = (completed_count / task_status.total_steps * 100) if task_status.total_steps > 0 else 0

        progress_data = InventoryTaskProgress(
            task_no=task_status.task_no,
            status=task_status.status,
            current_step=task_status.current_step,
            total_steps=task_status.total_steps,
            progress_percentage=round(progress_percentage, 2),
            bin_locations=bin_statuses,
            start_time=task_status.start_time,
            end_time=task_status.end_time
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": 200,
                "message": "获取进度成功",
                "data": progress_data.dict()
            }
        )
    except Exception as e:
        logger.error(f"获取任务进度失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务进度失败: {str(e)}"
        )


@router.get("/results")
async def get_inventory_results(taskNo: str):
    """获取盘点任务的完整结果"""
    try:
        if taskNo not in inventory_tasks:
            return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "code": 404,
                        "message": "任务不存在",
                        "data": None
                    }
                )

        task_status = inventory_tasks[taskNo]

        if task_status.status != "completed":
            # 任务失败时，携带错误信息返回
            if task_status.status == "failed":
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "code": 200,
                        "message": task_status.error_message or "任务失败",
                        "errorType": task_status.error_type or "other",
                        "data": {
                            "taskNo": taskNo,
                            "status": task_status.status,
                            "currentStep": task_status.current_step,
                            "totalSteps": task_status.total_steps,
                            "inventoryResults": []
                        }
                    }
                )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "code": 200,
                    "message": "任务尚未完成",
                    "data": {
                        "taskNo": taskNo,
                        "status": task_status.status,
                        "currentStep": task_status.current_step,
                        "totalSteps": task_status.total_steps,
                        "inventoryResults": []
                    }
                }
            )

        inventory_results = []
        if taskNo in inventory_task_details and "inventoryResults" in inventory_task_details[taskNo]:
            inventory_results = inventory_task_details[taskNo]["inventoryResults"]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": 200,
                "message": "获取盘点结果成功",
                "data": {
                    "taskNo": taskNo,
                    "status": task_status.status,
                    "inventoryResults": inventory_results
                }
            }
        )
    except Exception as e:
        logger.error(f"获取盘点结果失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取盘点结果失败: {str(e)}"
        )


@router.get("/image")
async def get_inventory_image(
    taskNo: str,
    binLocation: str,
    cameraType: str,
    filename: str,
    source: str = "output"
):
    """获取盘点任务中的图片"""
    try:
        if source == "capture_img":
            image_path = project_root / "capture_img" / taskNo / binLocation / cameraType / filename
        else:
            image_path = project_root / "output" / taskNo / binLocation / cameraType / filename

        if not image_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"图片不存在: {filename} (路径: {image_path})"
            )

        with open(image_path, "rb") as f:
            image_data = f.read()

        media_type = "image/jpeg"
        if filename.endswith(".png"):
            media_type = "image/png"
        elif filename.endswith(".bmp"):
            media_type = "image/bmp"

        return Response(content=image_data, media_type=media_type)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图片失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取图片失败: {str(e)}"
        )


@router.get("/task-detail")
async def get_task_detail(taskNo: str, binLocation: str):
    """获取任务的详细信息"""
    try:
        storage = get_task_state_storage()
        task_details = storage["details"]

        if taskNo in task_details and binLocation in task_details[taskNo]:
            detail = task_details[taskNo][binLocation]
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "code": 200,
                    "message": "获取任务详情成功",
                    "data": detail
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "code": 404,
                    "message": "任务详情不存在",
                    "data": None
                }
            )

    except Exception as e:
        logger.error(f"获取任务详情失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务详情失败: {str(e)}"
        )


@router.post("/scan-and-recognize")
async def scan_and_recognize(request: ScanAndRecognizeRequest = Body(...)):
    """扫码+识别接口"""
    try:
        image_path = f"{request.taskNo}/{request.binLocation}/3d_camera/"
        image_dir = project_root / "capture_img" / image_path

        recognition_time = datetime.now().isoformat()
        results = {
            "taskNo": request.taskNo,
            "binLocation": request.binLocation,
            "recognition_time": recognition_time,
            "detect_result": None,
            "barcode_result": None,
            "photos": []
        }

        # 查找照片
        try:
            photos = []
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']

            if image_dir.exists():
                for ext in image_extensions:
                    for common_name in ['main', 'MAIN', 'raw', 'RAW', 'image', 'IMAGE']:
                        main_file = image_dir / f"{common_name}{ext}"
                        if main_file.exists():
                            relative_path = f"{request.taskNo}/{request.binLocation}/3d_camera/{common_name.upper()}{ext}"
                            photos.append(f"/{relative_path}")
                            break
                    if photos:
                        break

            results["photos"] = photos
        except Exception as e:
            logger.error(f"查找照片路径失败: {str(e)}")
            results["photos"] = []

        # Barcode 模块
        detected_pile_id = request.pile_id
        if ENABLE_BARCODE and BARCODE_MODULE_AVAILABLE and BarcodeRecognizer:
            try:
                recognizer = BarcodeRecognizer(code_type=request.code_type)
                barcode_results = recognizer.process_folder(input_dir=str(image_dir))
                resolver = get_tobacco_case_resolver()

                resolved_info = None
                for result in barcode_results:
                    barcode_text = result.get('output') or result.get('text')
                    if barcode_text:
                        resolved_info = resolver.resolve(barcode_text)
                        if resolved_info['success']:
                            break

                if resolved_info and resolved_info['success']:
                    detected_pile_id = resolved_info['pile_id']
                    results["barcode_result"] = {
                        "image_path": str(image_dir),
                        "code_type": request.code_type,
                        "six_digit_code": resolved_info['six_digit_code'],
                        "stack_type_1": resolved_info['stack_type_1'],
                        "product_name": resolved_info['product_name'],
                        "tobacco_code": resolved_info['tobacco_code'],
                        "mapped_pile_id": detected_pile_id,
                        "total_images": len(barcode_results),
                        "status": "success"
                    }
                else:
                    results["barcode_result"] = {
                        "image_path": str(image_dir),
                        "status": "no_match",
                        "message": "条码识别成功但未匹配到烟箱信息"
                    }
            except Exception as e:
                logger.error(f"Barcode模块识别失败: {str(e)}")
                results["barcode_result"] = {"status": "failed", "error": str(e)}
        else:
            results["barcode_result"] = {"status": "disabled"}

        # Detect 模块
        if DETECT_MODULE_AVAILABLE and count_boxes:
            try:
                if not image_dir.exists() or not image_dir.is_dir():
                    return JSONResponse(
                        status_code=status.HTTP_200_OK,
                        content={"code": 200, "message": "图片目录不存在", "data": results}
                    )

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
                    debug_output_dir = project_root / "debug" / request.taskNo / request.binLocation
                    debug_output_dir.mkdir(parents=True, exist_ok=True)

                    depth_path = image_dir / "depth.jpg"
                    total_count = count_boxes(
                        image_path=str(image_files[0]),
                        pile_id=detected_pile_id,
                        depth_image_path=str(depth_path) if depth_path.exists() else None,
                        enable_debug=ENABLE_DEBUG,
                        enable_visualization=ENABLE_VISUALIZATION,
                        output_dir=str(debug_output_dir)
                    )

                    results["detect_result"] = {
                        "image_path": str(image_files[0]),
                        "pile_id": detected_pile_id,
                        "total_count": total_count,
                        "status": "success"
                    }
            except Exception as e:
                logger.error(f"Detect模块识别失败: {str(e)}")
                results["detect_result"] = {"status": "failed", "error": str(e)}

        # 更新任务状态
        storage = get_task_state_storage()
        task_bins = storage["bins"]
        task_details = storage["details"]

        if request.taskNo in task_bins:
            for bin_status in task_bins[request.taskNo]:
                if bin_status.bin_location == request.binLocation:
                    bin_status.detect_result = results["detect_result"]
                    bin_status.barcode_result = results["barcode_result"]
                    bin_status.recognition_time = recognition_time
                    break

        if request.taskNo not in task_details:
            task_details[request.taskNo] = {}
        if request.binLocation not in task_details[request.taskNo]:
            task_details[request.taskNo][request.binLocation] = {}
        task_details[request.taskNo][request.binLocation]["recognition"] = results

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"code": 200, "message": "扫码+识别执行完成", "data": results}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"扫码+识别失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"扫码+识别失败: {str(e)}"
        )


@router.get("/recognition-result")
async def get_recognition_result(taskNo: str, binLocation: str):
    """读取识别结果接口"""
    try:
        storage = get_task_state_storage()
        task_bins = storage["bins"]
        task_details = storage["details"]

        result_data = {
            "taskNo": taskNo,
            "binLocation": binLocation,
            "detect_result": None,
            "barcode_result": None,
            "recognition_time": None
        }

        if taskNo in task_bins:
            for bin_status in task_bins[taskNo]:
                if bin_status.bin_location == binLocation:
                    result_data["detect_result"] = bin_status.detect_result
                    result_data["barcode_result"] = bin_status.barcode_result
                    result_data["recognition_time"] = bin_status.recognition_time
                    break

        if not result_data["detect_result"] and taskNo in task_details:
            if binLocation in task_details[taskNo]:
                recognition_data = task_details[taskNo][binLocation].get("recognition")
                if recognition_data:
                    result_data["detect_result"] = recognition_data.get("detect_result")
                    result_data["barcode_result"] = recognition_data.get("barcode_result")
                    result_data["recognition_time"] = recognition_data.get("recognition_time")

        if not result_data["detect_result"] and not result_data["barcode_result"]:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"code": 404, "message": "识别结果不存在", "data": None}
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"code": 200, "message": "获取识别结果成功", "data": result_data}
        )

    except Exception as e:
        logger.error(f"获取识别结果失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取识别结果失败: {str(e)}"
        )


@router.post("/save-results")
async def save_inventory_results(request: Request):
    """保存盘点结果并生成Excel文件"""
    try:
        data = await request.json()
        task_no = data.get("taskNo")
        inventory_results = data.get("inventoryResults", [])

        if not task_no:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务编号不能为空")

        if not inventory_results:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="盘点结果不能为空")

        logger.info(f"保存盘点结果: {task_no}, 共 {len(inventory_results)} 个储位")

        excel_data = []
        for i, result in enumerate(inventory_results, 1):
            spec_name = result.get("specName", "") or result.get("actualSpec", "")
            excel_data.append({
                "任务编号": task_no,
                "序号": i,
                "品规名称": spec_name,
                "储位名称": result.get("binLocation", ""),
                "实际品规": result.get("actualSpec", ""),
                "库存数量": result.get("systemQuantity", 0),
                "实际数量": result.get("actualQuantity", 1),
                "差异": result.get("difference", 1),
                "照片1路径": result.get("photo3dPath", ""),
                "照片2路径": result.get("photoDepthPath", ""),
                "照片3路径": result.get("photoScan1Path", ""),
                "照片4路径": result.get("photoScan2Path", ""),
            })

        df = pd.DataFrame(excel_data)
        output_dir = project_root / "output" / "history_data"
        output_dir.mkdir(parents=True, exist_ok=True)
        xlsx_file = output_dir / f"{task_no}.xlsx"

        with pd.ExcelWriter(xlsx_file, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='盘点结果')
            workbook = writer.book
            worksheet = writer.sheets['盘点结果']
            for idx, col in enumerate(df.columns, 1):
                max_length = max(df[col].astype(str).apply(len).max(), len(col))
                worksheet.column_dimensions[chr(64 + idx)].width = min(max_length + 2, 50)

        logger.info(f"成功生成Excel文件: {xlsx_file}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": 200,
                "message": "保存成功",
                "data": {
                    "taskNo": task_no,
                    "xlsxFile": str(xlsx_file),
                    "xlsxUrl": f"/api/inventory/download-xlsx?taskNo={task_no}",
                    "count": len(inventory_results)
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存盘点结果失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存盘点结果失败: {str(e)}"
        )


@router.get("/download-xlsx")
async def download_xlsx(taskNo: str):
    """下载Excel文件"""
    try:
        output_dir = project_root / "output" / "history_data"
        xlsx_file = output_dir / f"{taskNo}.xlsx"

        if not xlsx_file.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Excel文件不存在: {taskNo}.xlsx")

        with open(xlsx_file, "rb") as f:
            excel_data = f.read()

        return Response(
            content=excel_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={taskNo}.xlsx"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载Excel文件失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"下载Excel文件失败: {str(e)}")


@router.post("/update-bins-data")
async def update_bins_data(request: Request):
    """更新 bins_data.xlsx 中的数量和品规"""
    try:
        data = await request.json()
        inventory_items = data.get("inventoryItems", [])

        if not inventory_items:
            return {"code": 400, "message": "没有盘点数据"}

        bins_data_path = project_root / "services" / "sim" / "lms" / "bins_data.xlsx"

        if not bins_data_path.exists():
            return {"code": 500, "message": "bins_data.xlsx 文件不存在"}

        from openpyxl import load_workbook
        wb = load_workbook(bins_data_path)
        ws = wb.active

        location_to_data = {}
        for item in inventory_items:
            location_name = item.get("locationName") or item.get("binDesc")
            actual_quantity = item.get("actualQuantity")
            actual_spec = item.get("actualSpec")
            if location_name and actual_quantity is not None:
                location_to_data[location_name] = {"quantity": actual_quantity, "spec": actual_spec}

        updated_count = 0
        for row in range(2, ws.max_row + 1):
            location_name = ws.cell(row, 5).value
            if location_name in location_to_data:
                item_data = location_to_data[location_name]
                ws.cell(row, 8).value = item_data["quantity"]
                if item_data["spec"]:
                    ws.cell(row, 10).value = item_data["spec"]
                updated_count += 1

        wb.save(bins_data_path)
        wb.close()

        return {"code": 200, "message": f"成功更新 {updated_count} 个储位", "data": {"updatedCount": updated_count}}

    except Exception as e:
        logger.error(f"更新 bins_data.xlsx 失败: {str(e)}")
        return {"code": 500, "message": f"更新失败: {str(e)}"}


@router.get("/get-local-bins")
async def get_local_bins():
    """从本地 bins_data.xlsx 读取储位数据（用于模拟模式）"""
    try:
        bins_data_path = project_root / "services" / "sim" / "lms" / "bins_data.xlsx"

        if not bins_data_path.exists():
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"code": 404, "message": "bins_data.xlsx 文件不存在", "data": []}
            )

        from openpyxl import load_workbook
        wb = load_workbook(bins_data_path, read_only=True)
        ws = wb.active

        # 读取表头
        headers = [cell.value for cell in ws[1]]

        bins_list = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(row):  # 跳过空行
                continue

            row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}

            # 构建与 LMS 接口兼容的数据格式
            bin_item = {
                "whCode": row_dict.get("仓库编码", ""),
                "areaCode": row_dict.get("区域编码", ""),
                "areaName": row_dict.get("区域名称", ""),
                "binCode": row_dict.get("储位编码", ""),
                "binDesc": row_dict.get("储位名称", ""),
                "maxQty": row_dict.get("最大数量", 0),
                "binStatus": row_dict.get("储位状态", ""),
                "tobaccoQty": row_dict.get("数量(万支)", 0) or 0,
                "tobaccoCode": row_dict.get("烟草编码", ""),
                "tobaccoName": row_dict.get("品规名称", ""),
                "rcsCode": row_dict.get("RCS编码", ""),
            }
            bins_list.append(bin_item)

        wb.close()

        logger.info(f"从本地文件读取 {len(bins_list)} 条储位数据")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"code": 200, "message": "获取本地储位数据成功", "data": bins_list}
        )

    except Exception as e:
        logger.error(f"读取本地储位数据失败: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"code": 500, "message": f"读取失败: {str(e)}", "data": []}
        )
