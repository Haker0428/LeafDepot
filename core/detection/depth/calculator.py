"""深度计算模块：从立体图像计算深度图"""

import cv2
import numpy as np
import os
import csv
import shutil
from pathlib import Path
from typing import Optional, Tuple, Union
from PIL import Image
from tqdm import tqdm


class DepthCalculator:
    """深度计算器：处理立体图像，生成深度图和深度矩阵"""
    
    def __init__(self, enable_debug: bool = True):
        """
        初始化深度计算器
        
        :param enable_debug: 是否启用调试输出
        """
        self.enable_debug = enable_debug
    
    def rotate_image(self, image_path: Union[str, Path], 
                     rotation_angle: int = -90,
                     output_path: Optional[Union[str, Path]] = None,
                     overwrite: bool = True) -> str:
        """
        旋转图像
        
        :param image_path: 输入图像路径
        :param rotation_angle: 旋转角度（负数表示顺时针，正数表示逆时针）
        :param output_path: 输出路径（可选，如果不提供则覆盖原图）
        :param overwrite: 是否覆盖已存在的文件
        :return: 输出图像路径
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"图像文件不存在: {image_path}")
        
        # 确定输出路径
        if output_path is None:
            output_path = image_path
        else:
            output_path = Path(output_path)
            if not overwrite and output_path.exists():
                if self.enable_debug:
                    print(f"ℹ️  文件已存在，跳过: {output_path}")
                return str(output_path)
        
        try:
            # 打开图像并旋转
            with Image.open(image_path) as img:
                rotated = img.rotate(rotation_angle, expand=True)
                
                # 处理不同格式
                ext = image_path.suffix.lower()
                if ext == '.png' and img.mode == 'RGBA':
                    rotated.save(output_path, 'PNG', quality=100)
                elif ext in ('.jpg', '.jpeg'):
                    rotated.save(output_path, 'JPEG', quality=95, optimize=True, progressive=True)
                else:
                    rotated.save(output_path)
                
                if self.enable_debug:
                    print(f"✅ 图像已旋转: {image_path.name} -> {output_path.name}")
                
                return str(output_path)
                
        except Exception as e:
            raise RuntimeError(f"旋转图像时出错: {e}")
    
    def split_image(self, image_path: Union[str, Path]) -> Tuple[list, Path, int, int]:
        """
        将图像分割为四个象限
        
        :param image_path: 输入图像路径
        :return: (分割后的图像路径列表, 输出目录, 原始宽度, 原始高度)
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"图像文件不存在: {image_path}")
        
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
            base_name = image_path.stem
            output_dir = image_path.parent / f"{base_name}_split"
            output_dir.mkdir(exist_ok=True)

            quadrant_paths = []
            for i, bbox in enumerate(quadrants, start=1):
                quadrant = img.crop(bbox)
                output_path = output_dir / f"{base_name}_{i}.jpg"
                quadrant.save(output_path, "JPEG", quality=95)
                quadrant_paths.append(str(output_path))

            if self.enable_debug:
                print(f"✅ 图像已分割为4个象限，保存至: {output_dir}")

            return quadrant_paths, output_dir, width, height

        except Exception as e:
            raise RuntimeError(f"分割图像时出错: {e}")
    
    def generate_disparity_map(self, left_path: Union[str, Path], 
                               right_path: Union[str, Path], 
                               output_dir: Union[str, Path] = "disparity_results") -> Tuple[str, np.ndarray, str]:
        """
        生成视差图及可视化，并旋转可视化图像90度
        
        :param left_path: 左图像路径
        :param right_path: 右图像路径
        :param output_dir: 输出目录
        :return: (视差图路径, 视差数据数组, 彩色可视化路径)
        """
        left_path = Path(left_path)
        right_path = Path(right_path)
        output_dir = Path(output_dir)
        
        # 读取图像
        left_img = cv2.imread(str(left_path))
        right_img = cv2.imread(str(right_path))
        
        if left_img is None or right_img is None:
            raise FileNotFoundError("无法读取左右图像")
        
        # 在debug模式下保存加载的左右图像
        if self.enable_debug:
            output_dir.mkdir(parents=True, exist_ok=True)
            left_save_path = output_dir / "left_image_loaded.jpg"
            right_save_path = output_dir / "right_image_loaded.jpg"
            cv2.imwrite(str(left_save_path), left_img)
            cv2.imwrite(str(right_save_path), right_img)
            print(f"💾 已保存加载的左图: {left_save_path}")
            print(f"💾 已保存加载的右图: {right_save_path}")
        
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
                # 保存调整后的图像
                left_resized_path = output_dir / "left_image_resized.jpg"
                right_resized_path = output_dir / "right_image_resized.jpg"
                cv2.imwrite(str(left_resized_path), left_img)
                cv2.imwrite(str(right_resized_path), right_img)
                print(f"💾 已保存调整后的左图: {left_resized_path}")
                print(f"💾 已保存调整后的右图: {right_resized_path}")
        
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
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存原始视差数据
        disparity_path = output_dir / "disparity.tiff"
        cv2.imwrite(str(disparity_path), disparity)
        if self.enable_debug:
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
        disparity_gray_path = output_dir / "disparity_visual_gray.jpg"
        disparity_color_path = output_dir / "disparity_visual_color.jpg"
        
        cv2.imwrite(str(disparity_gray_path), disparity_visual)
        cv2.imwrite(str(disparity_color_path), disparity_color)
        
        if self.enable_debug:
            print(f"旋转后的灰度视差图保存至: {disparity_gray_path}")
            print(f"旋转后的彩色视差图保存至: {disparity_color_path}")
        
        return str(disparity_path), disparity, str(disparity_color_path)
    
    def calculate_depth(self, disparity: np.ndarray, 
                       focal_length_px: float = 11000.0, 
                       baseline_mm: float = 60.0) -> np.ndarray:
        """
        计算深度图（毫米单位）
        
        :param disparity: 视差图数组
        :param focal_length_px: 焦距（像素单位）
        :param baseline_mm: 双目相机基线距离（毫米）
        :return: 深度图数组（毫米单位）
        """
        # 避免除以零错误
        disparity_img = np.copy(disparity)
        disparity_img[disparity_img <= 0] = 0.0001
        
        # 计算深度
        depth = (focal_length_px * baseline_mm) / disparity_img
        
        # 将过大值和无效值设为零
        depth[np.isinf(depth)] = 0
        depth[np.isnan(depth)] = 0
        
        return depth
    
    def save_depth_map(self, depth: np.ndarray, output_file: Union[str, Path]) -> Tuple[str, str]:
        """
        保存深度图为TIFF文件，并创建可视化图像
        
        :param depth: 深度图数组
        :param output_file: 输出文件路径
        :return: (深度图路径, 可视化图像路径)
        """
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存深度图 (32位浮点)
        cv2.imwrite(str(output_file), depth.astype(np.float32))
        if self.enable_debug:
            print(f"深度图尺寸: {depth.shape[1]}x{depth.shape[0]}")
        
        # 创建可视化图像（不旋转）
        depth_visual = cv2.normalize(
            depth, None, alpha=0, beta=255, 
            norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U
        )
        depth_color = cv2.applyColorMap(depth_visual, cv2.COLORMAP_JET)
        
        # 保存可视化图像
        depth_viz_path = output_file.with_suffix('.jpg').with_stem(output_file.stem + '_visual')
        cv2.imwrite(str(depth_viz_path), depth_color)
        
        # 创建旋转后的可视化图像
        depth_color_rotated = cv2.rotate(depth_color, cv2.ROTATE_90_CLOCKWISE)
        depth_viz_rot_path = output_file.with_suffix('.jpg').with_stem(output_file.stem + '_visual_rotated')
        cv2.imwrite(str(depth_viz_rot_path), depth_color_rotated)
        
        if self.enable_debug:
            print(f"深度图保存至: {output_file}")
            print(f"深度可视化图保存至: {depth_viz_path}")
            print(f"旋转后的深度可视化图保存至: {depth_viz_rot_path}")
        
        return str(output_file), str(depth_viz_path)
    
    def save_depth_matrix(self, depth: np.ndarray, csv_path: Union[str, Path]) -> Tuple[str, str]:
        """
        将深度数据保存为矩阵格式的CSV文件
        
        :param depth: 深度数据数组
        :param csv_path: CSV文件保存路径
        :return: (CSV路径, 预览图路径)
        """
        csv_path = Path(csv_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 获取深度图尺寸
        height, width = depth.shape
        if self.enable_debug:
            print(f"创建深度矩阵CSV: {width}列 x {height}行")
        
        # 统计有效点个数
        valid_count = np.count_nonzero(depth)
        total_points = width * height
        valid_percent = valid_count / total_points * 100
        if self.enable_debug:
            print(f"有效深度点占比: {valid_percent:.2f}% ({valid_count}/{total_points})")
        
        # 保存为CSV
        if self.enable_debug:
            print(f"正在保存深度矩阵到CSV (尺寸: {height}行 x {width}列)")
        
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # 添加进度条
            for y in tqdm(range(height), desc="写入行", disable=not self.enable_debug):
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
        
        preview_path = csv_path.with_suffix('.png').with_stem(csv_path.stem + '_preview')
        cv2.imwrite(str(preview_path), preview_color)
        
        if self.enable_debug:
            print(f"深度矩阵CSV保存至: {csv_path}")
            print(f"深度预览图保存至: {preview_path}")
        
        return str(csv_path), str(preview_path)
    
    def process_depth_image(self, depth_image_path: Union[str, Path],
                           output_dir: Union[str, Path],
                           debug_output_dir: Optional[Union[str, Path]] = None,
                           skip_rotation: bool = False,
                           split_image: bool = True) -> Tuple[np.ndarray, str]:
        """
        处理深度图：从深度图生成深度矩阵CSV
        
        :param depth_image_path: 深度图路径（可以是视差图或深度图，如果是立体图像格式需要分割）
        :param output_dir: 输出目录（用于保存CSV和缓存）
        :param debug_output_dir: 调试输出目录（用于保存视差图可视化，可选）
        :param skip_rotation: 是否跳过旋转（如果深度图已经是正确方向）
        :param split_image: 是否先分割图像（如果深度图是立体图像格式，包含左右视图）
        :return: (深度数组, CSV路径)
        """
        depth_image_path = Path(depth_image_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not depth_image_path.exists():
            raise FileNotFoundError(f"深度图文件不存在: {depth_image_path}")
        
        # 如果需要分割图像（立体图像格式）
        if split_image:
            if self.enable_debug:
                print("=" * 50)
                print("开始处理深度图（立体图像格式，需要分割）:", depth_image_path.name)
                print("\n步骤1: 分割深度图...")
            
            # 分割图像
            quadrants, split_dir, orig_width, orig_height = self.split_image(depth_image_path)
            
            # 提取左上和右上（左右视图）
            top_left_path = Path(quadrants[0])  # 左上
            top_right_path = Path(quadrants[1])  # 右上
            
            # 在debug模式下保存分割后的左上和右上（未旋转）
            if self.enable_debug:
                print("\n步骤2: 保存分割后的左上和右上深度图（未旋转）...")
                if debug_output_dir:
                    debug_output_dir = Path(debug_output_dir)
                    debug_output_dir.mkdir(parents=True, exist_ok=True)
                else:
                    debug_output_dir = output_dir / "depth_split_debug"
                    debug_output_dir.mkdir(parents=True, exist_ok=True)
                
                # 保存左上和右上（原始未旋转）
                left_original_path = debug_output_dir / "depth_left_original.jpg"
                right_original_path = debug_output_dir / "depth_right_original.jpg"
                
                # 直接复制文件，避免重复读取
                shutil.copy2(top_left_path, left_original_path)
                shutil.copy2(top_right_path, right_original_path)
                print(f"💾 已保存原始左上深度图（未旋转）: {left_original_path}")
                print(f"💾 已保存原始右上深度图（未旋转）: {right_original_path}")
            
            # 旋转左上和右上图像
            if self.enable_debug:
                print("\n步骤3: 旋转左上和右上深度图...")
            
            # 旋转左上图（顺时针90度，即-90度）
            left_rotated_path = split_dir / f"{top_left_path.stem}_rotated{top_left_path.suffix}"
            left_rotated_path = self.rotate_image(
                top_left_path,
                rotation_angle=-90,
                output_path=left_rotated_path,
                overwrite=True
            )
            
            # 旋转右上图（顺时针90度，即-90度）
            right_rotated_path = split_dir / f"{top_right_path.stem}_rotated{top_right_path.suffix}"
            right_rotated_path = self.rotate_image(
                top_right_path,
                rotation_angle=-90,
                output_path=right_rotated_path,
                overwrite=True
            )
            
            if self.enable_debug:
                print(f"✅ 左上深度图已旋转: {left_rotated_path}")
                print(f"✅ 右上深度图已旋转: {right_rotated_path}")
            
            # 读取旋转后的左上深度图（作为最终深度图）
            if self.enable_debug:
                print("\n步骤4: 读取旋转后的左上深度图...")
            depth_img = cv2.imread(str(left_rotated_path), cv2.IMREAD_UNCHANGED)
        else:
            # 直接读取深度图（不分割）
            if self.enable_debug:
                print("=" * 50)
                print("开始处理深度图（直接处理，不分割）:", depth_image_path.name)
            
            depth_img = cv2.imread(str(depth_image_path), cv2.IMREAD_UNCHANGED)
        
        if depth_img is None:
            raise RuntimeError(f"无法读取深度图: {depth_image_path}")
        
        # 如果是彩色图像，转换为灰度图
        if len(depth_img.shape) == 3:
            depth_img = cv2.cvtColor(depth_img, cv2.COLOR_BGR2GRAY)
        
        # 如果深度图是视差图，需要转换为深度图
        # 这里假设输入的是深度图，如果是视差图需要先转换
        depth_array = depth_img.astype(np.float32)
        
        # 如果深度值看起来像视差值（通常较小），则转换为深度
        if np.max(depth_array) < 1000:  # 可能是视差值
            if self.enable_debug:
                print("检测到视差图，转换为深度图...")
            depth_array = self.calculate_depth(depth_array)
        
        # 保存深度矩阵CSV
        if self.enable_debug:
            step_num = "步骤5" if split_image else "步骤1"
            print(f"\n{step_num}: 保存深度矩阵CSV...")
        csv_path = output_dir / "depth_matrix.csv"
        csv_path, preview_path = self.save_depth_matrix(depth_array, csv_path)
        
        if self.enable_debug:
            print(f"✅ 深度矩阵处理完成: {csv_path}")
            if split_image:
                print("=" * 50)
        
        return depth_array, csv_path
    
    def process_stereo_image(self, image_path: Union[str, Path],
                            output_dir: Union[str, Path],
                            focal_length_px: float = 11000.0,
                            baseline_mm: float = 60.0) -> Tuple[np.ndarray, str]:
        """
        处理立体图像：从包含左右视图的图像生成深度矩阵
        
        :param image_path: 输入图像路径（包含左右视图，需要分割）
        :param output_dir: 输出目录
        :param focal_length_px: 焦距（像素单位）
        :param baseline_mm: 基线距离（毫米）
        :return: (深度数组, CSV路径)
        """
        image_path = Path(image_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if self.enable_debug:
            print("=" * 50)
            print("开始处理立体图像:", image_path.name)
        
        # 1. 分割图像
        if self.enable_debug:
            print("\n步骤1: 分割图像...")
        quadrants, split_dir, orig_width, orig_height = self.split_image(image_path)
        
        # 2. 提取左上和右上图像（左右视图）
        top_left_path = Path(quadrants[0])  # 左上
        top_right_path = Path(quadrants[1])  # 右上
        
        # 在debug模式下保存分割后的左上和右上（未旋转）
        if self.enable_debug:
            print("\n步骤2: 保存分割后的左上和右上图像（未旋转）...")
            disparity_results_dir = output_dir / "disparity_results"
            disparity_results_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存左上和右上（原始未旋转）- 直接复制分割后的文件
            left_original_path = disparity_results_dir / "left_image_original.jpg"
            right_original_path = disparity_results_dir / "right_image_original.jpg"
            
            # 直接复制文件，避免重复读取
            shutil.copy2(top_left_path, left_original_path)
            shutil.copy2(top_right_path, right_original_path)
            print(f"💾 已保存原始左上图（未旋转）: {left_original_path}")
            print(f"💾 已保存原始右上图（未旋转）: {right_original_path}")
        
        # 3. 旋转左上和右上图像
        if self.enable_debug:
            print("\n步骤3: 旋转左上和右上图像...")
        
        # 旋转左上图（顺时针90度，即-90度）
        left_rotated_path = split_dir / f"{top_left_path.stem}_rotated{top_left_path.suffix}"
        left_rotated_path = self.rotate_image(
            top_left_path,
            rotation_angle=-90,
            output_path=left_rotated_path,
            overwrite=True
        )
        
        # 旋转右上图（顺时针90度，即-90度）
        right_rotated_path = split_dir / f"{top_right_path.stem}_rotated{top_right_path.suffix}"
        right_rotated_path = self.rotate_image(
            top_right_path,
            rotation_angle=-90,
            output_path=right_rotated_path,
            overwrite=True
        )
        
        if self.enable_debug:
            print(f"✅ 左上图已旋转: {left_rotated_path}")
            print(f"✅ 右上图已旋转: {right_rotated_path}")
        
        # 4. 生成视差图（使用旋转后的图像）
        if self.enable_debug:
            print("\n步骤4: 生成视差图（使用旋转后的图像）...")
        disparity_results_dir = output_dir / "disparity_results"
        disparity_path, disparity_data, disparity_visual = self.generate_disparity_map(
            left_rotated_path, right_rotated_path, disparity_results_dir)
        
        # 5. 计算深度图
        if self.enable_debug:
            print("\n步骤5: 计算深度图...")
        depth = self.calculate_depth(disparity_data, focal_length_px, baseline_mm)
        
        # 6. 保存深度图
        depth_dir = output_dir / "depth_results"
        depth_dir.mkdir(parents=True, exist_ok=True)
        depth_tiff_path = depth_dir / "depth.tiff"
        depth_tiff_path, depth_visual = self.save_depth_map(depth, depth_tiff_path)
        
        # 7. 保存为矩阵格式的CSV
        if self.enable_debug:
            print("\n步骤6: 转换深度图为矩阵CSV...")
        depth_csv_path = depth_dir / "depth_matrix.csv"
        csv_path, preview_path = self.save_depth_matrix(depth, depth_csv_path)
        
        if self.enable_debug:
            print("\n" + "=" * 50)
            print("处理完成! 结果文件:")
            print(f"- 目录: {output_dir}")
            print(f"  - 分割图像 (4张，在 {split_dir})")
            print(f"  - 旋转后的左右图 (在 {split_dir})")
            print(f"  - disparity_results/:")
            print(f"      left_image_original.jpg - 原始左上图（未旋转）")
            print(f"      right_image_original.jpg - 原始右上图（未旋转）")
            print(f"      left_image_loaded.jpg - 加载的旋转后左图")
            print(f"      right_image_loaded.jpg - 加载的旋转后右图")
            print(f"      left_image_resized.jpg - 调整后的左图（如果尺寸不一致）")
            print(f"      right_image_resized.jpg - 调整后的右图（如果尺寸不一致）")
            print(f"      disparity.tiff - 原始视差数据")
            print(f"      disparity_visual_gray.jpg - 灰度视差图")
            print(f"      disparity_visual_color.jpg - 彩色视差图")
            print(f"  - depth_results/:")
            print(f"      depth.tiff - 原始深度数据")
            print(f"      depth_visual.jpg - 深度图预览")
            print(f"      depth_visual_rotated.jpg - 旋转后深度预览")
            print(f"      depth_matrix.csv - 深度矩阵数据")
            print(f"      depth_matrix_preview.png - 矩阵预览图")
            print(f"\n*CSV格式说明: {depth.shape[0]}行 x {depth.shape[1]}列的矩阵")
            print(f"  第y行第x列的值 = 像素点(x, y)的深度(mm)，0表示无效值")
            print("=" * 50)
        
        return depth, csv_path
