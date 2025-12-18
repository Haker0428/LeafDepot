"""深度计算模块：从立体图像计算深度图"""

import cv2
import numpy as np
import os
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image


class DepthCalculator:
    """深度计算器：从立体图像计算深度图"""
    
    def __init__(self, 
                 focal_length_px: float = 11000.0,
                 baseline_mm: float = 60.0,
                 enable_debug: bool = True):
        """
        初始化深度计算器
        
        :param focal_length_px: 焦距（像素）
        :param baseline_mm: 基线长度（毫米）
        :param enable_debug: 是否启用调试输出
        """
        self.focal_length_px = focal_length_px
        self.baseline_mm = baseline_mm
        self.enable_debug = enable_debug
    
    def rotate_image(self, image_path: str, rotation_angle: int = -90, 
                     output_path: Optional[str] = None, 
                     overwrite: bool = False) -> str:
        """
        旋转图像（顺时针90度）
        
        :param image_path: 输入图像路径
        :param rotation_angle: 旋转角度（负数表示顺时针，默认-90度）
        :param output_path: 输出路径（可选，如果不提供且overwrite=False，则创建临时文件）
        :param overwrite: 是否覆盖原文件（默认False，创建新文件）
        :return: 旋转后的图像路径
        """
        try:
            # 支持的图像格式
            supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
            
            # 检查文件扩展名
            ext = os.path.splitext(image_path)[1].lower()
            if ext not in supported_formats:
                if self.enable_debug:
                    print(f"⚠️  不支持的图像格式: {ext}，跳过旋转")
                return image_path
            
            # 确定输出路径
            if output_path is None:
                if overwrite:
                    output_path = image_path
                else:
                    # 创建临时文件路径
                    base_name = os.path.splitext(os.path.basename(image_path))[0]
                    output_dir = os.path.dirname(image_path)
                    output_path = os.path.join(output_dir, f"{base_name}_rotated{ext}")
            
            # 打开图像并旋转
            with Image.open(image_path) as img:
                rotated = img.rotate(rotation_angle, expand=True)  # 负数表示顺时针旋转
                
                # 处理PNG图像透明度通道问题
                if ext == '.png' and img.mode == 'RGBA':
                    rotated.save(output_path, 'PNG', quality=100)
                # 处理JPEG质量保留
                elif ext in ('.jpg', '.jpeg'):
                    rotated.save(output_path, 'JPEG', quality=95, optimize=True, progressive=True)
                # 其他格式
                else:
                    rotated.save(output_path)
            
            if self.enable_debug:
                if overwrite:
                    print(f"✅ 已旋转图像（覆盖原文件）: {os.path.basename(image_path)} ({rotation_angle}度)")
                else:
                    print(f"✅ 已旋转图像: {os.path.basename(image_path)} -> {os.path.basename(output_path)} ({rotation_angle}度)")
            
            return output_path
            
        except Exception as e:
            if self.enable_debug:
                print(f"⚠️  旋转图像 {os.path.basename(image_path)} 时出错: {str(e)}")
            return image_path
    
    def split_image(self, image_path: str, output_base_dir: Optional[str] = None) -> Tuple[list, str, int, int]:
        """
        将图像分割为四个象限
        
        :param image_path: 输入图像路径
        :param output_base_dir: 输出基础目录（可选，如果提供则保存到此目录）
        :return: (象限路径列表, 输出目录, 原始宽度, 原始高度)
        """
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
            if output_base_dir:
                # 如果提供了输出基础目录，保存到那里
                output_dir = os.path.join(output_base_dir, f"{base_name}_split")
            else:
                # 否则保存到图像同目录
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
            if self.enable_debug:
                print(f"分割错误: {str(e)}")
            raise
    
    def generate_disparity_map(self, left_path: str, right_path: str, 
                              output_dir: str = "disparity_results",
                              debug_output_dir: Optional[str] = None,
                              original_image_dir: Optional[str] = None) -> Tuple[str, np.ndarray, Optional[str]]:
        """
        生成视差图及可视化，并旋转视差数据90度（顺时针）
        
        :param left_path: 左眼图像路径
        :param right_path: 右眼图像路径
        :param output_dir: 输出目录（用于保存旋转后的视差数据）
        :param debug_output_dir: 调试输出目录（可选，用于保存可视化图像）
        :param original_image_dir: 原图目录（可选，用于在非debug模式下保存depth_color.jpg）
        :return: (视差图路径, 旋转后的视差数据, 彩色可视化路径)
        """
        # 读取图像
        left_img = cv2.imread(left_path)
        right_img = cv2.imread(right_path)
        
        if left_img is None or right_img is None:
            raise FileNotFoundError("无法读取左右图像")
        
        # 确保图像尺寸一致
        if left_img.shape[0] != right_img.shape[0] or left_img.shape[1] != right_img.shape[1]:
            if self.enable_debug:
                print("左右图像尺寸不一致，调整为一致的尺寸...")
            new_height = min(left_img.shape[0], right_img.shape[0])
            new_width = min(left_img.shape[1], right_img.shape[1])
            left_img = cv2.resize(left_img, (new_width, new_height))
            right_img = cv2.resize(right_img, (new_width, new_height))
            if self.enable_debug:
                print(f"调整后尺寸: {new_width}x{new_height}") 
        
        # 打印实际处理尺寸
        if self.enable_debug:
            print(f"实际处理尺寸: {left_img.shape[1]}x{left_img.shape[0]}")
        
        # 转换为灰度图
        left_gray = cv2.cvtColor(left_img, cv2.COLOR_BGR2GRAY)
        right_gray = cv2.cvtColor(right_img, cv2.COLOR_BGR2GRAY)
        
        # 使用SGBM算法创建视差图
        if self.enable_debug:
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
        
        # 旋转视差数据90度（顺时针）
        disparity_rotated = cv2.rotate(disparity, cv2.ROTATE_90_CLOCKWISE)
        if self.enable_debug:
            print(f"原始视差图尺寸: {disparity.shape[1]}x{disparity.shape[0]}")
            print(f"旋转后视差图尺寸: {disparity_rotated.shape[1]}x{disparity_rotated.shape[0]}")
        
        # 保存旋转后的原始视差数据
        disparity_path = os.path.join(output_dir, "disparity.tiff")
        cv2.imwrite(disparity_path, disparity_rotated)
        
        # 生成可视化图像（无论debug模式与否）
        # 创建归一化的可视化视差图 (8位灰度) - 使用旋转后的数据
        disparity_visual = cv2.normalize(
            disparity_rotated, None, alpha=0, beta=255, 
            norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U
        )
        
        # 创建彩色可视化视差图
        disparity_color = cv2.applyColorMap(disparity_visual, cv2.COLORMAP_JET)
        
        disparity_color_path = None
        
        # debug模式下：保存到debug_output_dir
        if self.enable_debug:
            # 确定可视化图像保存目录（优先使用debug_output_dir）
            if debug_output_dir is not None:
                vis_output_dir = debug_output_dir
            else:
                vis_output_dir = output_dir
            
            # 确保目录存在
            os.makedirs(vis_output_dir, exist_ok=True)
            
            # 保存可视化图像（已经是旋转后的）
            disparity_gray_path = os.path.join(vis_output_dir, "disparity_visual_gray.jpg")
            disparity_color_path = os.path.join(vis_output_dir, "depth_color.jpg")
            
            # 保存图像
            success_gray = cv2.imwrite(disparity_gray_path, disparity_visual)
            success_color = cv2.imwrite(disparity_color_path, disparity_color)
            
            if success_gray and success_color:
                print(f"✅ 旋转后的灰度视差图保存至: {disparity_gray_path}")
                print(f"✅ 旋转后的彩色视差图保存至: {disparity_color_path}")
            else:
                print(f"⚠️  视差图保存失败: gray={success_gray}, color={success_color}")
                print(f"   保存路径: {vis_output_dir}")
        
        # 非debug模式下：保存到原图路径，命名为depth_color.jpg
        if original_image_dir is not None:
            os.makedirs(original_image_dir, exist_ok=True)
            depth_path = os.path.join(original_image_dir, "depth_color.jpg")
            success = cv2.imwrite(depth_path, disparity_color)
            if success:
                if self.enable_debug:
                    print(f"✅ 深度图已保存至原图路径: {depth_path}")
            else:
                if self.enable_debug:
                    print(f"⚠️  深度图保存失败: {depth_path}")
        
        # 返回旋转后的视差数据，用于后续深度计算
        return disparity_path, disparity_rotated, disparity_color_path
    
    def calculate_depth(self, disparity: np.ndarray) -> np.ndarray:
        """
        计算深度图（毫米单位）
        
        :param disparity: 视差数据
        :return: 深度图（毫米）
        """
        # 避免除以零错误
        disparity_img = np.copy(disparity)
        disparity_img[disparity_img <= 0] = 0.0001
        
        # 计算深度
        depth = (self.focal_length_px * self.baseline_mm) / disparity_img
        
        # 将过大值和无效值设为零
        depth[np.isinf(depth)] = 0
        depth[np.isnan(depth)] = 0
        
        return depth
    
    def save_depth_matrix(self, depth: np.ndarray, csv_path: str) -> Tuple[str, str]:
        """
        将深度数据保存为矩阵格式的CSV文件
        
        :param depth: 深度数据数组（来自视差计算）
        :param csv_path: CSV文件保存路径
        :return: (CSV路径, 预览图路径)
        """
        # 获取深度图尺寸
        height, width = depth.shape
        if self.enable_debug:
            print(f"创建深度矩阵CSV: {width}列 x {height}行")
        
        # 创建输出目录
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        # 统计有效点个数
        valid_count = np.count_nonzero(depth)
        total_points = width * height
        valid_percent = valid_count / total_points * 100
        if self.enable_debug:
            print(f"有效深度点占比: {valid_percent:.2f}% ({valid_count}/{total_points})")
        
        # 保存为CSV
        if self.enable_debug:
            print(f"正在保存深度矩阵到CSV (尺寸: {height}行 x {width}列)")
        
        import csv
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for y in range(height):
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
        
        if self.enable_debug:
            print(f"深度矩阵CSV保存至: {csv_path}")
            print(f"深度预览图保存至: {preview_path}")
        
        return csv_path, preview_path
    
    def process_stereo_image(self, image_path: str, 
                            output_dir: Optional[str] = None,
                            debug_output_dir: Optional[str] = None,
                            skip_rotation: bool = False,
                            original_image_dir: Optional[str] = None) -> Tuple[np.ndarray, str]:
        """
        处理立体图像，生成深度矩阵CSV
        
        :param image_path: 输入图像路径（包含四个象限的立体图像）
        :param output_dir: 输出目录（可选，默认在图像同目录下）
        :param debug_output_dir: 调试输出目录（可选，用于保存视差图可视化）
        :param skip_rotation: 是否跳过旋转（如果图像已经旋转过）
        :param original_image_dir: 原图目录（可选，用于在非debug模式下保存depth_color.jpg）
        :return: (深度图数组, depth_matrix.csv路径)
        """
        if self.enable_debug:
            print("=" * 50)
            print("开始处理立体图像:", os.path.basename(image_path))
        
        # 0. 旋转图像（顺时针90度）- 如果未跳过
        if not skip_rotation:
            if self.enable_debug:
                print("\n步骤0: 旋转图像（顺时针90度）...")
            # 创建旋转后的临时图像文件（不覆盖原文件）
            rotated_image_path = self.rotate_image(image_path, rotation_angle=-90, overwrite=False)
        else:
            if self.enable_debug:
                print("\n步骤0: 跳过旋转（图像已旋转）...")
            rotated_image_path = image_path
        
        # 1. 分割图像（使用旋转后的图像）
        if self.enable_debug:
            print("\n步骤1: 分割图像...")
        # 如果提供了debug_output_dir，将split结果保存到那里
        # 这样所有生成的图都会在output目录下
        split_base_dir = debug_output_dir if debug_output_dir else None
        quadrants, split_output_dir, orig_width, orig_height = self.split_image(
            rotated_image_path, output_base_dir=split_base_dir)
        
        # split_image已经会将图保存到debug_output_dir（如果提供）
        if self.enable_debug:
            print(f"原始图像尺寸: {orig_width}x{orig_height}")
            print(f"分割图目录: {split_output_dir}")
        
        # 2. 提取左上和右上图像（左右图）
        # 注意：根据用户要求，使用左上和右上象限
        left_path = quadrants[0]  # 左上象限作为左图
        right_path = quadrants[1]  # 右上象限作为右图
        if self.enable_debug:
            print(f"\n📸 深度处理使用的左右图:")
            print(f"   ✅ 左图（左眼图像）: {os.path.basename(left_path)} - 左上象限 (quadrants[0])")
            print(f"   ✅ 右图（右眼图像）: {os.path.basename(right_path)} - 右上象限 (quadrants[1])")
            print(f"   左图完整路径: {left_path}")
            print(f"   右图完整路径: {right_path}")
            
            # 打印左右图的详细信息
            import cv2
            left_img = cv2.imread(left_path)
            right_img = cv2.imread(right_path)
            if left_img is not None and right_img is not None:
                print(f"\n   左图尺寸: {left_img.shape[1]}x{left_img.shape[0]} (宽x高)")
                print(f"   右图尺寸: {right_img.shape[1]}x{right_img.shape[0]} (宽x高)")
        
        # 3. 生成视差图
        if self.enable_debug:
            print("\n步骤2: 生成视差图...")
        disparity_results_dir = os.path.join(split_output_dir, "disparity_results")
        disparity_path, disparity_data, disparity_visual = self.generate_disparity_map(
            left_path, right_path, disparity_results_dir, 
            debug_output_dir=debug_output_dir,
            original_image_dir=original_image_dir)
        
        # 4. 计算深度图
        if self.enable_debug:
            print("\n步骤3: 计算深度图...")
        depth = self.calculate_depth(disparity_data)
        
        # 5. 保存深度矩阵CSV
        if self.enable_debug:
            print("\n步骤4: 转换深度图为矩阵CSV...")
        if output_dir is None:
            depth_dir = os.path.join(split_output_dir, "depth_results")
        else:
            depth_dir = output_dir
        os.makedirs(depth_dir, exist_ok=True)
        
        depth_csv_path = os.path.join(depth_dir, "depth_matrix.csv")
        csv_path, preview_path = self.save_depth_matrix(depth, depth_csv_path)
        
        if self.enable_debug:
            print("\n" + "=" * 50)
            print("处理完成! 结果文件:")
            print(f"- 目录: {depth_dir}")
            print(f"  - depth_matrix.csv - 深度矩阵数据")
            print(f"  - depth_matrix_preview.png - 矩阵预览图")
            print(f"\n*CSV格式说明: {depth.shape[0]}行 x {depth.shape[1]}列的矩阵")
            print(f"  第y行第x列的值 = 像素点(x, y)的深度(mm)，0表示无效值")
        
        return depth, csv_path

