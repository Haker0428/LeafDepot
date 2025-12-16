"""深度处理模块：从深度矩阵CSV中提取和分析深度数据"""

import numpy as np
import csv
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
import matplotlib.pyplot as plt


class DepthProcessor:
    """深度处理器：从深度矩阵CSV中提取和分析深度数据"""
    
    def __init__(self, enable_debug: bool = True):
        """
        初始化深度处理器
        
        :param enable_debug: 是否启用调试输出
        """
        self.enable_debug = enable_debug
    
    def load_depth_matrix(self, csv_path: Union[str, Path]) -> np.ndarray:
        """
        加载深度矩阵CSV文件
        
        :param csv_path: CSV文件路径
        :return: 深度矩阵数组
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"深度矩阵CSV文件不存在: {csv_path}")
        
        if self.enable_debug:
            print(f"正在读取深度矩阵文件: {csv_path}")
        
        depth_matrix = []
        with open(csv_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                try:
                    float_row = [float(x) for x in row]
                    depth_matrix.append(float_row)
                except ValueError as e:
                    if self.enable_debug:
                        print(f"转换错误: {e} - 跳过此行")
        
        # 转换为NumPy数组
        depth_matrix = np.array(depth_matrix)
        depth_height, depth_width = depth_matrix.shape
        
        if self.enable_debug:
            print(f"深度矩阵尺寸: {depth_height}行 x {depth_width}列")
        
        return depth_matrix
    
    def extract_depth_at_position(self, depth_matrix: np.ndarray,
                                  norm_x: float, norm_y: float,
                                  region_size: int = 5) -> Dict:
        """
        从深度矩阵中提取指定位置的深度值（使用区域平均）
        
        :param depth_matrix: 深度矩阵数组
        :param norm_x: 归一化X坐标 (0~1)
        :param norm_y: 归一化Y坐标 (0~1)
        :param region_size: 区域大小（提取 region_size x region_size 区域的平均值）
        :return: 包含深度值和状态的字典
        """
        depth_height, depth_width = depth_matrix.shape
        
        # 计算像素坐标
        y = int(norm_y * depth_height)
        x = int(norm_x * depth_width)
        
        # 确保坐标在合理范围内
        if x < 0 or x >= depth_width or y < 0 or y >= depth_height:
            return {
                "success": False,
                "value": 0.0,
                "message": f"坐标超出范围: ({x}, {y})"
            }
        
        # 提取区域（确保边界安全）
        half_size = region_size // 2
        y_start = max(0, y - half_size)
        y_end = min(depth_height, y + half_size + 1)
        x_start = max(0, x - half_size)
        x_end = min(depth_width, x + half_size + 1)
        
        region_data = depth_matrix[y_start:y_end, x_start:x_end]
        
        # 提取有效点数据并过滤异常值
        valid_points = []
        all_region_values = []
        
        for i in range(region_data.shape[0]):
            for j in range(region_data.shape[1]):
                abs_y = y_start + i
                abs_x = x_start + j
                value = region_data[i, j]
                
                # 跳过无效点
                if value <= 0:
                    continue
                
                # 收集所有有效值用于计算中位数
                all_region_values.append(value)
                
                # 添加点信息
                point_info = {
                    'value': value,
                    'x': abs_x,
                    'y': abs_y
                }
                valid_points.append(point_info)
        
        # 计算区域中位数
        median_value = np.median(all_region_values) if all_region_values else 0
        
        if not valid_points:
            return {
                "success": False,
                "value": 0.0,
                "message": "无有效点"
            }
        
        # 过滤与中位数差距过大的点
        filtered_points = []
        
        # 第一轮过滤：使用中位数作为参考
        for point in valid_points:
            if abs(point['value'] - median_value) <= 500:
                filtered_points.append(point)
        
        # 如果过滤后点太少，尝试基于有效点的方差进行二次过滤
        if len(filtered_points) < 5:
            # 计算有效点的平均值和标准差
            valid_values = [p['value'] for p in valid_points]
            valid_mean = np.mean(valid_values)
            valid_std = np.std(valid_values)
            
            # 使用更宽松的条件：均值±2倍标准差
            filtered_points = [
                p for p in valid_points 
                if (abs(p['value'] - valid_mean) <= 2 * valid_std)
            ]
        
        if not filtered_points:
            return {
                "success": False,
                "value": 0.0,
                "message": "无有效过滤点"
            }
        
        # 计算平均值
        result_value = np.mean([p['value'] for p in filtered_points])
        
        # 计算统计信息
        values = [p['value'] for p in filtered_points]
        region_min = min(values)
        region_max = max(values)
        std_val = np.std(values)
        
        return {
            "success": True,
            "value": float(result_value),
            "median": float(median_value),
            "min": float(region_min),
            "max": float(region_max),
            "std": float(std_val),
            "valid_points": len(filtered_points),
            "total_points": len(valid_points),
            "pixel_x": x,
            "pixel_y": y
        }
    
    def process_depth_data(self, csv_file: Union[str, Path],
                          norm_x: float, norm_y: float,
                          output_dir: Optional[Union[str, Path]] = None) -> Dict:
        """
        处理深度数据：从depth_matrix.csv中提取指定坐标位置的数据
        
        :param csv_file: depth_matrix.csv文件路径
        :param norm_x: 归一化X坐标 (0~1)
        :param norm_y: 归一化Y坐标 (0~1)
        :param output_dir: 输出目录（可选，用于保存分析结果）
        :return: 处理结果字典
        """
        csv_file = Path(csv_file)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV文件不存在: {csv_file}")
        
        if norm_x < 0 or norm_x > 1 or norm_y < 0 or norm_y > 1:
            raise ValueError("坐标值必须在0~1范围内")
        
        # 加载深度矩阵
        depth_matrix = self.load_depth_matrix(csv_file)
        
        # 提取深度值
        result = self.extract_depth_at_position(depth_matrix, norm_x, norm_y)
        
        # 如果提供了输出目录，保存分析结果
        if output_dir is not None:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存文本结果
            result_file = output_dir / "depth_analysis_result.txt"
            coords_str = f"({norm_x:.6f},{norm_y:.6f})"
            pixel_str = f"({result.get('pixel_x', 'N/A')},{result.get('pixel_y', 'N/A')})"
            
            result_output = (
                f"深度矩阵文件: {csv_file}\n"
                f"坐标位置: {coords_str} → {pixel_str}\n"
                f"处理结果: {result.get('message', '成功')}\n"
                f"平均深度值: {result.get('value', 0.0):.1f} mm\n"
                f"区域中位数: {result.get('median', 0.0):.1f} mm\n"
                f"有效点数量: {result.get('valid_points', 0)}/{result.get('total_points', 0)}\n"
                f"值域: {result.get('min', 0.0):.1f} - {result.get('max', 0.0):.1f} mm\n"
                f"标准差: {result.get('std', 0.0):.1f} mm\n"
            )
            
            with open(result_file, 'w') as outfile:
                outfile.write(result_output)
            
            if self.enable_debug:
                print(f"分析结果已保存至: {result_file}")
        
        return result
