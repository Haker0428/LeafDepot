import datetime
import cv2
import subprocess
import os
import json
from ultralytics import YOLO

# === 配置参数 ===
MODEL_PATH = 'yolo_model_weight/best.pt'              # YOLOv8 权重文件路径
IMAGE_PATH = 'data/img0004.png'             # 输入图像路径
BARCODE_CLASS_ID = 0                # 条形码类别ID
BARCODE_READER_PATH = 'BarcodeReaderCLI/bin/BarcodeReaderCLI'  # 条形码识别程序路径
CONFIDENCE_THRESHOLD = 0.5          # 置信度阈值
CODE_TYPE = 'ucc128'

# 生成带时间戳的输出目录
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = os.path.join('output', f"run_{timestamp}")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 加载模型
model = YOLO(MODEL_PATH)

# 执行预测
results = model.predict(source=IMAGE_PATH, conf=CONFIDENCE_THRESHOLD)

# 读取原始图像
original_image = cv2.imread(IMAGE_PATH)

# 初始化计数器和文件名列表
save_count = 0
image_files = []

# 遍历所有检测结果
for result in results:
    boxes = result.boxes
    for box in boxes:
        cls = int(box.cls)
        if cls == BARCODE_CLASS_ID:
            conf = box.conf.item()
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            if conf > 0.5:
                # 裁剪图像并增强清晰度
                cropped_img = original_image[y1:y2, x1:x2]

                # 扩展边界（防止裁剪过紧）
                padding = 10  # 可调整扩展像素
                x1 = max(0, x1 - padding)
                y1 = max(0, y1 - padding)
                x2 = min(original_image.shape[1], x2 + padding)
                y2 = min(original_image.shape[0], y2 + padding)
                cropped_img = original_image[y1:y2, x1:x2]

                # 图像增强：调整对比度和亮度
                alpha = 1.0  # 对比度增强系数（1.0-3.0）
                beta = 0     # 亮度调整（0-100）
                enhanced_img = cv2.convertScaleAbs(
                    cropped_img, alpha=alpha, beta=beta)

                # 超分辨率放大（可选）
                scale_factor = 2  # 放大倍数
                resized_img = cv2.resize(
                    enhanced_img, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)

                # 保存为无损格式
                filename = f"barcode_{save_count}.png"
                save_path = os.path.join(OUTPUT_DIR, filename)
                cv2.imwrite(save_path, resized_img)  # 使用 PNG 格式保存
                image_files.append(filename)
                save_count += 1

# 识别所有裁剪图像并保存结果
results_data = []
for filename in image_files:
    image_path = os.path.join(OUTPUT_DIR, filename)

    # 构建命令行参数
    args = [
        BARCODE_READER_PATH,
        f'-type={CODE_TYPE}',
        # '-type=code128',
        image_path
    ]

    # 调用外部程序
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
        if output != "":
            print("STDOUT:\n" + output)
    except subprocess.CalledProcessError as e:
        output = ""
        error = f"调用失败: {e}"

    # 保存结果
    results_data.append({
        "filename": filename,
        "output": output,
        "error": error
    })

# 保存结果为 JSON 文件
json_path = os.path.join(OUTPUT_DIR, "results.json")
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(results_data, f, ensure_ascii=False, indent=2)

print(f"识别结果已保存至: {json_path}")
