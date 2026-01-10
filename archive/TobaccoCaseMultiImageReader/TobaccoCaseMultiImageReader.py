import subprocess
import pandas as pd
import re
import json
from typing import Optional, List, Dict, Any, Tuple
import os


class TobaccoCaseMultiImageReader:
    def __init__(self, excel_path: str, barcode_reader_path: str = "BarcodeReaderCLI"):
        """
        初始化烟草烟箱信息读取器（支持多图处理）

        Args:
            excel_path: Excel文件路径
            barcode_reader_path: 条码读取器可执行文件路径（Linux）
        """
        self.excel_path = excel_path
        self.barcode_reader_path = barcode_reader_path
        self.data = None
        self.code_mapping = None

        # 垛型映射字典
        self.stack_type_mapping = {
            "5*8": 0,
            "5*6": 1,
            "5*5": 2,
            "3*10": 3,
            "4*7+2": 4,
            "特殊垛型": 5
        }

        # 加载Excel数据
        self._load_excel_data()

    def _load_excel_data(self):
        """加载Excel数据并创建映射"""
        try:
            # 读取Excel文件
            df = pd.read_excel(self.excel_path, dtype=str)

            # 创建代码到行数据的映射
            self.code_mapping = {}

            for idx, row in df.iterrows():
                # 获取提取的6位数字
                code = str(row.get('提取的6位数字', '')).strip()

                if code and code != 'nan' and code != '':  # 确保code不为空
                    # 存储相关数据
                    self.code_mapping[code] = {
                        '品名': str(row.get('品名', '')),
                        '烟草内部品规代号': str(row.get('烟草内部品规代号', '')),
                        '烟箱尺寸': str(row.get('烟箱尺寸（mm）', '')),
                        '垛型_1': str(row.get('垛型_1', '')),
                        '垛型_2': str(row.get('垛型_2', ''))
                    }

            # 保存原始数据供调试用
            self.data = df
            print(f"成功加载 {len(self.code_mapping)} 条烟箱信息")

        except Exception as e:
            print(f"加载Excel文件失败: {e}")
            raise

    def _parse_dimensions(self, dimension_str: str) -> Tuple[int, int, int]:
        """
        解析烟箱尺寸字符串

        Args:
            dimension_str: 尺寸字符串，如 "520*281*288"

        Returns:
            包含三个整数的元组
        """
        try:
            # 清理字符串并分割
            cleaned_str = str(dimension_str).replace(
                'mm', '').replace('(', '').replace(')', '').strip()
            parts = re.split(r'[×*xX]', cleaned_str)

            if len(parts) >= 3:
                return int(float(parts[0])), int(float(parts[1])), int(float(parts[2]))
            elif len(parts) == 1:
                # 尝试其他分隔符
                if '×' in cleaned_str:
                    parts = cleaned_str.split('×')
                elif 'x' in cleaned_str:
                    parts = cleaned_str.split('x')

                if len(parts) >= 3:
                    return int(float(parts[0])), int(float(parts[1])), int(float(parts[2]))
            return 0, 0, 0
        except Exception as e:
            print(f"解析尺寸字符串 '{dimension_str}' 时出错: {e}")
            return 0, 0, 0

    def _parse_stack_type(self, stack_type_str: str) -> int:
        """
        解析垛型字符串为对应的整数编码

        Args:
            stack_type_str: 垛型字符串

        Returns:
            对应的整数编码，未定义则返回-1
        """
        if not stack_type_str or str(stack_type_str).strip().lower() in ['nan', 'none', '']:
            return -1

        # 清理字符串
        stack_type = str(stack_type_str).strip()

        # 查找映射
        return self.stack_type_mapping.get(stack_type, -1)

    def _extract_six_digits(self, barcode_data: str) -> Optional[str]:
        """
        从识别码中提取6位数字（忽略前两位"91"）

        Args:
            barcode_data: 条码识别结果（字符串）

        Returns:
            提取的6位数字字符串，失败则返回None
        """
        if not barcode_data:
            print("条码数据为空")
            return None

        print(f"原始条码数据: {barcode_data}")

        # 移除可能的(91)前缀
        if barcode_data.startswith('(91)'):
            barcode_data = barcode_data[4:]
            print(f"移除(91)前缀后: {barcode_data}")
        # 或者直接以91开头
        elif barcode_data.startswith('91'):
            barcode_data = barcode_data[2:]
            print(f"移除91前缀后: {barcode_data}")

        # 查找前6位连续数字
        match = re.search(r'(\d{6})', barcode_data)
        if match:
            six_digits = match.group(1)
            print(f"提取的6位数字: {six_digits}")
            return six_digits

        print(f"在字符串中未找到6位连续数字")
        return None

    def _parse_barcode_result(self, result_text: str) -> Optional[str]:
        """
        解析BarcodeReaderCLI的输出，提取条码文本

        Args:
            result_text: BarcodeReaderCLI的输出文本

        Returns:
            提取的条码文本，失败则返回None
        """
        if not result_text:
            return None

        print(f"原始输出文本: {result_text}")

        # 尝试解析JSON
        try:
            result_json = json.loads(result_text)
            print(f"成功解析JSON结果")

            # 根据提供的JSON结构提取条码文本
            # sessions[0].barcodes[0].text
            if ('sessions' in result_json and
                len(result_json['sessions']) > 0 and
                'barcodes' in result_json['sessions'][0] and
                len(result_json['sessions'][0]['barcodes']) > 0 and
                    'text' in result_json['sessions'][0]['barcodes'][0]):

                barcode_text = result_json['sessions'][0]['barcodes'][0]['text']
                print(f"从JSON中提取条码文本: {barcode_text}")
                return barcode_text
            else:
                print("JSON结构不符合预期")
                return None

        except json.JSONDecodeError:
            # 如果不是JSON，则假设是纯文本条码
            print("输出不是JSON格式，按纯文本处理")
            # 去除首尾空白字符
            barcode_text = result_text.strip()
            if barcode_text:
                print(f"纯文本条码: {barcode_text}")
                return barcode_text

        return None

    def read_barcode_from_image(self, image_path: str, code_type: str = 'ucc128') -> Tuple[Optional[str], str]:
        """
        使用BarcodeReaderCLI从图片读取条码（Linux版本）

        Args:
            image_path: 图片文件路径
            code_type: 条码类型参数

        Returns:
            (识别到的条码字符串, 原始输出信息)，失败则返回(None, 错误信息)
        """
        if not os.path.exists(image_path):
            error_msg = f"图片文件不存在: {image_path}"
            print(error_msg)
            return None, error_msg

        try:
            # 构建命令行参数（参考main.py）
            args = [
                self.barcode_reader_path,
                f'-type={code_type}',
                image_path
            ]

            print(f"执行命令: {' '.join(args)}")

            # 调用外部条码读取器
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0 and result.stdout.strip():
                # 解析输出结果
                barcode = self._parse_barcode_result(result.stdout.strip())
                if barcode:
                    print(f"成功识别条码: {barcode}")
                    return barcode, result.stdout
                else:
                    error_msg = "无法从输出中提取条码文本"
                    print(error_msg)
                    return None, error_msg
            else:
                error_msg = f"条码识别失败: {result.stderr if result.stderr else '无输出'}"
                print(error_msg)
                # 尝试其他条码类型
                if code_type != 'code128':
                    print(f"尝试使用code128类型重新识别...")
                    return self.read_barcode_from_image(image_path, 'code128')
                return None, error_msg

        except FileNotFoundError:
            error_msg = f"找不到条码读取器: {self.barcode_reader_path}"
            print(error_msg)
            return None, error_msg
        except subprocess.TimeoutExpired:
            error_msg = "条码识别超时"
            print(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"条码识别过程中发生错误: {e}"
            print(error_msg)
            return None, error_msg

    def process_single_image(self, image_path: str, code_type: str = 'ucc128') -> Optional[Dict[str, Any]]:
        """
        处理单张图片并返回匹配的烟箱信息

        Args:
            image_path: 图片文件路径
            code_type: 条码类型参数

        Returns:
            包含匹配信息的字典，格式为:
            {
                '品名': str,
                '烟草内部品规代号': str,
                '尺寸_长': int,
                '尺寸_宽': int,
                '尺寸_高': int,
                '垛型_1': int,  # 编码后的整数
                '垛型_2': int,  # 编码后的整数
                '源图像': str,   # 源图片路径
                '识别码': str     # 识别的原始条码
            }
            如果未找到匹配则返回None
        """
        print(f"\n处理图片: {image_path}")

        # 1. 从图片读取条码
        barcode, raw_output = self.read_barcode_from_image(
            image_path, code_type)
        if not barcode:
            print(f"图片 {image_path} 中未识别到条码")
            return None

        # 2. 提取6位数字（忽略前两位"91"）
        six_digits = self._extract_six_digits(barcode)
        if not six_digits:
            print(f"无法从条码 '{barcode}' 中提取6位数字")
            return None

        # print(f"提取的6位数字: {six_digits}")

        # 3. 在Excel数据中查找
        if six_digits not in self.code_mapping:
            print(f"未找到匹配的烟箱信息，代码: {six_digits}")
            # 尝试查找相似代码（容错处理）
            similar_codes = [code for code in self.code_mapping.keys(
            ) if six_digits in code or code in six_digits]
            if similar_codes:
                print(f"找到相似代码: {similar_codes}")
                # 使用第一个相似代码
                six_digits = similar_codes[0]
                print(f"使用相似代码: {six_digits}")
            else:
                return None

        # 4. 获取匹配的数据
        match_data = self.code_mapping[six_digits]

        # 5. 解析数据
        try:
            # 解析尺寸
            dim_str = match_data['烟箱尺寸']
            length, width, height = self._parse_dimensions(dim_str)

            # 解析垛型
            stack_type_1 = self._parse_stack_type(match_data['垛型_1'])
            stack_type_2 = self._parse_stack_type(match_data['垛型_2'])

            # 返回结果
            result = {
                '品名': match_data['品名'],
                '烟草内部品规代号': match_data['烟草内部品规代号'],
                '尺寸_长': length,
                '尺寸_宽': width,
                '尺寸_高': height,
                '垛型_1': stack_type_1,
                '垛型_2': stack_type_2,
                '源图像': image_path,
                '识别码': barcode,
                '提取的6位数字': six_digits
            }

            print(f"成功匹配烟箱信息: {result['品名']}")
            return result

        except Exception as e:
            print(f"解析数据时发生错误: {e}")
            return None

    def process_multiple_images(self, image_paths: List[str], code_type: str = 'ucc128') -> Optional[Dict[str, Any]]:
        """
        处理多张图片，综合识别结果

        Args:
            image_paths: 图片文件路径列表
            code_type: 条码类型参数

        Returns:
            包含匹配信息的字典（以识别到的有效结果为准），
            如果所有图片都未识别到有效结果则返回None
        """
        print(f"\n开始处理 {len(image_paths)} 张图片...")

        results = []
        successful_images = []
        failed_images = []

        # 处理每张图片
        for i, image_path in enumerate(image_paths):
            print(f"\n处理第 {i+1}/{len(image_paths)} 张图片...")

            result = self.process_single_image(image_path, code_type)
            if result:
                results.append(result)
                successful_images.append(image_path)
                print(f"图片 {image_path} 识别成功")
            else:
                failed_images.append(image_path)
                print(f"图片 {image_path} 识别失败")

        # 输出统计信息
        print(f"\n识别统计:")
        print(f"成功识别: {len(successful_images)} 张图片")
        print(f"识别失败: {len(failed_images)} 张图片")

        if failed_images:
            print(f"失败的图片: {failed_images}")

        # 选择最佳结果
        if results:
            print(f"\n从 {len(results)} 个成功识别结果中选择最佳结果...")

            # 策略1: 优先选择有垛型信息的结果
            best_result = None
            for result in results:
                if result['垛型_1'] != -1 or result['垛型_2'] != -1:
                    best_result = result
                    break

            # 策略2: 如果没有垛型信息，选择第一个结果
            if not best_result and results:
                best_result = results[0]

            if best_result:
                print(f"选择最佳结果来自图片: {best_result['源图像']}")
                return best_result

        print("\n所有图片均未识别到有效烟箱信息")
        return None

    def get_stack_type_mapping(self) -> Dict[str, int]:
        """
        获取垛型映射字典

        Returns:
            垛型字符串到整数编码的映射字典
        """
        return self.stack_type_mapping.copy()


# 使用示例
if __name__ == "__main__":
    # 1. 实例化类
    reader = TobaccoCaseMultiImageReader(
        excel_path="/home/ubuntu/Projects/LeafDepot/archive/TobaccoCaseMultiImageReader/烟箱信息汇总完整版.xlsx",
        barcode_reader_path="/home/ubuntu/Projects/LeafDepot/shared/tools/BarcodeReaderCLI/bin/BarcodeReaderCLI"  # Linux可执行文件路径
    )

    # 示例1: 处理单张图片
    print("=" * 50)
    print("示例1: 处理单张图片")
    print("=" * 50)
    single_image_path = "data/picture/4.jpeg"  # 替换为你的图片路径
    result1 = reader.process_single_image(
        single_image_path, code_type='ucc128')

    if result1:
        print("\n匹配到的烟箱信息:")
        print(f"品名: {result1['品名']}")
        print(f"烟草内部品规代号: {result1['烟草内部品规代号']}")
        print(
            f"烟箱尺寸: {result1['尺寸_长']} * {result1['尺寸_宽']} * {result1['尺寸_高']} mm")
        print(f"垛型_1 (编码): {result1['垛型_1']}")
        print(f"垛型_2 (编码): {result1['垛型_2']}")
        print(f"源图像: {result1['源图像']}")
        print(f"识别码: {result1['识别码']}")

        # 反向查找垛型编码对应的原始字符串
        reverse_mapping = {v: k for k, v in reader.stack_type_mapping.items()}
        if result1['垛型_1'] in reverse_mapping:
            print(f"垛型_1 (原始): {reverse_mapping[result1['垛型_1']]}")
        if result1['垛型_2'] in reverse_mapping and result1['垛型_2'] != -1:
            print(f"垛型_2 (原始): {reverse_mapping[result1['垛型_2']]}")
    else:
        print("未能识别或匹配到烟箱信息")

    # 示例2: 处理多张图片
    print("\n" + "=" * 50)
    print("示例2: 处理多张图片")
    print("=" * 50)
    multiple_image_paths = [
        "data/picture/5-1.jpeg",
        "data/picture/5-2.jpeg",  # 假设有另一张图片
        # 可以添加更多图片路径
    ]

    # 确保图片文件存在
    existing_image_paths = [
        path for path in multiple_image_paths if os.path.exists(path)]
    if existing_image_paths:
        result2 = reader.process_multiple_images(
            existing_image_paths, code_type='ucc128')

        if result2:
            print("\n综合匹配到的烟箱信息:")
            print(f"品名: {result2['品名']}")
            print(f"烟草内部品规代号: {result2['烟草内部品规代号']}")
            print(
                f"烟箱尺寸: {result2['尺寸_长']} * {result2['尺寸_宽']} * {result2['尺寸_高']} mm")
            print(f"垛型_1 (编码): {result2['垛型_1']}")
            print(f"垛型_2 (编码): {result2['垛型_2']}")
            print(f"源图像: {result2['源图像']}")
            print(f"识别码: {result2['识别码']}")

            # 反向查找垛型编码对应的原始字符串
            reverse_mapping = {v: k for k,
                               v in reader.stack_type_mapping.items()}
            if result2['垛型_1'] in reverse_mapping:
                print(f"垛型_1 (原始): {reverse_mapping[result2['垛型_1']]}")
            if result2['垛型_2'] in reverse_mapping and result2['垛型_2'] != -1:
                print(f"垛型_2 (原始): {reverse_mapping[result2['垛型_2']]}")
        else:
            print("所有图片均未识别到有效烟箱信息")
    else:
        print("指定的图片文件均不存在")

    # 示例3: 查看垛型映射
    print("\n" + "=" * 50)
    print("示例3: 垛型映射关系")
    print("=" * 50)
    mapping = reader.get_stack_type_mapping()
    print("垛型编码映射:")
    for stack_type, code in mapping.items():
        print(f"  {stack_type} -> {code}")
