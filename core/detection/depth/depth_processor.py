"""深度处理模块：从depth_matrix.csv中提取指定坐标位置的深度数据"""

import numpy as np
import os
import csv
import matplotlib.pyplot as plt
from typing import Optional, Tuple, Dict


class DepthProcessor:
    """深度处理器：从CSV矩阵中提取和处理深度数据"""
    
    def __init__(self, enable_debug: bool = True):
        """
        初始化深度处理器
        
        :param enable_debug: 是否启用调试输出
        """
        self.enable_debug = enable_debug
    
    def load_depth_matrix(self, csv_file: str) -> np.ndarray:
        """
        从CSV文件加载深度矩阵
        
        :param csv_file: depth_matrix.csv文件路径
        :return: 深度矩阵（numpy数组）
        """
        if self.enable_debug:
            print(f"正在读取深度矩阵文件: {csv_file}")
        
        depth_matrix = []
        with open(csv_file, 'r') as csvfile:
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
    
    def extract_depth_at_position(self, 
                                   depth_matrix: np.ndarray,
                                   norm_x: float,
                                   norm_y: float,
                                   region_size: int = 5) -> Dict:
        """
        从深度矩阵中提取指定坐标位置的深度值
        
        :param depth_matrix: 深度矩阵（numpy数组）
        :param norm_x: 归一化X坐标 (0~1)
        :param norm_y: 归一化Y坐标 (0~1)
        :param region_size: 提取区域大小（默认5x5）
        :return: 提取结果字典
        """
        depth_height, depth_width = depth_matrix.shape
        
        # 计算像素坐标(取整)
        y = int(float(norm_y) * depth_height)
        x = int(float(norm_x) * depth_width)
        
        # 确保坐标在合理范围内
        if x < 0 or x >= depth_width or y < 0 or y >= depth_height:
            err_msg = f"坐标超出范围: ({x}, {y})"
            if self.enable_debug:
                print("错误: " + err_msg)
            return {
                "success": False,
                "error": err_msg,
                "value": 0.0
            }
        
        # 提取区域(确保边界安全)
        half_size = region_size // 2
        y_start = max(0, y - half_size)
        y_end = min(depth_height, y + half_size + 1)
        x_start = max(0, x - half_size)
        x_end = min(depth_width, x + half_size + 1)
        
        region_data = depth_matrix[y_start:y_end, x_start:x_end]
        region_height, region_width = region_data.shape

        # 提取有效点数据并过滤异常值
        valid_points = []
        all_region_values = []  # 存储所有有效值用于计算中位数

        for i in range(region_height):
            for j in range(region_width):
                abs_y = y_start + i
                abs_x = x_start + j
                value = region_data[i, j]
                
                # 跳过无效点
                if value <= 0:
                    continue
                    
                # 收集所有有效值用于计算中位数
                all_region_values.append(value)
                
                # 添加点信息(值和位置)
                point_info = {
                    'value': value,
                    'x': abs_x,
                    'y': abs_y
                }
                valid_points.append(point_info)

        # 计算区域中位数（如果有效值足够）
        median_value = np.median(all_region_values) if all_region_values else 0
        result_value = 0.0
        result_status = "无有效点"
        region_min = region_max = 0
        std_val = 0.0

        center_value = depth_matrix[y, x] if (0 <= y < depth_height and 0 <= x < depth_width) else 0
        
        if not valid_points:
            result_status = "无有效点"
        else:
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
                result_status = f"宽松过滤: {len(filtered_points)}/{len(valid_points)}点"
            else:
                result_status = f"中位数过滤: {len(filtered_points)}/{len(valid_points)}点"
            
            if filtered_points:
                # 计算平均值并保留1位小数
                result_value = round(np.mean([p['value'] for p in filtered_points]), 1)
                
                # 计算最小最大值
                values = [p['value'] for p in filtered_points]
                region_min = min(values)
                region_max = max(values)
                std_val = np.std(values)
            else:
                result_status = "无有效过滤点"

        return {
            "success": True,
            "value": result_value,
            "center_value": center_value,
            "median_value": median_value,
            "status": result_status,
            "valid_points_count": len(filtered_points) if filtered_points else 0,
            "total_valid_points": len(valid_points),
            "region_min": region_min,
            "region_max": region_max,
            "std": std_val,
            "pixel_coords": (x, y),
            "norm_coords": (norm_x, norm_y),
            "region_bounds": {
                "x_start": x_start,
                "x_end": x_end,
                "y_start": y_start,
                "y_end": y_end
            },
            "filtered_points": filtered_points if filtered_points else []
        }
    
    def process_depth_data(self, csv_file: str, norm_x: float, norm_y: float,
                          output_dir: Optional[str] = None) -> Optional[str]:
        """
        处理深度数据：从depth_matrix.csv中提取指定坐标位置的数据
        
        :param csv_file: depth_matrix.csv文件路径
        :param norm_x: 归一化X坐标 (0~1)
        :param norm_y: 归一化Y坐标 (0~1)
        :param output_dir: 输出目录（可选）
        :return: 结果文件路径（如果生成）
        """
        # 读取深度矩阵数据
        depth_matrix = self.load_depth_matrix(csv_file)
        
        # 提取深度值
        result = self.extract_depth_at_position(depth_matrix, norm_x, norm_y)
        
        if not result["success"]:
            # 保存错误信息
            if output_dir is None:
                output_dir = os.path.dirname(csv_file)
            result_file = os.path.join(output_dir, "depth_analysis_result.txt")
            with open(result_file, 'w') as outfile:
                outfile.write(f"深度矩阵文件: {csv_file}\n")
                outfile.write(f"坐标位置错误: {result['error']}\n")
            return result_file
        
        # 准备结果输出
        if output_dir is None:
            output_dir = os.path.dirname(csv_file)
        result_file = os.path.join(output_dir, "depth_analysis_result.txt")
        img_path = os.path.join(output_dir, f"depth_analysis_{norm_x:.3f}_{norm_y:.3f}.png")
        
        # 准备输出变量
        coords_str = f"({norm_x:.6f},{norm_y:.6f})"
        pixel_str = f"({result['pixel_coords'][0]},{result['pixel_coords'][1]})"
        region_bounds = result['region_bounds']
        region_size = f"{region_bounds['x_end'] - region_bounds['x_start']}x{region_bounds['y_end'] - region_bounds['y_start']}"
        
        # 构建方差字符串
        if result['valid_points_count'] > 0:
            variance_str = f"值域: {result['region_min']:.1f} - {result['region_max']:.1f} | 标准差: {result['std']:.1f}"
        else:
            variance_str = "值域: N/A | 标准差: N/A"

        # 输出结果
        result_output = (
            f"深度矩阵文件: {csv_file}\n"
            f"坐标位置: {coords_str} → {pixel_str}\n"
            f"区域范围: {pixel_str} ±2像素 ({region_size}区域)\n"
            f"中心点深度值: {result['center_value']:.1f}\n"
            f"区域中位数: {result['median_value']:.1f}\n"
            f"有效点数量: {result['valid_points_count']}/{result['total_valid_points']}\n"
            f"平均深度值: {result['value']:.1f}\n"
            f"处理结果: {result['status']}\n"
            f"{variance_str}\n"
            f"结果图表: {img_path}"
        )
        
        if self.enable_debug:
            print("\n" + "=" * 60)
            print("深度分析结果:")
            print(result_output)
            print("=" * 60)
        
        # 保存结果到文件
        with open(result_file, 'w') as outfile:
            outfile.write(result_output + "\n")
        
        # 生成可视化图表
        self._generate_visualization(
            depth_matrix,
            result,
            img_path,
            coords_str
        )
        
        return result_file
    
    def _generate_visualization(self, depth_matrix: np.ndarray, result: Dict,
                                img_path: str, coords_str: str):
        """生成处理区域的可视化图表"""
        try:
            x, y = result['pixel_coords']
            x_start = result['region_bounds']['x_start']
            x_end = result['region_bounds']['x_end']
            y_start = result['region_bounds']['y_start']
            y_end = result['region_bounds']['y_end']
            valid_points = result.get('filtered_points', [])
            filtered_points = valid_points  # 这里filtered_points就是有效点
            
            # 创建图表
            plt.figure(figsize=(14, 8))
            plt.suptitle(f"深度提取分析: 坐标 {coords_str}", fontsize=16)
            
            # 原始深度分布图
            ax1 = plt.subplot(1, 2, 1)
            depth_map = ax1.imshow(np.log1p(depth_matrix), cmap='viridis', origin='upper')
            ax1.plot([x], [y], 'ro', markersize=10, label='目标点')
            ax1.add_patch(plt.Rectangle(
                (x_start, y_start), x_end - x_start, y_end - y_start,
                fill=False, edgecolor='red', linewidth=2
            ))
            ax1.set_title(f"整体视图 ({depth_matrix.shape[1]}x{depth_matrix.shape[0]})")
            ax1.set_xlabel("X坐标")
            ax1.set_ylabel("Y坐标")
            plt.colorbar(depth_map, ax=ax1, label="对数深度值")
            ax1.legend(loc='best')
            
            # 区域放大视图
            ax2 = plt.subplot(1, 2, 2)
            region_data = depth_matrix[y_start:y_end, x_start:x_end]
            region_height, region_width = region_data.shape
            
            # 显示区域数据
            region_map = ax2.imshow(region_data, cmap='viridis', origin='upper', 
                      vmin=0, vmax=np.max(depth_matrix))
            
            # 标记目标点
            target_x = x - x_start
            target_y = y - y_start
            ax2.plot([target_x], [target_y], 'ro', markersize=10, label='目标点')
            
            # 标记有效点
            if filtered_points:
                for point in filtered_points:
                    point_x = point['x'] - x_start
                    point_y = point['y'] - y_start
                    ax2.plot([point_x], [point_y], 'go', markersize=8)
                ax2.plot([], [], 'go', markersize=8, label='有效点')
            
            # 添加网格
            ax2.grid(True, linestyle='--', alpha=0.3)
            
            # 添加颜色条
            plt.colorbar(region_map, ax=ax2, label="深度值")
            
            ax2.set_title(f"局部区域: {region_width}x{region_height}")
            ax2.set_xlabel("X偏移")
            ax2.set_ylabel("Y偏移")
            
            # 添加统计信息
            if filtered_points and len(filtered_points) > 0:
                stats_info = (
                    f"中心值: {result['center_value']:.1f}\n"
                    f"区域中位数: {result['median_value']:.1f}\n"
                    f"有效点数量: {result['valid_points_count']}\n"
                    f"平均值: {result['value']:.1f}\n"
                    f"值域: {result['region_min']:.1f} - {result['region_max']:.1f}\n"
                    f"标准差: {result['std']:.1f}"
                )
                plt.figtext(0.5, 0.05, stats_info, ha="center", fontsize=10, 
                            bbox=dict(facecolor='white', alpha=0.7))
            
            # 简化图例
            ax2.legend(loc='best')
            
            # 调整布局并保存
            plt.tight_layout(rect=[0, 0.05, 1, 0.95])
            plt.savefig(img_path, dpi=150)
            plt.close()
            
            if self.enable_debug:
                print(f"可视化图表已保存至: {img_path}")
                
        except Exception as e:
            if self.enable_debug:
                print(f"图表生成错误: {str(e)}")
