import numpy as np
import os
import csv
import matplotlib.pyplot as plt
import argparse

def process_depth_data(csv_file, norm_x, norm_y):
    """
    处理深度数据：从depth_matrix.csv中提取指定坐标位置的数据
    
    参数:
        csv_file: depth_matrix.csv文件路径
        norm_x: 归一化X坐标 (0~1)
        norm_y: 归一化Y坐标 (0~1)
    """
    # 读取深度矩阵数据
    print(f"正在读取深度矩阵文件: {csv_file}")
    depth_matrix = []
    with open(csv_file, 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            try:
                float_row = [float(x) for x in row]
                depth_matrix.append(float_row)
            except ValueError as e:
                print(f"转换错误: {e} - 跳过此行")
    
    # 转换为NumPy数组
    depth_matrix = np.array(depth_matrix)
    depth_height, depth_width = depth_matrix.shape
    print(f"深度矩阵尺寸: {depth_height}行 x {depth_width}列")
    
    # 准备结果输出
    output_dir = os.path.dirname(csv_file)
    result_file = os.path.join(output_dir, "depth_analysis_result.txt")
    img_path = os.path.join(output_dir, f"depth_analysis_{norm_x:.3f}_{norm_y:.3f}.png")
    
    # 计算像素坐标(取整)
    y = int(float(norm_y) * depth_height)
    x = int(float(norm_x) * depth_width)
    
    # 确保坐标在合理范围内
    if x < 0 or x >= depth_width or y < 0 or y >= depth_height:
        err_msg = f"坐标超出范围: ({x}, {y})"
        print("错误: " + err_msg)
        with open(result_file, 'w') as outfile:
            outfile.write(f"深度矩阵文件: {csv_file}\n")
            outfile.write(f"坐标位置错误: {err_msg}\n")
        return
    
    # 提取5x5区域(确保边界安全)
    y_start = max(0, y-2)
    y_end = min(depth_height, y+3)
    x_start = max(0, x-2)
    x_end = min(depth_width, x+3)
    
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

    center_value = depth_matrix[y, x] if (0 <= y < depth_height and 0 <= x < depth_width) else 'N/A'
    
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

    # 准备输出变量
    coords_str = f"({norm_x:.6f},{norm_y:.6f})"
    pixel_str = f"({x},{y})"
    region_size = f"{region_width}x{region_height}"
    
    # 构建方差字符串
    if filtered_points:
        variance_str = f"值域: {region_min:.1f} - {region_max:.1f} | 标准差: {std_val:.1f}"
    else:
        variance_str = "值域: N/A | 标准差: N/A"

    # 输出结果
    result_output = (
        f"深度矩阵文件: {csv_file}\n"
        f"坐标位置: {coords_str} → {pixel_str}\n"
        f"区域范围: {pixel_str} ±2像素 ({region_size}区域)\n"
        f"中心点深度值: {center_value}\n"  # 修改为直接输出不需要格式化的浮点数
        f"区域中位数: {median_value:.1f}\n"  # 添加中位数值
        f"有效点数量: {len(filtered_points) if 'filtered_points' in locals() else 0}/{len(valid_points)}\n"
        f"平均深度值: {result_value:.1f}\n"
        f"处理结果: {result_status}\n"
        f"{variance_str}\n"
        f"结果图表: {img_path}"
    )
    
    print("\n" + "=" * 60)
    print("深度分析结果:")
    print(result_output)
    print("=" * 60)
    
    # 保存结果到文件
    with open(result_file, 'w') as outfile:
        outfile.write(result_output + "\n")
    
    # 生成可视化图表
    generate_visualization(
        depth_matrix,
        x, y, x_start, x_end, y_start, y_end,
        valid_points, filtered_points,
        img_path, coords_str
    )
    
    return result_file

def generate_visualization(depth_matrix, x, y, x_start, x_end, y_start, y_end,
                           valid_points, filtered_points, img_path, coords_str):
    """生成处理区域的可视化图表"""
    try:
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
        
        # 标记有效点和过滤点
        valid_added = False
        filtered_added = False
        
        for point in valid_points:
            point_x = point['x'] - x_start
            point_y = point['y'] - y_start
            
            if filtered_points and point in filtered_points:
                if not valid_added:
                    ax2.plot([point_x], [point_y], 'go', markersize=8, label='有效点')
                    valid_added = True
                else:
                    ax2.plot([point_x], [point_y], 'go', markersize=8)
            else:
                if not filtered_added:
                    ax2.plot([point_x], [point_y], 'rx', markersize=8, label='过滤点')
                    filtered_added = True
                else:
                    ax2.plot([point_x], [point_y], 'rx', markersize=8)
        
        # 添加网格
        ax2.grid(True, linestyle='--', alpha=0.3)
        
        # 添加颜色条
        plt.colorbar(region_map, ax=ax2, label="深度值")
        
        ax2.set_title(f"局部区域: {region_width}x{region_height}")
        ax2.set_xlabel("X偏移")
        ax2.set_ylabel("Y偏移")
        
        # 添加统计信息
        if filtered_points and len(filtered_points) > 0:
            min_val = min(p['value'] for p in filtered_points)
            max_val = max(p['value'] for p in filtered_points)
            avg_val = np.mean([p['value'] for p in filtered_points])
            stats_info = (
                f"中心值: {depth_matrix[y, x]:.1f}\n"
                f"区域中位数: {np.median([p['value'] for p in filtered_points]):.1f}\n"
                f"有效点数量: {len(filtered_points)}\n"
                f"平均值: {avg_val:.1f}\n"
                f"值域: {min_val:.1f} - {max_val:.1f}\n"
                f"标准差: {np.std([p['value'] for p in filtered_points]):.1f}"
            )
            plt.figtext(0.5, 0.05, stats_info, ha="center", fontsize=10, 
                        bbox=dict(facecolor='white', alpha=0.7))
        
        # 简化图例（避免重复）
        handles, labels = ax2.get_legend_handles_labels()
        unique_handles = []
        unique_labels = []
        
        for handle, label in zip(handles, labels):
            if label not in unique_labels:
                unique_labels.append(label)
                unique_handles.append(handle)
        ax2.legend(unique_handles, unique_labels, loc='best')
        
        # 调整布局并保存
        plt.tight_layout(rect=[0, 0.05, 1, 0.95])
        plt.savefig(img_path, dpi=150)
        plt.close()
        
        print(f"可视化图表已保存至: {img_path}")
        
    except Exception as e:
        print(f"图表生成错误: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='深度数据处理工具', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('csv_file', type=str, help='深度矩阵CSV文件路径')
    parser.add_argument('norm_x', type=float, help='归一化X坐标 (0~1)')
    parser.add_argument('norm_y', type=float, help='归一化Y坐标 (0~1)')
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"错误: CSV文件不存在 - {args.csv_file}")
        return
    
    if args.norm_x < 0 or args.norm_x > 1 or args.norm_y < 0 or args.norm_y > 1:
        print("错误: 坐标值必须在0~1范围内")
        return
    
    print("=" * 60)
    print(f"      深度数据提取工具")
    print(f"  目标位置: ({args.norm_x:.6f}, {args.norm_y:.6f})")
    print("=" * 60)
    
    result_file = process_depth_data(args.csv_file, args.norm_x, args.norm_y)
    
    print("\n" + "=" * 60)
    print(f"处理完成! 完整结果已保存至: {result_file}")

if __name__ == "__main__":
    main()
