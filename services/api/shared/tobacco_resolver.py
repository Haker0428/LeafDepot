"""
烟箱信息解析器
"""
import re
from typing import Dict, Any, Optional

import pandas as pd

from services.api.shared.config import (
    logger,
    project_root,
    STACK_TYPE_TO_CODE,
    STACK_TYPE_CODE_TO_PILE_ID,
)


class TobaccoCaseInfoResolver:
    """
    烟草烟箱信息解析器

    功能：根据条码识别结果，查询烟箱信息并返回垛型编码和映射后的 pile_id
    """

    _instance = None
    _code_mapping = None

    def __new__(cls):
        """单例模式，避免重复加载Excel数据"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化：加载Excel数据"""
        if self._code_mapping is None:
            self._load_excel_data()

    def _load_excel_data(self):
        """加载烟箱信息Excel数据"""
        try:
            excel_path = project_root / "shared" / "data" / "烟箱信息汇总完整版.xlsx"

            if not excel_path.exists():
                logger.warning(f"烟箱信息Excel文件不存在: {excel_path}")
                self._code_mapping = {}
                return

            df = pd.read_excel(excel_path, dtype=str)
            self._code_mapping = {}

            for _, row in df.iterrows():
                # 获取6位数字代码
                code = str(row.get('提取的6位数字', '')).strip()
                if code and code not in ['nan', '']:
                    self._code_mapping[code] = {
                        'product_name': str(row.get('品名', '')),
                        'tobacco_code': str(row.get('烟草内部品规代号', '')),
                        'stack_type_1': str(row.get('垛型_1', '')),
                        'stack_type_2': str(row.get('垛型_2', '')),
                    }

            logger.info(f"成功加载 {len(self._code_mapping)} 条烟箱信息")

        except Exception as e:
            logger.error(f"加载烟箱信息Excel失败: {e}")
            self._code_mapping = {}

    def _extract_six_digits(self, barcode: str) -> Optional[str]:
        """从条码中提取6位数字（忽略91前缀）"""
        if not barcode:
            return None

        # 移除 (91) 或 91 前缀
        if barcode.startswith('(91)'):
            barcode = barcode[4:]
        elif barcode.startswith('91'):
            barcode = barcode[2:]

        # 提取前6位连续数字
        match = re.search(r'(\d{6})', barcode)
        return match.group(1) if match else None

    def _parse_stack_type(self, stack_type_str: str) -> int:
        """将垛型字符串转换为编码"""
        if not stack_type_str or str(stack_type_str).strip().lower() in ['nan', 'none', '']:
            return -1
        return STACK_TYPE_TO_CODE.get(str(stack_type_str).strip(), -1)

    def resolve(self, barcode: str) -> Dict[str, Any]:
        """
        根据条码解析烟箱信息

        Args:
            barcode: 识别到的条码字符串

        Returns:
            {
                'success': bool,
                'six_digit_code': str,
                'stack_type_1': int,  # 垛型编码
                'pile_id': int,       # 映射后的 pile_id
                'product_name': str,
                'tobacco_code': str,
            }
        """
        result = {
            'success': False,
            'six_digit_code': None,
            'stack_type_1': -1,
            'pile_id': None,
            'product_name': '',
            'tobacco_code': '',
        }

        if not barcode:
            return result

        # 提取6位数字
        six_digits = self._extract_six_digits(barcode)
        if not six_digits:
            logger.warning(f"无法从条码提取6位数字: {barcode}")
            return result

        result['six_digit_code'] = six_digits

        # 查找匹配的烟箱信息
        match_data = self._code_mapping.get(six_digits)
        if not match_data:
            # 尝试模糊匹配
            for code in self._code_mapping:
                if six_digits in code or code in six_digits:
                    match_data = self._code_mapping[code]
                    logger.info(f"使用模糊匹配: {six_digits} -> {code}")
                    break

        if not match_data:
            logger.warning(f"未找到匹配的烟箱信息: {six_digits}")
            return result

        # 解析垛型
        stack_type_code = self._parse_stack_type(match_data['stack_type_1'])

        # 映射 pile_id
        pile_id = STACK_TYPE_CODE_TO_PILE_ID.get(stack_type_code, 1)

        result.update({
            'success': True,
            'stack_type_1': stack_type_code,
            'pile_id': pile_id,
            'product_name': match_data['product_name'],
            'tobacco_code': match_data['tobacco_code'],
        })

        logger.info(f"烟箱信息解析成功: code={six_digits}, stack_type={stack_type_code}, pile_id={pile_id}")
        return result


def get_tobacco_case_resolver() -> TobaccoCaseInfoResolver:
    """获取烟箱信息解析器单例"""
    return TobaccoCaseInfoResolver()
