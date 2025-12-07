/*
 * @Author: big box big box@qq.com
 * @Date: 2025-10-29 21:44:16
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2025-11-13 00:09:56
 * @FilePath: /cam_sys/src/main.cpp
 * @Description:
 *
 * Copyright (c) 2025 by lizh, All Rights Reserved.
 */
#include <iostream>

#include "CameraController.h"
#include "ConfigManager.h"

int main() {
  // 加载配置文件
  ConfigManager config;
  if (!config.loadConfig()) {
    std::cerr << "Failed to load configuration: " << config.getLastError()
              << std::endl;

    // 尝试创建默认配置文件
    std::cout << "Creating default configuration file..." << std::endl;
    if (!config.saveConfig()) {
      std::cerr << "Failed to create default config: " << config.getLastError()
                << std::endl;
      return -1;
    }
    std::cout << "Default config created. Please edit config.json and restart."
              << std::endl;
    return -1;
  }

  CameraController camera;

  // 初始化相机控制器
  if (!camera.initialize()) {
    std::cerr << "Failed to initialize camera controller: "
              << camera.getLastError() << std::endl;
    return -1;
  }

  // 从配置文件读取连接参数
  std::string ip = config.getCameraIP();
  int port = config.getCameraPort();
  std::string username = config.getCameraUsername();
  std::string password = config.getCameraPassword();

  std::cout << "Connecting to camera: " << ip << ":" << port
            << " as user: " << username << std::endl;

  // 从配置文件获取参数
  int channel = config.getCameraChannel();
  int streamType = config.getStreamType();
  int connectionType = config.getConnectionType();
  int streamMode = config.getStreamMode();

  std::cout << "Using parameters - Channel: " << channel
            << ", Stream Type: " << streamType
            << ", Connection Type: " << connectionType
            << ", Stream Mode: " << streamMode << std::endl;

  // 从配置文件获取搜索时间范围
  int searchSeconds = config.getPictureSearchSeconds();
  std::cout << "Using parameters - searchSeconds: " << searchSeconds
            << std::endl;

  // 连接到设备
  if (!camera.login(ip, port, username, password)) {
    std::cerr << "Login failed: " << camera.getLastError() << std::endl;
    return -1;
  }

  std::cout << "=== Camera Controller Demo ===" << std::endl;

  // （1）预览通道号
  // （2） 0-主码流，1-子码流，2-码流3，3-码流4，以此类推
  // （3）0- TCP方式，1- UDP方式，2-多播方式，3-RTP方式，4-RTP/RTSP，5-RSTP/HTTP
  // （4）0- 非阻塞取流，1- 阻塞取流
  camera.getRealPlay(channel, streamType, connectionType, streamMode);

  LinuxSystemTime timeStart = camera.getLocalTime();

  camera.doGetCapturePicture();

  LinuxSystemTime timeEnd(timeStart.year, timeStart.month, timeStart.day,
                          timeStart.hour, timeStart.minute,
                          timeStart.second + searchSeconds);

  // 查找30s内的照片
  std::cout << "\nSearching with 30s time range..." << std::endl;

  int pictureCount = camera.findPictures(channel, timeStart, timeEnd);

  if (pictureCount > 0) {
    std::cout << "Found " << pictureCount << " pictures in custom time range."
              << std::endl;
  }

  // 等待用户输入退出
  char input = 0;
  while (input != 'q') {
    std::cout << "\nEnter 'q' to quit: ";
    std::cin >> input;
  }

  std::cout << "Exiting application..." << std::endl;
  return 0;
}