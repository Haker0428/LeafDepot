import cv2
import numpy as np
import os
import sys
import argparse
import csv
from PIL import Image
from tqdm import tqdm
import matplotlib.pyplot as plt

def split_image(image_path):
    """将图像分割为四个象限"""
    try:
        img = Image.open(image_path)
        width, height = img.size
        if width < 2 or height < 2:
            raise ValueError(f"图片尺寸过小 ({width}x{height})，无法分割")

        mid_x = width // 2
        mid_y = height // 2

        # 定义四个象限
        quadrants = [
            (0, 0, mid_x, mid_y),          # 左上
            (mid_x, 0, width, mid_y),      # 右上
            (0, mid_y, mid_x, height),     # 左下
            (mid_x, mid_y, width, height)  # 右下
        ]

        # 创建输出目录
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_dir = os.path.join(os.path.dirname(image_path), f"{base_name}_split")
        os.makedirs(output_dir, exist_ok=True)

        quadrant_paths = []
        for i, bbox in enumerate(quadrants, start=1):
            quadrant = img.crop(bbox)
            output_path = os.path.join(output_dir, f"{base_name}_{i}.jpg")
            quadrant.save(output_path, "JPEG", quality=95)
            quadrant_paths.append(output_path)

        return quadrant_paths, output_dir, width, height

    except Exception as e:
        print(f"分割错误: {str(e)}")
        sys.exit(1)

def generate_disparity_map(left_path, right_path, output_dir="disparity_results"):
    """生成视差图及可视化，并旋转可视化图像90度"""
    # 读取图像
    left_img = cv2.imread(left_path)
    right_img = cv2.imread(right_path)
    
    if left_img is None or right_img is None:
        raise FileNotFoundError("无法读取左右图像")
    
    # 确保图像尺寸一致
    if left_img.shape[0] != right_img.shape[0] or left_img.shape[1] != right_img.shape[1]:
        print("左右图像尺寸不一致，调整为一致的尺寸...")
        new_height = min(left_img.shape[0], right_img.shape[0])
        new_width = min(left_img.shape[1], right_img.shape[1])
        left_img = cv2.resize(left_img, (new_width, new_height))
        right_img = cv2.resize(right_img, (new_width, new_height))
        print(f"调整后尺寸: {new_width}x{new_height}") 
    
    # 打印实际处理尺寸
    print(f"实际处理尺寸: {left_img.shape[1]}x{left_img.shape[0]}")
    
    # 转换为灰度图
    left_gray = cv2.cvtColor(left_img, cv2.COLOR_BGR2GRAY)
    right_gray = cv2.cvtColor(right_img, cv2.COLOR_BGR2GRAY)
    
    # 使用SGBM算法创建视差图
    print("使用SGBM算法计算视差图...")
    
    # 配置视差参数
    window_size = 11
    min_disp = 0
    num_disp = 128 - min_disp
    
    stereo = cv2.StereoSGBM_create(
        minDisparity=min_disp,
        numDisparities=num_disp,
        blockSize=window_size,
        P1=8 * 3 * window_size ** 2,
        P2=32 * 3 * window_size ** 2,
        disp12MaxDiff=10,
        uniquenessRatio=20,
        speckleWindowSize=200,
        speckleRange=2
    )
    
    # 计算视差图
    disparity = stereo.compute(left_gray, right_gray).astype(np.float32) / 16.0
    
    # 保存结果目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存原始视差数据
    disparity_path = os.path.join(output_dir, "disparity.tiff")
    cv2.imwrite(disparity_path, disparity)
    print(f"原始视差图尺寸: {disparity.shape[1]}x{disparity.shape[0]}")
    
    # 创建归一化的可视化视差图 (8位灰度)
    disparity_visual = cv2.normalize(
        disparity, None, alpha=0, beta=255, 
        norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U
    )
    
    # 创建彩色可视化视差图
    disparity_color = cv2.applyColorMap(disparity_visual, cv2.COLORMAP_JET)
    
    # 旋转可视化图像90度（顺时针）
    disparity_visual = cv2.rotate(disparity_visual, cv2.ROTATE_90_CLOCKWISE)
    disparity_color = cv2.rotate(disparity_color, cv2.ROTATE_90_CLOCKWISE)
    
    # 保存可视化图像
    disparity_gray_path = os.path.join(output_dir, "disparity_visual_gray.jpg")
    disparity_color_path = os.path.join(output_dir, "disparity_visual_color.jpg")
    
    cv2.imwrite(disparity_gray_path, disparity_visual)
    cv2.imwrite(disparity_color_path, disparity_color)
    
    print(f"旋转后的灰度视差图保存至: {disparity_gray_path}")
    print(f"旋转后的彩色视差图保存至: {disparity_color_path}")
    
    return disparity_path, disparity, disparity_color_path

def calculate_depth(disparity, focal_length_px=11000.0, baseline_mm=60.0):
    """计算深度图（毫米单位）"""
    # 避免除以零错误
    disparity_img = np.copy(disparity)
    disparity_img[disparity_img <= 0] = 0.0001
    
    # 计算深度
    depth = (focal_length_px * baseline_mm) / disparity_img
    
    # 将过大值和无效值设为零
    depth[np.isinf(depth)] = 0
    depth[np.isnan(depth)] = 0
    
    return depth

def save_depth_map(depth, output_file):
    """保存深度图为TIFF文件，并创建可视化图像"""
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 保存深度图 (32位浮点)
    cv2.imwrite(output_file, depth.astype(np.float32))
    print(f"深度图尺寸: {depth.shape[1]}x{depth.shape[0]}")
    
    # 创建可视化图像（不旋转）
    depth_visual = cv2.normalize(
        depth, None, alpha=0, beta=255, 
        norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U
    )
    depth_color = cv2.applyColorMap(depth_visual, cv2.COLORMAP_JET)
    
    # 保存可视化图像
    depth_viz_path = os.path.splitext(output_file)[0] + "_visual.jpg"
    cv2.imwrite(depth_viz_path, depth_color)
    
    # 创建旋转后的可视化图像
    depth_color_rotated = cv2.rotate(depth_color, cv2.ROTATE_90_CLOCKWISE)
    depth_viz_rot_path = os.path.splitext(output_file)[0] + "_visual_rotated.jpg"
    cv2.imwrite(depth_viz_rot_path, depth_color_rotated)
    
    print(f"深度图保存至: {output_file}")
    print(f"深度可视化图保存至: {depth_viz_path}")
    print(f"旋转后的深度可视化图保存至: {depth_viz_rot_path}")
    
    return output_file, depth_viz_path

def save_depth_matrix(depth, csv_path):
    """
    将深度数据保存为矩阵格式的CSV文件
    :param depth: 深度数据数组（来自视差计算）
    :param csv_path: CSV文件保存路径
    """
    # 获取深度图尺寸
    height, width = depth.shape
    print(f"创建深度矩阵CSV: {width}列 x {height}行")
    
    # 创建输出目录
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    # 统计有效点个数
    valid_count = np.count_nonzero(depth)
    total_points = width * height
    valid_percent = valid_count / total_points * 100
    print(f"有效深度点占比: {valid_percent:.2f}% ({valid_count}/{total_points})")
    
    # 保存为CSV
    print(f"正在保存深度矩阵到CSV (尺寸: {height}行 x {width}列)")
    
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # 添加进度条
        for y in tqdm(range(height), desc="写入行"):
            # 为每行创建深度值列表
            row_depths = [f"{depth[y, x]:.4f}" for x in range(width)]
            writer.writerow(row_depths)
    
    # 创建一个小型预览图（100x100）保存为PNG
    depth_preview = cv2.resize(depth, (min(100, width), min(100, height)))
    preview_norm = cv2.normalize(
        depth_preview, None, alpha=0, beta=255, 
        norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U
    )
    preview_color = cv2.applyColorMap(preview_norm, cv2.COLORMAP_JET)
    
    preview_path = os.path.splitext(csv_path)[0] + "_preview.png"
    cv2.imwrite(preview_path, preview_color)
    
    print(f"深度矩阵CSV保存至: {csv_path}")
    print(f"深度预览图保存至: {preview_path}")
    return csv_path, preview_path

def main(image_path):
    print("=" * 50)
    print("开始处理图像:", os.path.basename(image_path))
    
    # 1. 分割图像
    print("\n步骤1: 分割图像...")
    quadrants, output_dir, orig_width, orig_height = split_image(image_path)
    print(f"原始图像尺寸: {orig_width}x{orig_height}")
    print(f"分割图目录: {output_dir}")
    
    # 2. 提取左上和右上图像
    top_left_path = quadrants[0]  # 左上
    top_right_path = quadrants[1] # 右上
    print(f"左眼图像: {os.path.basename(top_left_path)}")
    print(f"右眼图像: {os.path.basename(top_right_path)}")
    
    # 3. 生成视差图
    print("\n步骤2: 生成视差图...")
    disparity_results_dir = os.path.join(output_dir, "disparity_results")
    disparity_path, disparity_data, disparity_visual = generate_disparity_map(
        top_left_path, top_right_path, disparity_results_dir)
    
    # 4. 计算深度图
    print("\n步骤3: 计算深度图...")
    depth = calculate_depth(disparity_data)
    depth_dir = os.path.join(output_dir, "depth_results")
    os.makedirs(depth_dir, exist_ok=True)
    
    depth_tiff_path = os.path.join(depth_dir, "depth.tiff")
    depth_tiff_path, depth_visual = save_depth_map(depth, depth_tiff_path)
    
    # 5. 保存为矩阵格式的CSV
    print("\n步骤4: 转换深度图为矩阵CSV...")
    depth_csv_path = os.path.join(depth_dir, "depth_matrix.csv")
    
    # 仅使用计算得到的深度数据，尺寸与depth.tiff完全一致
    csv_path, preview_path = save_depth_matrix(depth, depth_csv_path)
    
    print("\n" + "=" * 50)
    print("处理完成! 结果文件:")
    print(f"- 目录: {output_dir}")
    print(f"  - 分割图像 (4张)")
    print(f"  - disparity_results/: 视差数据及可视化")
    print(f"  - depth_results/:")
    print(f"      depth.tiff - 原始深度数据")
    print(f"      depth_visual.jpg - 深度图预览")
    print(f"      depth_visual_rotated.jpg - 旋转后深度预览")
    print(f"      depth_matrix.csv - 深度矩阵数据")
    print(f"      depth_matrix_preview.png - 矩阵预览图")
    print(f"\n*CSV格式说明: {depth.shape[0]}行 x {depth.shape[1]}列的矩阵")
    print(f"  第y行第x列的值 = 像素点(x, y)的深度(mm)，0表示无效值")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='改进的图像深度处理流程 (精确匹配深度图和CSV尺寸)')
    parser.add_argument('image', type=str, help='输入图像路径')
    args = parser.parse_args()
    
    if not os.path.exists(args.image):
        print(f"错误: 文件不存在 - {args.image}")
        sys.exit(1)
    
    main(args.image)
