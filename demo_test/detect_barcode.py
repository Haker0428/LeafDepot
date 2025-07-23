import cv2
import numpy as np
import os
import signal
import sys
from tqdm import tqdm  # 添加进度条

# 全局变量，用于跟踪是否收到中断信号
interrupted = False

# 信号处理函数，用于捕获Ctrl+C


def signal_handler(sig, frame):
    global interrupted
    print("\n程序被用户中断，正在退出...")
    interrupted = True
    cv2.destroyAllWindows()
    sys.exit(0)


# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)


def suppress_near_duplicates(boxes, min_dist_thresh=15):
    """空间感知去除重复框（保留相距较远的多个条码）"""
    if len(boxes) == 0:
        return []

    kept = []
    for box in boxes:
        if interrupted:  # 检查是否被中断
            return kept

        x1, y1, w1, h1 = box
        cx1, cy1 = x1 + w1 // 2, y1 + h1 // 2

        too_close = False
        for kx, ky, kw, kh in kept:
            cx2, cy2 = kx + kw // 2, ky + kh // 2
            dist = np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
            if dist < min_dist_thresh:
                too_close = True
                break

        if not too_close:
            kept.append(box)

    return kept


def detect_barcode(image_path, result_image_path=None, save_crops=False, padding=0.2):
    """
    条形码检测主函数
    :param image_path: 输入图像路径
    :param result_image_path: 结果图像保存路径(可选)
    :param save_crops: 是否保存检测到的条形码区域
    :param padding: 条形码区域扩展比例
    :return: 检测到的条形码边界框列表
    """
    if not os.path.exists(image_path):
        print(f"错误: 文件 '{image_path}' 不存在")
        return []

    try:
        img = cv2.imread(image_path)
        if img is None:
            print(f"错误: 无法读取图像 '{image_path}'")
            return []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_h, img_w = img.shape[:2]
    except Exception as e:
        print(f"图像处理错误: {str(e)}")
        return []

    # 创建MSER检测器
    try:
        mser = cv2.MSER_create()
        mser.setMinArea(500)
        mser.setMaxArea(10000)
        regions, _ = mser.detectRegions(gray)
    except Exception as e:
        print(f"MSER检测错误: {str(e)}")
        return []

    candidates = []

    for region in regions:
        if interrupted:  # 检查是否被中断
            return []

        try:
            x, y, w, h = cv2.boundingRect(region)

            # 跳过图像顶部的区域（通常是标题等）
            if y < img_h * 0.3:
                continue

            aspect_ratio = w / float(h)
            area = w * h

            # 过滤不符合条形码特征的区域
            if not (1.0 < aspect_ratio < 10 and 500 < area < 20000):
                continue

            roi = gray[y:y+h, x:x+w]
            if roi.size == 0:
                continue

            # 1. 平滑区域过滤（空区域）
            roi_std = np.std(roi)
            if roi_std < 25:
                continue

            # 2. 梯度方向性分析（图标 vs 条形码）
            sobelx = cv2.Sobel(roi, cv2.CV_64F, 1, 0)
            sobely = cv2.Sobel(roi, cv2.CV_64F, 0, 1)
            v_std = np.std(sobelx)
            h_std = np.std(sobely)
            if v_std < 10 or v_std < h_std * 1.5:
                continue

            # 3. 灰度均值过滤（极亮/极暗误检）
            mean_intensity = np.mean(roi)
            if mean_intensity < 30 or mean_intensity > 230:
                continue

            # 4. 边缘密度过滤（防止空框）
            edge_count = np.count_nonzero(cv2.Canny(roi, 50, 150))
            if edge_count < roi.shape[0] * roi.shape[1] * 0.05:
                continue

            candidates.append((x, y, w, h))
        except Exception as e:
            print(f"处理区域时出错: {str(e)}")
            continue

    # 空间感知去除重复框
    final_boxes = suppress_near_duplicates(candidates, min_dist_thresh=15)

    if save_crops or result_image_path:
        for i, (x, y, w, h) in enumerate(final_boxes):
            if interrupted:  # 检查是否被中断
                return final_boxes

            # 扩大ROI
            x_pad = max(0, x - int(w * padding))
            y_pad = max(0, y - int(h * padding))
            w_pad = min(img_w - x_pad, int(w * (1 + 2 * padding)))
            h_pad = min(img_h - y_pad, int(h * (1 + 2 * padding)))

            # 绘制检测框
            cv2.rectangle(img, (x_pad, y_pad), (x_pad + w_pad,
                          y_pad + h_pad), (0, 255, 0), 2)

            # 添加标签
            cv2.putText(img, f"Barcode {i+1}", (x_pad, y_pad - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # # 保存裁剪区域
            # if save_crops:
            #     try:
            #         base_filename = os.path.splitext(
            #             os.path.basename(image_path))[0]
            #         crop_dir = os.path.join(
            #             os.path.dirname(result_image_path), "crops")
            #         os.makedirs(crop_dir, exist_ok=True)
            #         crop = img[y_pad:y_pad + h_pad, x_pad:x_pad + w_pad]
            #         crop_filename = f"barcode_{base_filename}_{i}.png"
            #         crop_path = os.path.join(crop_dir, crop_filename)
            #         cv2.imwrite(crop_path, crop)
            #     except Exception as e:
            #         print(f"保存条形码区域时出错: {str(e)}")

    # 保存结果图像
    if result_image_path:
        try:
            cv2.imwrite(result_image_path, img)
        except Exception as e:
            print(f"保存结果图像时出错: {str(e)}")

    return final_boxes


if __name__ == "__main__":
    print("===== 条形码检测程序 =====")
    print("按 Ctrl+C 可随时终止程序")

    # 设置输入输出目录
    input_dir = "./raw_img/BarCodeCam/600mmDistancePics/"  # 修改为你的输入目录
    output_dir = "./DistancePicsDetectionResults/"         # 修改为你的输出目录

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    # os.makedirs(os.path.join(output_dir, "crops"), exist_ok=True)

    # 获取支持的图片格式
    image_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]

    # 获取所有图片文件
    image_files = [f for f in os.listdir(input_dir)
                   if os.path.splitext(f)[1].lower() in image_extensions]

    print(f"\n找到 {len(image_files)} 张图片待处理")

    # 处理每张图片
    for filename in tqdm(image_files, desc="处理进度"):
        if interrupted:
            break

        try:
            image_path = os.path.join(input_dir, filename)
            result_image_path = os.path.join(
                output_dir, f"detected_{filename}")

            print(f"\n处理图像: {filename}")
            boxes = detect_barcode(
                image_path,
                result_image_path=result_image_path,
                save_crops=True,
                padding=0.5
            )

            print(f"检测到 {len(boxes)} 个条形码")
            print(f"结果已保存至: {result_image_path}")
            # print(f"裁剪区域已保存至: {os.path.join(output_dir, 'crops')}")

        except Exception as e:
            print(f"\n处理 {filename} 时出错: {str(e)}")
            continue

    print("\n所有图片处理完成")
    print("程序执行完毕")
