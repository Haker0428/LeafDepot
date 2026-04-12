"""
历史记录路由
"""
import re
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse, Response

from services.api.shared.config import logger, project_root
from services.api.shared.operation_log import log_operation

router = APIRouter(prefix="/api/history", tags=["history"])

# 历史数据输出根目录
OUTPUT_ROOT = project_root / "output"


def parse_task_date_from_filename(task_id: str) -> Optional[datetime]:
    """从任务ID解析日期"""
    patterns = [
        (r'(\d{4})(\d{2})(\d{2})', '%Y%m%d'),
        (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),
        (r'(\d{2})(\d{2})(\d{4})', '%d%m%Y'),
    ]

    for pattern, date_format in patterns:
        match = re.search(pattern, task_id)
        if match:
            try:
                date_str = ''.join(match.groups())
                return datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                continue
    return None


def is_task_expired(task_date: datetime) -> bool:
    """检查任务是否过期（超过6个月）"""
    if not task_date:
        return False
    now = datetime.now()
    six_months_ago = now - timedelta(days=180)
    return task_date < six_months_ago


@router.get("/available-dates")
async def get_available_dates():
    """获取所有有盘点数据的日期列表"""
    try:
        history_tasks_dir = OUTPUT_ROOT / "history_data"
        history_tasks_dir.mkdir(parents=True, exist_ok=True)

        xlsx_files = list(history_tasks_dir.glob("*.xlsx"))
        dates: Set[str] = set()

        for xlsx_file in xlsx_files:
            try:
                task_id = xlsx_file.stem
                task_date = parse_task_date_from_filename(task_id)
                if task_date:
                    dates.add(task_date.strftime("%Y-%m-%d"))
            except Exception:
                continue

        # 按日期降序排列
        sorted_dates = sorted(dates, reverse=True)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"code": 200, "message": "获取可用日期成功", "data": {"dates": sorted_dates}}
        )

    except Exception as e:
        logger.error(f"获取可用日期失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取可用日期失败: {str(e)}")


@router.get("/tasks")
async def get_history_tasks(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """获取历史任务列表"""
    try:
        history_tasks_dir = OUTPUT_ROOT / "history_data"
        history_tasks_dir.mkdir(parents=True, exist_ok=True)

        xlsx_files = list(history_tasks_dir.glob("*.xlsx"))
        tasks = []

        for xlsx_file in xlsx_files:
            try:
                task_id = xlsx_file.stem
                dispatch_time = None

                # 尝试从 Excel 文件读取下发时间（优先使用实际保存时间）
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(str(xlsx_file), data_only=True)
                    ws = wb.active
                    headers = [str(cell.value) for cell in ws[1] if cell.value]
                    if "下发时间" in headers:
                        dispatch_col_idx = headers.index("下发时间") + 1
                        dispatch_val = ws.cell(row=2, column=dispatch_col_idx).value
                        if dispatch_val:
                            # 支持 datetime 对象或字符串
                            if isinstance(dispatch_val, datetime):
                                dispatch_time = dispatch_val
                            else:
                                dispatch_time = datetime.strptime(str(dispatch_val), "%Y-%m-%d %H:%M:%S")
                    wb.close()
                except Exception as ex:
                    logger.warning(f"读取Excel下发时间失败 {xlsx_file.name}: {ex}")

                # 如果 Excel 中没有下发时间，则从任务编号解析
                if dispatch_time is None:
                    dispatch_time = parse_task_date_from_filename(task_id)

                is_expired = is_task_expired(dispatch_time) if dispatch_time else False

                # 从 Excel 读取操作员、修改记录和有效状态（用于任务列表显示）
                task_operator = ""
                task_has_modified = False
                task_is_valid = True  # 默认为有效（兼容没有有效状态列的旧文件）
                try:
                    import openpyxl
                    wb2 = openpyxl.load_workbook(str(xlsx_file), data_only=True)
                    ws2 = wb2.active
                    headers2 = [str(cell.value) for cell in ws2[1] if cell.value]
                    # 操作员在第一行数据中
                    if "操作员" in headers2 and ws2.max_row >= 2:
                        op_val = ws2.cell(row=2, column=headers2.index("操作员") + 1).value
                        if op_val:
                            task_operator = str(op_val)
                    # 修改记录：检查所有数据行，任一有非空值则标记为已修改
                    if "修改记录" in headers2 and ws2.max_row >= 2:
                        mod_col_idx = headers2.index("修改记录") + 1
                        for row_idx in range(2, ws2.max_row + 1):
                            mod_val = ws2.cell(row=row_idx, column=mod_col_idx).value
                            mod_str = str(mod_val or "")
                            if mod_str and mod_str != "None":
                                task_has_modified = True
                                break
                    # 有效状态：读取第一行数据的有效状态列（有效/无效）
                    if "有效状态" in headers2 and ws2.max_row >= 2:
                        valid_val = ws2.cell(row=2, column=headers2.index("有效状态") + 1).value
                        valid_str = str(valid_val or "").strip()
                        task_is_valid = (valid_str == "有效")
                    wb2.close()
                except Exception as ex:
                    logger.warning(f"读取Excel元信息失败 {xlsx_file.name}: {ex}")

                tasks.append({
                    "taskId": task_id,
                    "taskDate": dispatch_time.isoformat() if dispatch_time else None,
                    "fileName": xlsx_file.name,
                    "isExpired": is_expired,
                    "filePath": str(xlsx_file.relative_to(OUTPUT_ROOT)),
                    "operator": task_operator,
                    "hasModified": task_has_modified,
                    "isValid": task_is_valid,
                })
            except Exception as e:
                logger.error(f"解析历史任务文件失败 {xlsx_file.name}: {str(e)}")
                continue

        # 按下发时间范围过滤
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                tasks = [t for t in tasks if t.get("taskDate") and datetime.fromisoformat(t["taskDate"]) >= start_dt]
            except ValueError:
                pass  # 日期格式错误时忽略过滤

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                # 包含结束日期当天
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                tasks = [t for t in tasks if t.get("taskDate") and datetime.fromisoformat(t["taskDate"]) <= end_dt]
            except ValueError:
                pass

        tasks.sort(key=lambda x: x.get("taskDate") or "", reverse=True)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"code": 200, "message": "获取历史任务成功", "data": {"tasks": tasks, "total": len(tasks)}}
        )

    except Exception as e:
        logger.error(f"获取历史任务列表失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取历史任务列表失败: {str(e)}")


@router.get("/task/{task_id}")
async def get_history_task_details(task_id: str):
    """获取历史任务详情"""
    try:
        history_tasks_dir = OUTPUT_ROOT / "history_data"
        xlsx_file = history_tasks_dir / f"{task_id}.xlsx"

        if not xlsx_file.exists():
            possible_files = list(history_tasks_dir.glob(f"{task_id}.*"))
            if possible_files:
                xlsx_file = possible_files[0]
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"历史任务文件不存在: {task_id}.xlsx")

        logger.info(f"读取Excel文件: {xlsx_file}")

        import openpyxl
        workbook = openpyxl.load_workbook(str(xlsx_file), data_only=True)
        worksheet = workbook[workbook.sheetnames[0]]

        headers = [str(cell.value) for cell in worksheet[1] if cell.value]
        logger.info(f"Excel表头: {headers}")

        details = []
        has_modified = False
        modified_bins: List[str] = []
        operator = ""
        for row_index, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), 1):
            if all(cell is None for cell in row):
                continue

            row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
            # 操作员只取第一条记录的值（enumerate 从 1 开始计数，第一条数据行 row_index=1）
            if row_index == 1 and row_dict.get("操作员"):
                operator = str(row_dict.get("操作员", ""))
            mod_record = str(row_dict.get("修改记录", "") or "")
            # 排除空字符串和字符串 "None"（旧版 Excel 遗留值）
            if mod_record and mod_record != "None":
                has_modified = True
                bin_name = str(row_dict.get("储位名称", ""))
                if bin_name not in modified_bins:
                    modified_bins.append(bin_name)
            detail = {
                "序号": row_dict.get("序号") or row_index,
                "品规名称": str(row_dict.get("品规名称", "")),
                "储位名称": str(row_dict.get("储位名称", "")),
                "实际品规": str(row_dict.get("实际品规", row_dict.get("品规名称", ""))),
                "库存数量": int(row_dict.get("库存数量", 0) or 0),
                "实际数量": int(row_dict.get("实际数量", 0) or 0),
                "差异": str(row_dict.get("差异", "一致")),
                "修改记录": mod_record,
                "照片1路径": str(row_dict.get("照片1路径") or ""),
                "照片2路径": str(row_dict.get("照片2路径") or ""),
                "照片3路径": str(row_dict.get("照片3路径") or ""),
                "照片4路径": str(row_dict.get("照片4路径") or ""),
            }
            details.append(detail)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"code": 200, "message": "获取历史任务详情成功",
                     "data": {"taskId": task_id, "details": details, "total": len(details),
                              "operator": operator, "hasModified": has_modified, "modifiedBins": modified_bins}}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取历史任务详情失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取历史任务详情失败: {str(e)}")


@router.delete("/task/{task_id}")
async def delete_history_task(task_id: str, request: Request):
    """按任务ID删除历史盘点文件"""
    try:
        user_level = request.headers.get("X-User-Level")
        if user_level != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足，仅管理员可删除历史数据")

        if not re.match(r'^[A-Za-z0-9_-]+$', task_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务ID包含非法字符")

        history_tasks_dir = OUTPUT_ROOT / "history_data"
        xlsx_file = history_tasks_dir / f"{task_id}.xlsx"

        if not xlsx_file.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"任务 {task_id} 的历史文件不存在")

        xlsx_file.unlink()
        logger.info(f"已删除历史任务文件: {xlsx_file.name}")

        client_host = request.client.host if request.client else "unknown"
        log_operation(
            operation_type="system_cleanup",
            action="删除历史任务",
            user_name="前端传递",
            target=task_id,
            status="success",
            ip_address=client_host,
            details={"task_id": task_id, "filename": xlsx_file.name}
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"code": 200, "message": f"任务 {task_id} 已成功删除", "data": {"task_id": task_id}}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除历史任务失败 {task_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除历史任务失败: {str(e)}")


@router.get("/task/{task_id}/bin/{bin_location}")
async def get_history_task_bin_detail(task_id: str, bin_location: str):
    """获取历史任务中某个储位的详细信息"""
    try:
        history_tasks_dir = OUTPUT_ROOT / "history_data"
        xlsx_file = history_tasks_dir / f"{task_id}.xlsx"

        if not xlsx_file.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"历史任务文件不存在: {task_id}.xlsx")

        import openpyxl
        workbook = openpyxl.load_workbook(str(xlsx_file), data_only=True)
        worksheet = workbook[workbook.sheetnames[0]]

        headers = [str(cell.value) for cell in worksheet[1] if cell.value]

        for row in worksheet.iter_rows(min_row=2, values_only=True):
            row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
            if row_dict.get("储位名称") == bin_location:
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"code": 200, "message": "获取储位详情成功", "data": row_dict}
                )

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"储位 {bin_location} 不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取储位详情失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取储位详情失败: {str(e)}")


@router.get("/image")
async def get_history_image(taskNo: str, binLocation: str, cameraType: str, filename: str, source: str = "output"):
    """获取历史图片"""
    try:
        # 根据 source 参数确定根目录
        if source == "capture_img":
            base_dir = project_root / "capture_img"
        else:
            base_dir = OUTPUT_ROOT

        image_dir = base_dir / taskNo / binLocation / cameraType

        # 尝试查找匹配的图片文件（支持带扩展名和不带扩展名的 filename）
        image_path = None
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.JPG', '.JPEG', '.PNG', '.BMP']

        # 先尝试直接使用 filename 作为完整路径
        direct_path = image_dir / filename
        if direct_path.exists():
            image_path = direct_path
        else:
            # 尝试添加扩展名
            for ext in image_extensions:
                test_path = image_dir / f"{filename}{ext}"
                if test_path.exists():
                    image_path = test_path
                    break

        if not image_path or not image_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"图片不存在: {filename}")

        with open(image_path, "rb") as f:
            image_data = f.read()

        media_type = "image/jpeg"
        filename_lower = image_path.name.lower()
        if filename_lower.endswith(".png"):
            media_type = "image/png"
        elif filename_lower.endswith(".bmp"):
            media_type = "image/bmp"

        return Response(content=image_data, media_type=media_type)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图片失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取图片失败: {str(e)}")


@router.post("/cleanup")
async def cleanup_history(request: Request):
    """清理过期的历史数据"""
    try:
        user_level = request.headers.get("X-User-Level")
        if user_level != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

        data = await request.json()
        days = data.get("days", 180)

        history_tasks_dir = OUTPUT_ROOT / "history_data"
        deleted_count = 0

        for xlsx_file in history_tasks_dir.glob("*.xlsx"):
            task_id = xlsx_file.stem
            task_date = parse_task_date_from_filename(task_id)
            if task_date and is_task_expired(task_date):
                xlsx_file.unlink()
                deleted_count += 1
                logger.info(f"已清理过期文件: {xlsx_file.name}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"code": 200, "message": f"已清理 {deleted_count} 个过期文件", "data": {"deletedCount": deleted_count}}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理历史数据失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"清理历史数据失败: {str(e)}")


@router.get("/monthly-count")
async def get_monthly_count():
    """获取本月盘点次数和准确率"""
    try:
        import openpyxl

        # 历史数据目录
        history_tasks_dir = OUTPUT_ROOT / "history_data"

        if not history_tasks_dir.exists():
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "code": 200,
                    "message": "历史数据目录不存在",
                    "data": {
                        "count": 0,
                        "current_month": datetime.now().strftime("%Y-%m"),
                        "accuracy": None,
                        "files": []
                    }
                }
            )

        # 获取当前年月
        current_year = datetime.now().year
        current_month = datetime.now().month
        current_month_str = f"{current_year}-{current_month:02d}"

        # 查找所有历史数据文件
        all_files = list(history_tasks_dir.glob("*.xlsx"))
        all_files.extend(history_tasks_dir.glob("*.xls"))

        monthly_files = []

        for file_path in all_files:
            try:
                # 从文件名解析日期
                filename = file_path.stem
                if len(filename) >= 10 and filename[:2] == "HS":
                    date_str = filename[2:10]
                    try:
                        file_date = datetime.strptime(date_str, "%Y%m%d")
                        file_year = file_date.year
                        file_month = file_date.month

                        if file_year == current_year and file_month == current_month:
                            monthly_files.append({
                                "filename": file_path.name,
                                "filepath": str(file_path),
                                "date": file_date.strftime("%Y-%m-%d"),
                                "task_no": filename
                            })
                    except ValueError:
                        continue
            except Exception as e:
                logger.error(f"处理文件失败 {file_path.name}: {str(e)}")
                continue

        count = len(monthly_files)

        # 计算准确率
        accuracy = None
        if count > 0:
            total_count = 0
            match_count = 0

            for file_info in monthly_files:
                try:
                    wb = openpyxl.load_workbook(file_info["filepath"], read_only=True)
                    ws = wb.active

                    for row_idx in range(2, ws.max_row + 1):
                        cell_h = ws.cell(row=row_idx, column=8)  # 第H列（差异）
                        if cell_h.value is not None:
                            total_count += 1
                            if str(cell_h.value).strip() == "一致":
                                match_count += 1

                    wb.close()
                except Exception as e:
                    logger.error(f"读取Excel失败 {file_info['filename']}: {str(e)}")
                    continue

            if total_count > 0:
                accuracy = round((match_count / total_count) * 100, 1)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "code": 200,
                "message": "获取月度统计成功",
                "data": {
                    "count": count,
                    "current_month": current_month_str,
                    "accuracy": accuracy,
                    "files": [f["filename"] for f in monthly_files]
                }
            }
        )

    except Exception as e:
        logger.error(f"获取月度统计失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取月度统计失败: {str(e)}")
