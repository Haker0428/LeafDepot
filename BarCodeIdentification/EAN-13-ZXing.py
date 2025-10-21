import os
import zxing
import cv2
import numpy as np
from datetime import datetime
from tqdm import tqdm  # 导入进度条库


def preprocess_barcode_image(image_path):
    """增强版图像预处理：自适应阈值 + 形态学操作"""
    # 读取灰度图像并检查有效性
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"无法读取图像: {image_path}")

    # # 高斯模糊降噪
    # img = cv2.GaussianBlur(img, (3, 3), 0)

    # # 自适应阈值处理（更适应不同光照条件）
    # img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    #                             cv2.THRESH_BINARY, 11, 2)

    # # 形态学闭操作（连接断裂条码线）
    # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3))
    # img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)

    return img


def batch_decode_barcodes(folder_path, output_txt_path, delete_temp=True):
    """
    批量处理文件夹中的条码图像
    Args:
        folder_path: 包含待处理图像的文件夹路径
        output_txt_path: 保存结果的txt文件路径
        delete_temp: 是否删除处理后的临时文件
    """
    results = []
    temp_dir = os.path.join(folder_path, "processed_images")
    os.makedirs(temp_dir, exist_ok=True)

    reader = zxing.BarCodeReader()  # 创建一次解码器实例

    # 获取所有图像文件
    image_files = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]

    # 使用 tqdm 显示进度条
    for filename in tqdm(image_files, desc="处理条码", unit="文件"):
        try:
            image_path = os.path.join(folder_path, filename)

            # 图像预处理
            processed_img = preprocess_barcode_image(image_path)

            # 保存处理后的图像作为临时文件
            temp_filename = f"processed_{filename}"
            temp_path = os.path.join(temp_dir, temp_filename)
            cv2.imwrite(temp_path, processed_img)

            # 解码条码
            barcode = reader.decode(temp_path)

            # 记录结果
            if barcode:
                results.append({
                    'filename': filename,
                    'success': True,
                    'format': barcode.format,
                    'data': barcode.raw
                })
            else:
                results.append({
                    'filename': filename,
                    'success': False,
                    'reason': '未识别到条码'
                })

            # # 删除临时文件（如果需要）
            # if delete_temp:
            #     os.remove(temp_path)

        except Exception as e:
            results.append({
                'filename': filename,
                'success': False,
                'reason': f'处理错误: {str(e)}'
            })

    # 保存结果到txt文件
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"条码识别结果 ({timestamp})\n")
        f.write("="*50 + "\n")

        for result in results:
            f.write(f"\n文件: {result['filename']}\n")
            if result['success']:
                f.write(f"类型: {result['format']}\n")
                f.write(f"数据: {result['data']}\n")
            else:
                f.write(f"状态: 失败 ({result['reason']})\n")
            f.write("-"*50 + "\n")

    print(f"处理完成！共处理 {len(results)} 张图片，结果已保存到 {output_txt_path}")


# 使用示例
if __name__ == "__main__":
    input_folder = "./raw_img/BarCodeCam/600mmDistancePics"  # 替换为您的图像文件夹路径
    output_file = "barcode_results.txt"

    batch_decode_barcodes(input_folder, output_file)
