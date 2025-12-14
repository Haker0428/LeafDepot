'''
Author: big box big box@qq.com
Date: 2025-12-11 21:43:44
LastEditors: big box big box@qq.com
LastEditTime: 2025-12-11 22:12:56
FilePath: /cam_sys_3/scan_capture.py
Description: 

Copyright (c) 2025 by lizh, All Rights Reserved. 
'''
import sys
import os
import traceback

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
    
    # 测试登录
    print("尝试登录相机...")
    result = cam.login("10.16.82.182", 8000, "admin", "qwe147852")
    print(f"登录结果: {result}")
    
    # 设置任务信息
    print("设置任务信息...")
    cam.setTaskInfo("Task20251211001", "01-02-03")
    
    # 设置相机类型
    print("设置相机类型...")
    cam.setCameraType("scan_camera_2")
    
    # 继续其他测试
    print("开始预览...")
    cam.startRealPlay(1, 0, 0, 1)
    
    print("获取捕获...")
    cam.getCapture()
    
    print("停止预览...")
    cam.stopRealPlay()
    
    print("退出登录...")
    cam.logout()
    
    print("✅ 所有测试完成!")
    
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
                
except Exception as e:
    print(f"❌ 运行时错误: {str(e)}")
    print("\n错误详情:")
    traceback.print_exc()
