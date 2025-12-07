import os
import subprocess
import json
import datetime
from typing import List, Dict, Any
from pathlib import Path


class BarcodeRecognizer:
    def __init__(self,
                 barcode_reader_path: str = None,
                 code_type: str = 'ucc128'):
        """
        初始化条形码识别器

        :param barcode_reader_path: 条形码识别程序路径，如果为None则使用默认路径
        :param code_type: 条形码类型 (e.g., 'ucc128', 'code128', 'ean13')
        """
        if barcode_reader_path is None:
            # 默认路径：从项目根目录查找
            project_root = Path(__file__).parent.parent.parent
            default_path = project_root / "shared" / "tools" / "BarcodeReaderCLI" / "bin" / "BarcodeReaderCLI"
            self.barcode_reader_path = str(default_path) if default_path.exists() else None
        else:
            self.barcode_reader_path = barcode_reader_path
        
        if not self.barcode_reader_path or not os.path.exists(self.barcode_reader_path):
            raise FileNotFoundError(
                f"条形码识别工具未找到: {self.barcode_reader_path}\n"
                f"请确保 BarcodeReaderCLI 已安装到 shared/tools/BarcodeReaderCLI/"
            )
        
        self.code_type = code_type
        self.results = []  # 存储识别结果

    def process_folder(self, input_dir: str, output_json: str = None) -> List[Dict[str, Any]]:
        """
        处理指定文件夹中的所有图片

        :param input_dir: 输入图片文件夹路径
        :param output_json: 输出JSON文件路径 (可选)
        :return: 识别结果列表 [ { "filename": str, "output": str, "error": str }, ... ]
        """
        # 验证输入目录是否存在
        if not os.path.isdir(input_dir):
            raise FileNotFoundError(f"输入目录不存在: {input_dir}")

        # 收集结果
        self.results = []

        # 遍历文件夹中的图片
        for filename in os.listdir(input_dir):
            if not self._is_image_file(filename):
                continue

            image_path = os.path.join(input_dir, filename)
            # 调用预处理函数（预留，当前返回原始路径）
            processed_path = self.preprocess_image(image_path)
            self._process_image(processed_path, filename)

        # 保存到JSON文件 (如果指定了输出路径)
        if output_json:
            self._save_to_json(output_json)

        return self.results

    def _is_image_file(self, filename: str) -> bool:
        """检查文件是否为图片格式"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif'}
        return os.path.splitext(filename.lower())[1] in image_extensions

    def preprocess_image(self, image_path: str) -> str:
        """
        预留图像预处理函数（未来可扩展）

        当前实现：不进行任何处理，返回原始图像路径
        未来可添加图像增强、裁剪、对比度调整等操作

        :param image_path: 原始图像路径
        :return: 处理后的图像路径（当前为原始路径）
        """
        # === 预留位置 ===
        # 未来可在此实现图像预处理逻辑
        # 例如：
        #   return self._enhance_image(image_path)
        # 但当前保持原样
        return image_path

    def _process_image(self, image_path: str, filename: str):
        """处理单张图片的条形码识别"""
        args = [
            self.barcode_reader_path,
            f'-type={self.code_type}',
            image_path
        ]

        try:
            cp = subprocess.run(
                args,
                universal_newlines=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            output = cp.stdout.strip()
            error = cp.stderr.strip()
        except subprocess.CalledProcessError as e:
            output = ""
            error = f"识别失败: {e}"

        self.results.append({
            "filename": filename,
            "output": output,
            "error": error
        })

        # 打印实时进度 (可选)
        print(
            f"Processed: {filename} | Result: {output[:20]}{'...' if len(output) > 20 else ''}")

    def _save_to_json(self, output_json: str):
        """保存结果到JSON文件"""
        os.makedirs(os.path.dirname(output_json), exist_ok=True)
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"✅ 识别结果已保存至: {output_json}")

    def get_results(self) -> List[Dict[str, Any]]:
        """获取当前识别结果"""
        return self.results


# 使用示例
if __name__ == "__main__":
    # 初始化识别器 (根据实际路径调整)
    recognizer = BarcodeRecognizer(
        barcode_reader_path='../utils/BarcodeReaderCLI/bin/BarcodeReaderCLI',
        code_type='ucc128'
    )

    # 处理输入文件夹并保存结果
    results = recognizer.process_folder(
        input_dir='../images',
        output_json='output/barcode_results_20231015.json'
    )

    # 打印统计信息
    print(f"\n总处理图片数: {len(results)}")
    print(f"成功识别: {sum(1 for r in results if r['output'])}")

    # 可选：直接使用结果列表
    for result in results:
        print(f"{result['filename']}: {result['output']}")
