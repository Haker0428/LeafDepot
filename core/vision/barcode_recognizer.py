import os
import subprocess
import json
import datetime
import errno
import cv2
from typing import List, Dict, Any
from pathlib import Path

from core.vision.yolo_detector import YoloDetection


class BarcodeRecognizer:
    def __init__(self,
                 barcode_reader_path: str = None,
                 code_type: str = 'ucc128',
                 barcode_model_path: str = None):
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
        
        # 检查可执行文件格式（如果是Linux二进制文件在macOS上运行会报错）
        import platform
        if platform.system() == 'Darwin':  # macOS
            # 检查文件类型，如果是Linux ELF文件，给出提示
            try:
                import subprocess
                result = subprocess.run(['file', self.barcode_reader_path], 
                                      capture_output=True, text=True, timeout=2)
                if 'ELF' in result.stdout and 'Linux' in result.stdout:
                    # 在macOS上尝试运行Linux二进制文件会失败
                    pass  # 这里不立即报错，让执行时捕获OSError
            except:
                pass  # file命令不可用，忽略检查
        
        self.code_type = code_type
        self.results = []  # 存储识别结果

        # 初始化 YOLO 条码检测器（使用 barcode.pt）
        self.yolo_detector = None
        if barcode_model_path is None:
            project_root = Path(__file__).parent.parent.parent
            barcode_model_path = project_root / "shared" / "models" / "yolo" / "barcode.pt"
        barcode_model_path = str(barcode_model_path)
        if os.path.exists(barcode_model_path):
            self.yolo_detector = YoloDetection(
                model_path=barcode_model_path,
                class_mapping={0: 'barcode', 1: 'QR'},
                confidence_threshold=0.5,
                padding=30
            )

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
            # YOLO 检测并裁剪条形码区域，返回裁剪后的图像路径列表
            cropped_paths = self.preprocess_image(image_path)
            for cropped_path in cropped_paths:
                self._process_image(cropped_path, filename)

        # 保存到JSON文件 (如果指定了输出路径)
        if output_json:
            self._save_to_json(output_json)

        return self.results

    # 排除中间生成文件（深度处理、检测处理产生）
    EXCLUDED_BASENAMES = {
        'depth_color', 'depth', 'raw', 'main_rotated',
        'main_yolo_detection', 'main_step1_scene_prepare',
        'main_step2_layers', 'main_step2_layers_roi',
        'main_step3_layers_boxes', 'main_step4_final_result',
        'depth_loaded_original', 'depth_rotated_for_debug',
        'disparity_visual_gray', 'disparity_visual_color',
    }

    def _is_image_file(self, filename: str) -> bool:
        """检查文件是否为图片格式，且非中间生成文件"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif'}
        ext = os.path.splitext(filename.lower())[1]
        if ext not in image_extensions:
            return False
        # 排除中间生成文件（不含扩展名的 basename）
        name_without_ext = os.path.splitext(filename)[0].lower()
        return name_without_ext not in self.EXCLUDED_BASENAMES

    def preprocess_image(self, image_path: str) -> List[str]:
        """
        使用 YOLO 模型检测图像中的条形码区域并裁剪

        :param image_path: 原始图像路径
        :return: 裁剪后的条形码图像路径列表（检测到多个时返回多个）
                 若未检测到则返回原始图像路径
        """
        if self.yolo_detector is None:
            return [image_path]

        original_image = cv2.imread(image_path)
        if original_image is None:
            return [image_path]

        # 执行 YOLO 预测
        results = self.yolo_detector.model.predict(
            source=original_image,
            conf=self.yolo_detector.confidence_threshold
        )

        cropped_paths = []
        crop_index = 0
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls)
                if cls not in self.yolo_detector.class_mapping:
                    continue
                category = self.yolo_detector.class_mapping[cls]
                if category not in ('barcode', 'QR'):
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                # 扩展边界
                x1_pad = max(0, x1 - self.yolo_detector.padding)
                y1_pad = max(0, y1 - self.yolo_detector.padding)
                x2_pad = min(original_image.shape[1], x2 + self.yolo_detector.padding)
                y2_pad = min(original_image.shape[0], y2 + self.yolo_detector.padding)

                # 裁剪条形码区域
                cropped = original_image[y1_pad:y2_pad, x1_pad:x2_pad]
                cropped_dir = os.path.dirname(image_path)
                name, ext = os.path.splitext(os.path.basename(image_path))
                crop_filename = f"{name}_barcode_crop_{crop_index}{ext}"
                crop_path = os.path.join(cropped_dir, crop_filename)
                cv2.imwrite(crop_path, cropped)
                cropped_paths.append(crop_path)
                crop_index += 1

        return cropped_paths if cropped_paths else [image_path]

    def _process_image(self, image_path: str, filename: str):
        """处理单张图片的条形码识别"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"[Barcode] 开始识别图片: {filename}, 路径: {image_path}")

        # 设置库路径环境变量
        bin_dir = Path(self.barcode_reader_path).parent
        lib_dir = bin_dir / "lib"
        env = os.environ.copy()
        if lib_dir.exists():
            existing_ld_path = env.get('LD_LIBRARY_PATH', '')
            env['LD_LIBRARY_PATH'] = f"{lib_dir}:{existing_ld_path}" if existing_ld_path else str(lib_dir)
            logger.debug(f"[Barcode] 设置 LD_LIBRARY_PATH: {env['LD_LIBRARY_PATH']}")

        args = [
            self.barcode_reader_path,
            f'-type={self.code_type}',
            image_path
        ]

        try:
            # 使用参考代码的方式调用
            cp = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            if cp.returncode == 0 and cp.stdout.strip():
                output = cp.stdout.strip()
                error = ""
                logger.info(f"[Barcode] 识别成功 - 图片: {filename}, 条码内容: {output}")
            else:
                output = ""
                error = cp.stderr.strip() if cp.stderr else f"返回码: {cp.returncode}"
                logger.warning(f"[Barcode] 未识别到条码 - 图片: {filename}, 错误: {error}")

        except subprocess.TimeoutExpired as e:
            output = ""
            error = f"识别超时: {e}"
            logger.error(f"[Barcode] 识别超时 - 图片: {filename}")
        except OSError as e:
            # 处理Exec format error等系统错误
            import platform
            error_msg = f"执行错误: {e}"
            if "Exec format error" in str(e) or (hasattr(e, 'errno') and e.errno == errno.EBADF):
                if platform.system() == 'Darwin':
                    error_msg = "可执行文件格式不兼容: BarcodeReaderCLI 是 Linux 二进制文件，当前系统是 macOS。\n" \
                               "解决方案：\n" \
                               "1. 使用 Docker 运行 Linux 环境\n" \
                               "2. 或获取 macOS 版本的 BarcodeReaderCLI\n" \
                               "3. 或在 Linux 服务器上运行此服务"
                else:
                    error_msg = f"可执行文件格式不兼容: {e}"
            output = ""
            error = error_msg
            logger.error(f"[Barcode] 执行错误 - 图片: {filename}, 错误: {error_msg}")
        except Exception as e:
            output = ""
            error = f"识别失败: {e}"
            logger.error(f"[Barcode] 识别失败 - 图片: {filename}, 错误: {e}")

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
