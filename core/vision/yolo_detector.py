import os
import cv2
from ultralytics import YOLO
from typing import List, Dict, Any, Tuple
import json
import datetime  # 添加时间模块


class YoloDetection:
    def __init__(self,
                 model_path: str,
                 class_mapping: Dict[int, str] = None,
                 confidence_threshold: float = 0.7,
                 padding: int = 50):
        """
        初始化条形码检测器

        :param model_path: YOLO模型权重文件路径
        :param class_mapping: 类别ID到名称的映射 (e.g., {0: 'barcode', 1: 'QR', 2: 'piles', 3: 'box'})
        :param confidence_threshold: 置信度阈值
        :param padding: 裁剪边界扩展像素
        """
        self.model = YOLO(model_path)
        self.class_mapping = class_mapping or {
            0: 'barcode', 1: 'QR', 2: 'piles', 3: 'box'}
        self.confidence_threshold = confidence_threshold
        self.padding = padding

        # 用于存储每个类别的检测结果
        self.category_results = {category: []
                                 for category in self.class_mapping.values()}

    def _create_category_dirs(self, output_dir: str):
        """为每个类别创建子目录（在指定输出目录下）"""
        for category in self.class_mapping.values():
            os.makedirs(os.path.join(output_dir, category), exist_ok=True)

    def process_folder(self, input_dir: str, output_dir: str, timestamp) -> Dict[str, List[Dict[str, Any]],]:
        """
        处理输入文件夹中的所有图片，并按类别保存结果

        :param input_dir: 输入图片文件夹路径
        :param output_dir: 基础输出目录（将自动添加时间戳子目录）
        :return: 每个类别的检测结果 {category: [result, ...]}
        """
        # 验证输入目录是否存在
        if not os.path.isdir(input_dir):
            raise FileNotFoundError(f"输入目录不存在: {input_dir}")

        # 生成时间戳目录名 (格式: YYYYMMDD_HHMMSS)
        # timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        actual_output_dir = os.path.join(output_dir, timestamp)
        os.makedirs(actual_output_dir, exist_ok=True)
        print(f"✅ 创建时间戳输出目录: {actual_output_dir}")

        # 创建输出目录结构（使用实际输出目录）
        self._create_category_dirs(actual_output_dir)

        # 创建用于保存带检测框的图片的目录
        detected_images_dir = os.path.join(
            actual_output_dir, 'detected_images')
        os.makedirs(detected_images_dir, exist_ok=True)

        # 遍历文件夹中的图片
        for filename in os.listdir(input_dir):
            if not self._is_image_file(filename):
                continue

            image_path = os.path.join(input_dir, filename)
            self._process_image(image_path, filename,
                                actual_output_dir, detected_images_dir)

        # 保存每个类别的结果到JSON文件
        self._save_category_results(actual_output_dir)

        return self.category_results

    def _is_image_file(self, filename: str) -> bool:
        """检查文件是否为图片格式"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif'}
        return os.path.splitext(filename.lower())[1] in image_extensions

    def _process_image(self, image_path: str, filename: str, output_dir: str, detected_images_dir: str):
        """处理单张图片的检测和裁剪（无预处理）"""
        original_image = cv2.imread(image_path)
        if original_image is None:
            print(f"⚠️ 跳过无法读取的图像: {filename}")
            return

        # 执行YOLO预测
        results = self.model.predict(
            source=original_image,
            conf=self.confidence_threshold
        )

        # 保存带检测框的原始图片
        if results:
            plot_image = results[0].plot()  # 获取带框的图像 (RGB)
            # 转换为BGR格式以便OpenCV保存
            plot_image_bgr = cv2.cvtColor(plot_image, cv2.COLOR_RGB2BGR)
            detected_image_path = os.path.join(detected_images_dir, filename)
            cv2.imwrite(detected_image_path, plot_image_bgr)
            print(f"✅ 保存带检测框的图像: {detected_image_path}")
        else:
            # 如果没有检测结果，保存原始图片
            detected_image_path = os.path.join(detected_images_dir, filename)
            cv2.imwrite(detected_image_path, original_image)
            print(f"✅ 保存原始图像（无检测框）: {detected_image_path}")

        # 遍历所有检测结果
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls)
                conf = box.conf.item()

                # 检查类别是否在映射中
                if cls not in self.class_mapping:
                    continue

                # 检查置信度
                if conf < self.confidence_threshold:
                    continue

                category = self.class_mapping[cls]
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

                # 扩展边界
                x1_pad = max(0, x1 - self.padding)
                y1_pad = max(0, y1 - self.padding)
                x2_pad = min(original_image.shape[1], x2 + self.padding)
                y2_pad = min(original_image.shape[0], y2 + self.padding)

                # 裁剪图像（无预处理）
                cropped_img = original_image[y1_pad:y2_pad, x1_pad:x2_pad]

                # 保存裁剪图像 (带类别前缀)
                save_filename = f"{category}_{os.path.splitext(filename)[0]}_{len(self.category_results[category])}.png"
                save_path = os.path.join(output_dir, category, save_filename)
                cv2.imwrite(save_path, cropped_img)

                # 记录检测结果
                self.category_results[category].append({
                    "original_image": filename,
                    "cropped_image": save_filename,
                    "bbox": [x1, y1, x2, y2],
                    "confidence": conf,
                    "category": category
                })

                print(f"✅ 保存裁剪图像: {save_path}")

    def _save_category_results(self, output_dir: str):
        """将每个类别的结果保存为JSON文件"""
        for category, results in self.category_results.items():
            if not results:
                continue

            json_path = os.path.join(output_dir, f"{category}_results.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"✅ 保存类别结果: {json_path}")

    def get_results(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有检测结果"""
        return self.category_results


# 使用示例
if __name__ == "__main__":
    # 初始化检测器（包含padding参数）
    detector = YoloDetection(
        model_path='../../shared/models/yolo/best.pt',
        class_mapping={
            0: 'barcode',
            1: 'box',
            2: 'piles',
            3: 'QR'
        },
        confidence_threshold=0.7,
        padding=50
    )

    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # 处理输入文件夹（output_dir将自动添加时间戳子目录）
    results = detector.process_folder(
        input_dir='../images',  # 包含多张图片的文件夹
        output_dir='../output',   # 基础输出目录（会自动添加时间戳子目录
        timestamp=current_time)

    # 打印统计信息
    print("\n检测结果统计:")
    for category, items in results.items():
        print(f"  {category}: {len(items)} 个检测结果")

    # 打印示例结果
    print("\n示例结果:")
    for category, items in results.items():
        if items:
            print(f"  {category}: {items[0]}")
