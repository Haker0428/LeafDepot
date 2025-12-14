/*
 * @Author: lizh 447628890@qq.com
 * @Date: 2025-12-10 17:45:34
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2025-12-11 22:02:22
 * @FilePath: /cam_sys_3/src/CamController.cpp
 * @Description:
 *
 * Copyright (c) 2025 by lizh, All Rights Reserved.
 */
#include "CamController.h"

// 全局的播放库port号 - 现在作为CamController的静态成员变量
LONG CamController::m_lPort[16] = {-1, -1, -1, -1, -1, -1, -1, -1,
                                   -1, -1, -1, -1, -1, -1, -1, -1};

// 静态成员变量初始化
int CamController::times = 0;

/// 播放库硬解码回调 - 改为静态成员函数
void CALLBACK CamController::DisplayCBFun(DISPLAY_INFO_YUV* pstDisplayInfo,
                                          void* pUser) {
  CamController* pThis = static_cast<CamController*>(pUser);
  if (pThis) {
    if (pThis->times % 100 == 0) {
      FILE* fp = NULL;
      std::string ansiString = "example" +
                               std::to_string(pstDisplayInfo->nPort) + "___" +
                               std::to_string(pThis->times / 100) + ".yuv";
      fp = fopen(ansiString.c_str(), "wb");
      if (fp) {
        fwrite(pstDisplayInfo->pBuf, sizeof(char), pstDisplayInfo->nBufLen, fp);
        fclose(fp);
      }
    }
    pThis->times++;
    printf("Buf长度:%d\n画面宽:%d\n画面高:%d\n数据类型:%d\nn播放库句柄:%d\n",
           pstDisplayInfo->nBufLen, pstDisplayInfo->nWidth,
           pstDisplayInfo->nHeight, pstDisplayInfo->nType,
           pstDisplayInfo->nPort);
  }
}

// 播放库解码回调 - 改为静态成员函数
void CALLBACK CamController::DecCBFunIm(int nPort, char* pBuf, int nSize,
                                        FRAME_INFO* pFrameInfo, void* nUser,
                                        int nReserved2) {
  // 注意：回调函数中的nUser是char*类型，我们需要将它转换回CamController*
  CamController* pThis = reinterpret_cast<CamController*>(nUser);
  if (pThis) {
    printf("字节数据大小：%d\n", nSize);
    printf("相对时间戳：%d\n", pFrameInfo->nStamp);

    // 每100次回调保存一次数据
    if (pThis->times % 100 == 0) {
      // 注意：这里需要正确构造文件名
      std::string ansiString = "example" + std::to_string(pFrameInfo->nStamp) +
                               "___" + std::to_string(pThis->times / 100) +
                               ".jpg";

      // 确保字符串以null结尾
      ansiString.push_back('\0');

      PlayM4_ConvertToJpegFile(pBuf, nSize, pFrameInfo->nWidth,
                               pFrameInfo->nHeight, pFrameInfo->nType,
                               const_cast<char*>(ansiString.c_str()));

      std::string ansiStrings = "example" + std::to_string(pFrameInfo->nStamp) +
                                "___" + std::to_string(pThis->times / 100) +
                                ".bmp";
      ansiStrings.push_back('\0');
      PlayM4_ConvertToBmpFile(pBuf, nSize, pFrameInfo->nWidth,
                              pFrameInfo->nHeight, pFrameInfo->nType,
                              const_cast<char*>(ansiStrings.c_str()));
    }
    pThis->times++;
  }
}

// sdk码流回调 - 改为静态成员函数
void CALLBACK CamController::g_RealDataCallBack_V30(LONG lRealHandle,
                                                    DWORD dwDataType,
                                                    BYTE* pBuffer,
                                                    DWORD dwBufSize,
                                                    void* pUser) {
  CamController* pThis = static_cast<CamController*>(pUser);
  if (pThis) {
    pThis->HandleRealData(lRealHandle, dwDataType, pBuffer, dwBufSize);
  }
}

// 真正的数据处理函数 - 非静态成员函数，可以访问成员变量
void CamController::HandleRealData(LONG lRealHandle, DWORD dwDataType,
                                   BYTE* pBuffer, DWORD dwBufSize) {
  DWORD dRet = 0;
  BOOL inData = FALSE;
  LONG lPort = -1;

  switch (dwDataType) {
    case NET_DVR_SYSHEAD:  // 系统头
      if (!PlayM4_GetPort(&lPort)) {
        printf("申请播放库资源失败");
        break;
      }
      printf("播放库句柄：%d\n", lPort);

      // 使用成员变量lRealPlayHandle
      m_lPort[lRealPlayHandle] = lPort;

      if (dwBufSize > 0) {
        // 使用成员变量
        if (!PlayM4_SetStreamOpenMode(m_lPort[lRealPlayHandle],
                                      STREAME_REALTIME)) {
          printf("PlayM4_SetStreamOpenMode Error\n");
          printf("GetLastError错误码 :%d\n",
                 PlayM4_GetLastError(m_lPort[lRealPlayHandle]));
          break;
        } else {
          printf("PlayM4_SetStreamOpenMode Sus!\n");
        }

        if (!PlayM4_OpenStream(m_lPort[lRealPlayHandle], pBuffer, dwBufSize,
                               5 * 1024 * 1024)) {
          printf("PlayM4_OpenStream Error\n");
          printf("GetLastError错误码 :%d\n",
                 PlayM4_GetLastError(m_lPort[lRealPlayHandle]));
          break;
        } else {
          printf("PlayM4_OpenStream Sus!\n");
        }

        // 设置解码回调函数，传递this指针
        if (!PlayM4_SetDecCallBackExMend(m_lPort[lRealPlayHandle], DecCBFunIm,
                                         reinterpret_cast<char*>(this), 0,
                                         NULL)) {
          printf("PlayM4_SetDecCallBackExMend Error\n");
          printf("GetLastError错误码 :%d\n",
                 PlayM4_GetLastError(m_lPort[lRealPlayHandle]));
          break;
        } else {
          printf("PlayM4_SetDecodeEngine Sus!\n");
        }

        if (!PlayM4_Play(m_lPort[lRealPlayHandle], NULL)) {
          printf("PlayM4_Play Error\n");
          printf("GetLastError错误码 :%d\n",
                 PlayM4_GetLastError(m_lPort[lRealPlayHandle]));
          break;
        } else {
          printf("PlayM4_Play Sus!\n");
        }
      }
      break;

    case NET_DVR_STREAMDATA:  // 码流数据
      if (dwBufSize > 0 && m_lPort[lRealPlayHandle] != -1) {
        while (
            !PlayM4_InputData(m_lPort[lRealPlayHandle], pBuffer, dwBufSize)) {
          int dwError = PlayM4_GetLastError(m_lPort[lRealPlayHandle]);
          printf("播放库句柄ID：%d,错误码：%d\n", m_lPort[lRealPlayHandle],
                 dwError);
          if (dwError == 11) {
            continue;
          }
          break;
        }
      }
      break;

    default:  // 其他数据
      if (dwBufSize > 0 && m_lPort[lRealPlayHandle] != -1) {
        if (!PlayM4_InputData(m_lPort[lRealPlayHandle], pBuffer, dwBufSize)) {
          break;
        }
      }
      break;
  }
}

void CamController::getPic() {
  int i = 0;
  BOOL bFlag = FALSE;
  DWORD dwErr = 0;
  LONG dwWidth = 0;
  LONG dwHeight = 0;
  DWORD dwSize = 0;
  DWORD dwCapSize = 0;

  // 首先检查必要的成员变量是否已设置
  if (task_id_.empty() || bin_code_.empty() || camera_type_.empty()) {
    printf("错误: task_id_, bin_code_ 或 camera_type_ 未设置!\n");
    return;
  }

  // 构建基础路径
  std::string basePath = "output/" +task_id_ + "/" + bin_code_ + "/" + camera_type_;

  // 创建目录（如果不存在）
  createDirectory(basePath);

  // 根据 stream_type_ 确定文件名
  std::string fileName;
  if (stream_type_ == 0) {
    fileName = "main.jpg";
  } else if (stream_type_ == 3) {
    fileName = "depth.jpg";
  } else {
    printf("未知的 stream_type_: %d，使用默认文件名\n", stream_type_);
    fileName = "default.jpg";
  }

  // 抓10张图（可以根据需要调整次数）
  while (i++ < 1) {
    // 获取当前视频文件的分辨率
    bFlag =
        PlayM4_GetPictureSize(m_lPort[lRealPlayHandle], &dwWidth, &dwHeight);
    if (bFlag == FALSE) {
      dwErr = PlayM4_GetLastError(m_lPort[lRealPlayHandle]);
      printf("PlayM4_GetPictureSize, error code: %d\n", dwErr);
      break;
    }

    // 计算图片大小（根据YUV420格式，宽度*高度*1.5）
    dwSize = dwWidth * dwHeight * 3 / 2;

    // 申请抓图内存
    BYTE* m_pCapBuf = new BYTE[dwSize];
    if (m_pCapBuf == NULL) {
      printf("无法分配内存!\n");
      return;
    }

    // 抓图
    bFlag =
        PlayM4_GetJPEG(m_lPort[lRealPlayHandle], m_pCapBuf, dwSize, &dwCapSize);
    if (bFlag == FALSE) {
      dwErr = PlayM4_GetLastError(m_lPort[lRealPlayHandle]);
      printf("PlayM4_GetJPEG, error code: %d\n", dwErr);
      delete[] m_pCapBuf;
      break;
    }

    if (bFlag) {
      // 构建完整文件路径
      std::string filePath = basePath + "/" + fileName;

      FILE* fp = fopen(filePath.c_str(), "wb");
      if (fp) {
        fwrite(m_pCapBuf, sizeof(char), dwCapSize, fp);
        fclose(fp);
        printf("抓图保存到: %s\n", filePath.c_str());
      } else {
        printf("无法打开文件: %s\n", filePath.c_str());
      }
    }

    if (m_pCapBuf != NULL) {
      delete[] m_pCapBuf;
      m_pCapBuf = NULL;
    }
    printf("完成第%d张抓图\n", i);
    // 等待1秒后进入下一次抓图
    sleep(1);
  }
}

// 辅助函数：创建目录
void CamController::createDirectory(const std::string& path) {
  std::string command = "mkdir -p " + path;
  int result = system(command.c_str());
  if (result != 0) {
    printf("警告: 创建目录失败: %s\n", path.c_str());
  } else {
    printf("目录已创建/存在: %s\n", path.c_str());
  }
}

CamController::CamController() {
  // 初始化
  NET_DVR_Init();
  char ansiStringss[] = "./sdkLog";
  NET_DVR_SetLogToFile(3, ansiStringss, TRUE);
  // 设置连接时间与重连时间
  NET_DVR_SetConnectTime(2000, 1);
  NET_DVR_SetReconnect(10000, true);
}

CamController::~CamController() {
  if (lRealPlayHandle >= 0) {
    // 关闭预览
    NET_DVR_StopRealPlay(lRealPlayHandle);
    // 释放播放库资源
    PlayM4_Stop(m_lPort[lRealPlayHandle]);
    // 关闭流
    PlayM4_CloseStream(m_lPort[lRealPlayHandle]);
    // 释放播放端口
    PlayM4_FreePort(m_lPort[lRealPlayHandle]);
  }

  if (lUserID >= 0) {
    // 退出登录
    NET_DVR_Logout(lUserID);
    // 释放sdk资源
    NET_DVR_Cleanup();
  }
}

bool CamController::login(const std::string& deviceAddress, unsigned short port,
                          const std::string& userName,
                          const std::string& password) {
  // 登录参数，包括设备地址、登录用户、密码等
  NET_DVR_USER_LOGIN_INFO struLoginInfo = {0};
  struLoginInfo.bUseAsynLogin = 0;  // 同步登录方式
  memcpy(struLoginInfo.sDeviceAddress, deviceAddress.c_str(),
         NAME_LEN);            // 设备IP地址
  struLoginInfo.wPort = port;  // 设备服务端口
  // struLoginInfo.sUserName = ini.readstring(sSection, "username", "error",
  // dwSize); //设备登录用户名
  memcpy(struLoginInfo.sUserName, userName.c_str(), NAME_LEN);
  // struLoginInfo.sPassword = ini.readstring(sSection, "password", "error",
  // dwSize); //设备登录密码
  memcpy(struLoginInfo.sPassword, password.c_str(), NAME_LEN);

  // 设备信息, 输出参数
  NET_DVR_DEVICEINFO_V40 struDeviceInfoV40 = {0};
  // 登录
  lUserID = NET_DVR_Login_V40(&struLoginInfo, &struDeviceInfoV40);
  if (lUserID < 0) {
    printf("Login failed, error code: %d\n", NET_DVR_GetLastError());
    NET_DVR_Cleanup();
    return false;
  }

  return true;
}

bool CamController::logout() {
  if (lRealPlayHandle >= 0) {
    // 关闭预览
    NET_DVR_StopRealPlay(lRealPlayHandle);
    // 释放播放库资源
    PlayM4_Stop(m_lPort[lRealPlayHandle]);
    // 关闭流
    PlayM4_CloseStream(m_lPort[lRealPlayHandle]);
    // 释放播放端口
    PlayM4_FreePort(m_lPort[lRealPlayHandle]);
  }

  // 退出登录
  NET_DVR_Logout(lUserID);
  // 释放sdk资源
  NET_DVR_Cleanup();

  return true;
}

bool CamController::startRealPlay(unsigned short channel,
                                  unsigned short stream_type,
                                  unsigned short linkMode,
                                  unsigned short blocked) {
  stream_type_ = stream_type;
  NET_DVR_PREVIEWINFO struPlayInfo = {0};
  struPlayInfo.hPlayWnd =
      NULL;  // 需要SDK解码时句柄设为有效值，仅取流不解码时可设为空
  struPlayInfo.lChannel = channel;  // 预览通道号
  struPlayInfo.dwStreamType =
      stream_type;  // 0-主码流，1-子码流，2-码流3，3-码流4，以此类推
  struPlayInfo.dwLinkMode =
      linkMode;                     // 0- TCP方式，1- UDP方式，2- 多播方式，3-
                                    // RTP方式，4-RTP/RTSP，5-RSTP/HTTP
  struPlayInfo.bBlocked = blocked;  // 0- 非阻塞取流，1- 阻塞取流

  // 启动预览并设置回调数据流
  lRealPlayHandle = NET_DVR_RealPlay_V40(
      lUserID, &struPlayInfo, g_RealDataCallBack_V30, this);  // 传递this

  if (lRealPlayHandle < 0) {
    printf("NET_DVR_RealPlay_V40 error %d\n", NET_DVR_GetLastError());
    NET_DVR_Logout(lUserID);
    NET_DVR_Cleanup();
    return false;
  }
  // 等待播放库有数据，否则后面无法使用播放库抓图
  sleep(3);

  return true;
}

bool CamController::stopRealPlay() {
  NET_DVR_StopRealPlay(lRealPlayHandle);
  // 释放播放库资源
  PlayM4_Stop(m_lPort[lRealPlayHandle]);
  // 关闭流
  PlayM4_CloseStream(m_lPort[lRealPlayHandle]);
  // 释放播放端口
  PlayM4_FreePort(m_lPort[lRealPlayHandle]);

  return true;
}

void CamController::getCapture() {
  // 创建并启动抓图线程
  std::thread t1(&CamController::getPic, this);

  // 播放库抓图分离线程
  t1.detach();

  // 等待继续预览秒
  sleep(3);
}

void CamController::setCameraType(std::string camera_type) {
  camera_type_ = camera_type;
}

void CamController::setTaskInfo(std::string task_id, std::string bin_code) {
  task_id_ = task_id;
  bin_code_ = bin_code;
}
