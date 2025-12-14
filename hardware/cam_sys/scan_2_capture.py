'''
Author: big box big box@qq.com
Date: 2025-12-11 21:40:40
LastEditors: big box big box@qq.com
LastEditTime: 2025-12-11 22:12:25
FilePath: /cam_sys_3/3d_capture.py
Description: SCAN抓图脚本，接收任务编号和储位名称作为参数

Copyright (c) 2025 by lizh, All Rights Reserved. 
'''
import sys
import os
import traceback
import argparse

def main(task_no: str, bin_location: str):
    """
    主函数，执行SCAN抓图流程
    
    Args:
        task_no: 任务编号
        bin_location: 储位名称
    """
    print(f"任务编号: {task_no}")
    print(f"储位名称: {bin_location}")
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"当前目录: {current_dir}")

    # 列出当前目录所有文件
    print("当前目录文件列表:")
    for f in os.listdir(current_dir):
        if f.endswith('.so'):
            print(f"  [SO] {f}")
        else:
            print(f"      {f}")

    # 添加当前目录到Python路径
    sys.path.insert(0, current_dir)

    try:
        # 先检查模块文件是否存在
        so_file = None
        for f in os.listdir(current_dir):
            if f.startswith('camera_api') and f.endswith('.so'):
                so_file = os.path.join(current_dir, f)
                print(f"找到模块文件: {so_file}")
                break
        
        if not so_file:
            print("❌ 未找到camera_api*.so文件")
            sys.exit(1)
        
        # 检查文件权限
        if not os.access(so_file, os.R_OK):
            print(f"❌ 文件不可读: {so_file}")
            os.chmod(so_file, 0o644)
            print(f"✅ 已修复文件权限")
        
        # 检查Python版本匹配
        import platform
        python_version = sys.version_info
        print(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # 尝试导入
        print("尝试导入camera_api...")
        import camera_api
        
        print("✅ 成功导入camera_api模块!")
        
        # 创建对象
        print("创建CamController对象...")
        cam = camera_api.CamController()
        print("✅ CamController对象创建成功")
        
        # 登录
        print("尝试登录相机...")
        result = cam.login("10.16.82.182", 8000, "admin", "qwe147852")
        print(f"登录结果: {result}")
        
        # 设置任务信息（使用传入的参数）
        print(f"设置任务信息: 任务编号={task_no}, 储位信息={bin_location}")
        cam.setTaskInfo(task_no, bin_location)
        
        # 设置相机类型
        print("设置相机类型...")
        cam.setCameraType("scan_camera_2")
        
        # 预览主码流
        print("开始预览...")
        cam.startRealPlay(1, 0, 0, 1)
        
        # 捕获主码流
        print("获取捕获...")
        capture_result = cam.getCapture()
        print(f"捕获结果: {capture_result}")
        
        print("停止预览...")
        cam.stopRealPlay()
        
        print("退出登录...")
        cam.logout()
        
        print("✅ 所有测试完成!")
        
        # 返回成功结果
        return {
            "success": True,
            "task_no": task_no,
            "bin_location": bin_location,
            "capture_results": [
                {"stream": "main", "result": capture_result},
                {"stream": "fourth", "result": capture_result2}
            ]
        }
        
    except ImportError as e:
        print(f"❌ 导入失败: {str(e)}")
        print("\n详细错误信息:")
        traceback.print_exc()
        
        # 尝试查找所有可能的模块文件
        print("\n搜索所有可能的模块文件:")
        for root, dirs, files in os.walk(current_dir):
            for file in files:
                if 'camera_api' in file and file.endswith('.so'):
                    full_path = os.path.join(root, file)
                    print(f"  {full_path}")
        
        return {
            "success": False,
            "error": f"导入失败: {str(e)}",
            "task_no": task_no,
            "bin_location": bin_location
        }
                    
    except Exception as e:
        print(f"❌ 运行时错误: {str(e)}")
        print("\n错误详情:")
        traceback.print_exc()
        
        return {
            "success": False,
            "error": str(e),
            "task_no": task_no,
            "bin_location": bin_location
        }

if __name__ == "__main__":
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='SCAN_2_抓图脚本')
    parser.add_argument('--task-no', type=str, required=True, help='任务编号')
    parser.add_argument('--bin-location', type=str, required=True, help='储位名称')
    
    # 解析参数
    args = parser.parse_args()
    
    # 调用主函数
    result = main(args.task_no, args.bin_location)
    
    # 退出码
    exit_code = 0 if result.get("success", False) else 1
    sys.exit(exit_code)
