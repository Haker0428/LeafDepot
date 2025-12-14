/*
 * @Author: lizh 447628890@qq.com
 * @Date: 2025-12-10 17:45:43
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2025-12-11 22:02:19
 * @FilePath: /cam_sys_3/src/CamController.h
 * @Description:
 *
 * Copyright (c) 2025 by lizh, All Rights Reserved.
 */
#pragma once

#include <memory.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>

#include <iostream>
#include <string>
#include <thread>

#include "HCNetSDK/HCNetSDK.h"
#include "HCNetSDK/PlayM4.h"

class CamController {
 public:
  CamController();
  ~CamController();

  // 设备连接管理
  bool login(const std::string& deviceAddress, unsigned short port,
             const std::string& userName, const std::string& password);
  bool logout();

  bool startRealPlay(unsigned short channel, unsigned short stream_type,
                     unsigned short linkMode, unsigned short blocked);

  bool stopRealPlay();

  void getCapture();

  void setTaskInfo(std::string task_id, std::string bin_code);

  void setCameraType(std::string camera_type);

 private:
  std::string task_id_;
  std::string bin_code_;
  std::string camera_type_;
  unsigned short stream_type_;

  LONG lUserID;
  LONG lRealPlayHandle;

  static int times;
  static LONG m_lPort[16];  // 全局的播放库port号
  void getPic();

  // 静态回调函数
  static void CALLBACK DisplayCBFun(DISPLAY_INFO_YUV* pstDisplayInfo,
                                    void* pUser);
  static void CALLBACK DecCBFunIm(int nPort, char* pBuf, int nSize,
                                  FRAME_INFO* pFrameInfo, void* pUser,
                                  int nReserved2);
  static void CALLBACK g_RealDataCallBack_V30(LONG lRealHandle,
                                              DWORD dwDataType, BYTE* pBuffer,
                                              DWORD dwBufSize, void* pUser);

  // 真正的数据处理函数
  void HandleRealData(LONG lRealHandle, DWORD dwDataType, BYTE* pBuffer,
                      DWORD dwBufSize);

  void createDirectory(const std::string& path);
};