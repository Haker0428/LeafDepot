/*
 * @Author: big box big box@qq.com
 * @Date: 2025-10-29 22:34:54
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2025-10-29 22:56:54
 * @FilePath: /cam_sys/src/CameraController.h
 * @Description:
 *
 * Copyright (c) 2025 by lizh, All Rights Reserved.
 */
#ifndef CAMERACONTROLLER_H
#define CAMERACONTROLLER_H

#include <string>

#include "HCNetSDK/HCNetSDK.h"

// Linux 系统时间结构体，替换 Windows 的 SYSTEMTIME
struct LinuxSystemTime {
  int year;
  int month;
  int day;
  int hour;
  int minute;
  int second;

  // 默认构造函数
  LinuxSystemTime()
      : year(0), month(0), day(0), hour(0), minute(0), second(0) {}

  // 带参数构造函数
  LinuxSystemTime(int y, int m, int d, int h, int min, int sec)
      : year(y), month(m), day(d), hour(h), minute(min), second(sec) {}
};

class CameraController {
 public:
  CameraController();
  ~CameraController();

  // 初始化与清理
  bool initialize();
  void cleanup();

  // 设备连接管理
  bool login(const std::string& deviceAddress, unsigned short port,
             const std::string& userName, const std::string& password);
  void logout();

  // 图片操作 - 使用当前时间自动查找
  int findPictures(int channel);

  // 图片操作 - 指定时间范围查找
  int findPictures(int channel, const LinuxSystemTime& startTime,
                   const LinuxSystemTime& endTime);

  // 下载特定图片
  bool downloadPicture(const NET_DVR_FIND_PICTURE_V50& fileInfo);

  // 状态查询
  bool isConnected() const { return m_isConnected && m_userId >= 0; }
  std::string getLastError() const { return m_lastError; }

  // 获取最后找到的图片信息
  NET_DVR_FIND_PICTURE_V50 getLastFoundPicture() const {
    return m_lastFoundPicture;
  }

  LinuxSystemTime getLocalTime();

 private:
  // 工具函数
  bool createDirectory(const std::string& path);
  std::string getExecutablePath();
  void setLastError(const std::string& error);

  // 图片处理
  int doFindPicture(int channel, const LinuxSystemTime& startTime,
                    const LinuxSystemTime& endTime,
                    NET_DVR_FIND_PICTURE_V50& fileInfo);
  bool doGetPicture(const NET_DVR_FIND_PICTURE_V50& fileInfo);

  // 时间转换
  void convertToNetDvrTime(const LinuxSystemTime& src, NET_DVR_TIME& dst);

  // 成员变量
  LONG m_userId;
  bool m_isConnected;
  bool m_isInitialized;
  std::string m_lastError;
  std::string m_saveDirectory;
  NET_DVR_FIND_PICTURE_V50 m_lastFoundPicture;
};

#endif  // CAMERACONTROLLER_H