'''
Author: big box big box@qq.com
Date: 2025-12-03 22:58:31
LastEditors: big box big box@qq.com
LastEditTime: 2025-12-07 20:08:18
FilePath: /cam_sys/build/test.py
Description: 

Copyright (c) 2025 by lizh, All Rights Reserved. 
'''
import camera_api

cam = camera_api.CameraController()


# （3D）相机登录接口：IP、端口号、帐号、密码
cam.login("10.16.82.180", 8000, "admin", "qwe147852")

# 在获取图片前需要先调用该接口
# 预览通道号
# 0-主码流，1-子码流，2-码流3，3-码流4，以此类推
# 0-TCP方式，1-UDP方式，2-多播方式，3-RTP方式，4-RTP/RTSP，5-RSTP/HTTP
# 0-非阻塞取流，1-阻塞取流
cam.getRealPlay(1, 0, 0, 0)


# 获取图片接口：存储路径、任务号、库位号、相机类型（扫描相机或者深度相机）
cam.doGetCapturePicture_JPG_Param(
    "/home/ubuntu/LeafDepot/Intergration/app/cam_sys", "task01", "01-01-02", "depth_cam")

cam.doGetCapturePicture_JPG_Param(
    "/home/ubuntu/LeafDepot/Intergration/app/cam_sys", "task01", "01-01-02", "scan_cam")
