"""
共享的 Excel 写入工具
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Set


def build_excel_data(
    task_no: str,
    inventory_results: List[Dict[str, Any]],
    operator_name: str = "",
    manual_calibrated: Set[str] | None = None,
    calibration_records: Dict[str, Dict[str, Any]] | None = None,
    is_valid: bool = True,
) -> pd.DataFrame:
    """
    从盘点结果构建 DataFrame（用于写入 Excel）。
    is_valid: True=有效（用户确认保存），False=无效（自动保存但无人确认）
    """
    if manual_calibrated is None:
        manual_calibrated = set()
    if calibration_records is None:
        calibration_records = {}

    dispatch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    valid_status = "有效" if is_valid else "无效"
    excel_data = []

    for i, result in enumerate(inventory_results, 1):
        bin_loc = result.get("binLocation", "")
        is_manually_calibrated = (
            bin_loc in manual_calibrated or
            bool(calibration_records.get(bin_loc, {}).get("specModified")) or
            bool(calibration_records.get(bin_loc, {}).get("quantityModified"))
        )
        mod_record = "人工修改" if is_manually_calibrated else ""

        spec_name = result.get("specName", "")
        actual_spec = result.get("actualSpec", "")
        quantity_diff = result.get("difference", 0)

        if actual_spec and actual_spec != spec_name and actual_spec != "未识别":
            diff_desc = "品规不一致"
        elif actual_spec == "未识别":
            diff_desc = "品规不一致"
        elif quantity_diff != 0:
            diff_desc = quantity_diff
        else:
            diff_desc = "一致"

        excel_data.append({
            "任务编号": task_no,
            "序号": i,
            "下发时间": dispatch_time,
            "操作员": operator_name,
            "品规名称": result.get("specName", ""),
            "储位名称": bin_loc,
            "实际品规": result.get("actualSpec", ""),
            "库存数量": result.get("systemQuantity", 0),
            "实际数量": result.get("actualQuantity", 1),
            "差异": diff_desc,
            "修改记录": mod_record,
            "有效状态": valid_status,
            "照片1路径": result.get("photo3dPath", ""),
            "照片2路径": result.get("photoDepthPath", ""),
            "照片3路径": result.get("photoScan1Path", ""),
            "照片4路径": result.get("photoScan2Path", ""),
        })

    return pd.DataFrame(excel_data)


def get_column_letter(idx: int) -> str:
    """将 1-based 列索引转换为 Excel 列字母（如 1->A, 27->AA）"""
    result = ""
    while idx > 0:
        idx -= 1
        result = chr(65 + (idx % 26)) + result
        idx //= 26
    return result


def write_excel(
    task_no: str,
    df: pd.DataFrame,
    output_dir: Path | None = None,
) -> Path:
    """
    将 DataFrame 写入 Excel 文件。
    """
    from services.api.shared.config import project_root, logger

    if output_dir is None:
        output_dir = project_root / "output" / "history_data"

    output_dir.mkdir(parents=True, exist_ok=True)
    xlsx_file = output_dir / f"{task_no}.xlsx"

    with pd.ExcelWriter(xlsx_file, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='盘点结果')
        workbook = writer.book
        worksheet = writer.sheets['盘点结果']
        for idx, col in enumerate(df.columns, 1):
            max_length = max(df[col].astype(str).apply(len).max(), len(col))
            col_letter = get_column_letter(idx)
            worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)

    logger.info(f"成功生成Excel文件: {xlsx_file}")
    return xlsx_file
