'''
Author: big box big box@qq.com
Date: 2025-10-14 22:39:44
LastEditors: big box big box@qq.com
LastEditTime: 2025-10-15 00:19:25
FilePath: /rcs_client/main.py
Description: 

Copyright (c) 2025 by lizh, All Rights Reserved. 
'''
# main.py
from lms_client import LMSClient
from config_loader import ConfigLoader

if __name__ == "__main__":
    # 加载配置
    config = ConfigLoader()

    # 使用配置
    LMS_BASE_URL = config.get_lms_base_url()
    USER_CODE = config.get_user_code()
    PASSWORD = config.get_password()
    
    print("="*50)
    print("LMS智慧物流系统接口交互程序")
    print(f"目标系统: {LMS_BASE_URL}")
    print(f"用户: {USER_CODE}")
    print("="*50)

    client = LMSClient(LMS_BASE_URL, USER_CODE, PASSWORD)
    client.run()

    print("\n" + "="*50)
    print("程序执行完成！")
    print("数据已保存到 data/ 目录:")
    print("- bins.json: 储位信息")
    print("- tasks.json: 盘点任务")
    print("- tasks_updated.json: 更新后的盘点任务状态")
    print("="*50)
