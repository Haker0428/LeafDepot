#include "CameraController.h"

void CALLBACK g_ExceptionCallBack(DWORD dwType, LONG lUserID, LONG lHandle,
                                  void* pUser) {
  char tempbuf[256] = {0};
  switch (dwType) {
    case EXCEPTION_RECONNECT:  // 预览时重连
      printf("----------reconnect--------\n");
      break;
    default:
      break;
  }
}

LONG m_playPort;  // 全局的播放库port号

void g_RealDataCallBack_V30(LONG lRealHandle, DWORD dwDataType, BYTE* pBuffer,
                            DWORD dwBufSize, void* dwUser) {
  // HWND hWnd = GetConsoleWindowAPI();

  switch (dwDataType) {
    case NET_DVR_SYSHEAD:  // 系统头
      if (m_playPort >= 0) {
        break;  // 该通道取流之前已经获取到句柄，后续接口不需要再调用
      }

      if (!PlayM4_GetPort(&m_playPort))  // 获取播放库未使用的通道号
      {
        break;
      }
      // m_iPort = m_playPort;
      // //第一次回调的是系统头，将获取的播放库port号赋值给全局port，下次回调数据时即使用此port号播放
      if (dwBufSize > 0) {
        if (!PlayM4_SetStreamOpenMode(m_playPort,
                                      STREAME_REALTIME))  // 设置实时流播放模式
        {
          break;
        }

        if (!PlayM4_OpenStream(m_playPort, pBuffer, dwBufSize,
                               1024 * 1024))  // 打开流接口
        {
          break;
        }

        if (!PlayM4_Play(m_playPort, NULL))  // 播放开始
        {
          break;
        }
      }
      break;
    case NET_DVR_STREAMDATA:  // 码流数据
      if (dwBufSize > 0 && m_playPort != -1) {
        if (!PlayM4_InputData(m_playPort, pBuffer, dwBufSize)) {
          break;
        }
      }
      break;
    default:  // 其他数据
      if (dwBufSize > 0 && m_playPort != -1) {
        if (!PlayM4_InputData(m_playPort, pBuffer, dwBufSize)) {
          break;
        }
      }
      break;
  }
}

CameraController::CameraController()
    : m_userId(-1),
      m_isConnected(false),
      m_isInitialized(false),
      m_isGetRealPlay(false),
      m_realPlayHandle(-1) {
  memset(&m_lastFoundPicture, 0, sizeof(m_lastFoundPicture));
  m_struPlayInfo = {0};
}

CameraController::~CameraController() { cleanup(); }

bool CameraController::initialize() {
  if (m_isInitialized) {
    return true;
  }

  NET_DVR_Init();
  m_isInitialized = true;

  // 设置异常消息回调函数
  NET_DVR_SetExceptionCallBack_V30(0, NULL, g_ExceptionCallBack, NULL);

  // 设置保存目录
  std::string exePath = getExecutablePath();
  m_saveDirectory = exePath + "/../saved_images";

  if (!createDirectory(m_saveDirectory)) {
    setLastError("Failed to create save directory: " + m_saveDirectory);
    return false;
  }

  std::cout << "Camera controller initialized. Save directory: "
            << m_saveDirectory << std::endl;
  return true;
}

void CameraController::cleanup() {
  stopRealPlay();

  // 释放播放库资源
  PlayM4_Stop(m_playPort);
  PlayM4_CloseStream(m_playPort);
  PlayM4_FreePort(m_playPort);

  logout();

  if (m_isInitialized) {
    NET_DVR_Cleanup();
    m_isInitialized = false;
  }
}

void CameraController::stopRealPlay() {
  if (m_isGetRealPlay && m_realPlayHandle >= 0) {
    NET_DVR_StopRealPlay(m_realPlayHandle);
    m_realPlayHandle = -1;
    m_isGetRealPlay = false;
    std::cout << "Stop Real Play" << std::endl;
  }
}

bool CameraController::login(const std::string& deviceAddress,
                             unsigned short port, const std::string& userName,
                             const std::string& password) {
  if (!m_isInitialized && !initialize()) {
    setLastError("SDK not initialized");
    return false;
  }

  if (m_isConnected) {
    logout();
  }

  // 设置登录参数
  NET_DVR_USER_LOGIN_INFO loginInfo = {0};
  loginInfo.bUseAsynLogin = 0;
  strncpy(loginInfo.sDeviceAddress, deviceAddress.c_str(),
          sizeof(loginInfo.sDeviceAddress));
  loginInfo.wPort = port;
  strncpy(loginInfo.sUserName, userName.c_str(), sizeof(loginInfo.sUserName));
  strncpy(loginInfo.sPassword, password.c_str(), sizeof(loginInfo.sPassword));

  NET_DVR_DEVICEINFO_V40 deviceInfo = {0};

  m_userId = NET_DVR_Login_V40(&loginInfo, &deviceInfo);
  if (m_userId < 0) {
    setLastError("Login failed, error code: " +
                 std::to_string(NET_DVR_GetLastError()));
    m_isConnected = false;
    return false;
  }

  m_isConnected = true;
  std::cout << "Successfully connected to device: " << deviceAddress
            << std::endl;

  // 时间同步
  NET_DVR_TIME current_time_cam = getLocalTime2Cam();
  sync_time(current_time_cam);

  return true;
}

void CameraController::logout() {
  if (m_isConnected && m_userId >= 0) {
    NET_DVR_Logout(m_userId);
    m_userId = -1;
    m_isConnected = false;
    std::cout << "Logged out from device" << std::endl;
  }
}

int CameraController::findPictures(int channel) {
  // 使用当前时间作为默认查找范围（当天）
  LinuxSystemTime currentTime = getLocalTime();
  LinuxSystemTime startTime(currentTime.year, currentTime.month,
                            currentTime.day, 0, 0, 0);
  LinuxSystemTime endTime(currentTime.year, currentTime.month, currentTime.day,
                          23, 59, 59);

  return findPictures(channel, startTime, endTime);
}

int CameraController::findPictures(int channel,
                                   const LinuxSystemTime& startTime,
                                   const LinuxSystemTime& endTime) {
  if (!isConnected()) {
    setLastError("Not connected to any device");
    return 0;
  }

  std::vector<NET_DVR_FIND_PICTURE_V50> foundPictures;
  int fileCount = doFindPicture(channel, startTime, endTime, foundPictures);

  if (fileCount > 0) {
    std::cout << "Found " << fileCount << " pictures. Downloading..."
              << std::endl;

    int successCount = 0;
    for (const auto& picture : foundPictures) {
      if (doGetPicture(picture)) {
        successCount++;
        std::cout << "Picture downloaded successfully: " << picture.sFileName
                  << std::endl;
      } else {
        std::cout << "Failed to download picture: " << picture.sFileName
                  << std::endl;
      }
    }

    // 保存最后找到的图片信息
    if (!foundPictures.empty()) {
      m_lastFoundPicture = foundPictures.back();
    }

    std::cout << "Download completed: " << successCount << "/" << fileCount
              << " pictures downloaded successfully" << std::endl;
  }

  return fileCount;
}

bool CameraController::downloadPicture(
    const NET_DVR_FIND_PICTURE_V50& fileInfo) {
  if (!isConnected()) {
    setLastError("Not connected to any device");
    return false;
  }
  return doGetPicture(fileInfo);
}

// 私有方法实现
LinuxSystemTime CameraController::getLocalTime() {
  time_t rawTime;
  struct tm* timeInfo;
  time(&rawTime);
  timeInfo = localtime(&rawTime);

  LinuxSystemTime sysTime;
  sysTime.year = timeInfo->tm_year + 1900;
  sysTime.month = timeInfo->tm_mon + 1;
  sysTime.day = timeInfo->tm_mday;
  sysTime.hour = timeInfo->tm_hour;
  sysTime.minute = timeInfo->tm_min;
  sysTime.second = timeInfo->tm_sec;

  return sysTime;
}

NET_DVR_TIME CameraController::getLocalTime2Cam() {
  time_t rawTime;
  struct tm* timeInfo;
  time(&rawTime);
  timeInfo = localtime(&rawTime);

  NET_DVR_TIME sysTime;
  sysTime.dwYear = timeInfo->tm_year + 1900;
  sysTime.dwMonth = timeInfo->tm_mon + 1;
  sysTime.dwDay = timeInfo->tm_mday;
  sysTime.dwHour = timeInfo->tm_hour;
  sysTime.dwMinute = timeInfo->tm_min;
  sysTime.dwSecond = timeInfo->tm_sec;

  return sysTime;
}

int CameraController::sync_time(NET_DVR_TIME current_time) {
  LPVOID lpOutBuffer;
  LPDWORD lpBytesReturned;
  if (!NET_DVR_GetDVRConfig(m_userId, NET_DVR_GET_TIMECFG, 0xFFFFFFFF,
                            lpOutBuffer, 1024, lpBytesReturned)) {
    int error_code = NET_DVR_GetLastError();
    std::cerr << "get time config error, error_code: " << error_code
              << std::endl;
  };

  if (!NET_DVR_SetDVRConfig(m_userId, NET_DVR_SET_TIMECFG, 0xFFFFFFFF,
                            lpOutBuffer, 1024)) {
    int error_code = NET_DVR_GetLastError();
    std::cerr << "sync time config error, error_code: " << error_code
              << std::endl;
  };
}

bool CameraController::createDirectory(const std::string& path) {
  struct stat st;
  if (stat(path.c_str(), &st) == 0) {
    if (S_ISDIR(st.st_mode)) {
      return true;
    }
  }
  return mkdir(path.c_str(), 0755) == 0;
}

std::string CameraController::getExecutablePath() {
  char exePath[1024] = {0};
  ssize_t count = readlink("/proc/self/exe", exePath, sizeof(exePath) - 1);
  if (count != -1) {
    exePath[count] = '\0';
    char* lastSlash = strrchr(exePath, '/');
    if (lastSlash != NULL) {
      *lastSlash = '\0';
      return std::string(exePath);
    }
  }
  return ".";
}

void CameraController::setLastError(const std::string& error) {
  m_lastError = error;
  std::cerr << "Error: " << error << std::endl;
}

void CameraController::convertToNetDvrTime(const LinuxSystemTime& src,
                                           NET_DVR_TIME& dst) {
  dst.dwYear = src.year;
  dst.dwMonth = src.month;
  dst.dwDay = src.day;
  dst.dwHour = src.hour;
  dst.dwMinute = src.minute;
  dst.dwSecond = src.second;
}

int CameraController::doFindPicture(
    int channel, const LinuxSystemTime& startTime,
    const LinuxSystemTime& endTime,
    std::vector<NET_DVR_FIND_PICTURE_V50>& foundPictures) {
  int fileCount = 0;

  NET_DVR_FIND_PICTURE_PARAM findParam = {0};
  findParam.dwSize = sizeof(findParam);
  findParam.lChannel = channel;
  findParam.byFileType = 0xff;

  // 使用传入的时间参数设置查找范围
  convertToNetDvrTime(startTime, findParam.struStartTime);
  convertToNetDvrTime(endTime, findParam.struStopTime);

  LONG findHandle = NET_DVR_FindPicture(m_userId, &findParam);
  if (findHandle < 0) {
    setLastError("NET_DVR_FindPicture failed, error code: " +
                 std::to_string(NET_DVR_GetLastError()));
    return 0;
  }

  bool keepFinding = true;
  LONG result = -1;
  foundPictures.clear();

  while (keepFinding) {
    NET_DVR_FIND_PICTURE_V50 fileInfoV50 = {0};
    result = NET_DVR_FindNextPicture_V50(findHandle, &fileInfoV50);

    switch (result) {
      case -1:
        setLastError("NET_DVR_FindNextPicture_V50 failed, error code: " +
                     std::to_string(NET_DVR_GetLastError()));
        keepFinding = false;
        break;
      case 1000:
        std::cout << "Picture FileName: " << fileInfoV50.sFileName
                  << ", Time: " << fileInfoV50.struTime.dwYear << "-"
                  << fileInfoV50.struTime.dwMonth << "-"
                  << fileInfoV50.struTime.dwDay << " "
                  << fileInfoV50.struTime.dwHour << ":"
                  << fileInfoV50.struTime.dwMinute << ":"
                  << fileInfoV50.struTime.dwSecond
                  << ", FileSize: " << fileInfoV50.dwFileSize << std::endl;
        fileCount++;
        // 保存找到的图片信息到向量中
        foundPictures.push_back(fileInfoV50);
        continue;
      case 1002:
        usleep(5000);
        continue;
      case 1001:
        std::cout << "No picture found!" << std::endl;
        keepFinding = false;
        break;
      case 1003:
        std::cout << "Search completed, no more files!" << std::endl;
        keepFinding = false;
        break;
      case 1004:
        setLastError("Exception during picture search");
        keepFinding = false;
        break;
    }
  }

  if (!NET_DVR_CloseFindPicture(findHandle)) {
    setLastError("NET_DVR_CloseFindPicture failed, error code: " +
                 std::to_string(NET_DVR_GetLastError()));
  }

  std::cout << "Total number of pictures: " << fileCount << std::endl;
  return fileCount;
}

bool CameraController::doGetPicture(const NET_DVR_FIND_PICTURE_V50& fileInfo) {
  NET_DVR_PIC_PARAM picParam = {0};
  // picParam.dwSize = sizeof(picParam);
  picParam.pDVRFileName = const_cast<char*>(fileInfo.sFileName);
  picParam.dwBufLen = fileInfo.dwFileSize;

  DWORD retLen = 0;
  picParam.lpdwRetLen = &retLen;
  picParam.pSavedFileBuf = new char[fileInfo.dwFileSize];
  memset(picParam.pSavedFileBuf, 0, fileInfo.dwFileSize);

  bool success = false;

  if (!NET_DVR_GetPicture_V50(m_userId, &picParam)) {
    setLastError("NET_DVR_GetPicture_V50 failed, error code: " +
                 std::to_string(NET_DVR_GetLastError()));
  } else {
    std::string filename = m_saveDirectory + "/" + fileInfo.sFileName + ".jpg";
    FILE* file = fopen(filename.c_str(), "wb");
    if (file) {
      fwrite(picParam.pSavedFileBuf, retLen, 1, file);
      fclose(file);
      std::cout << "Picture saved to: " << filename << std::endl;
      success = true;
    } else {
      setLastError("Failed to open file for writing: " + filename);
    }
  }

  delete[] picParam.pSavedFileBuf;
  return success;
}

int CameraController::getRealPlay(int channel, int streamType, int linkMode,
                                  int blocked) {
  m_struPlayInfo.hPlayWnd =
      NULL;  // 需要SDK解码时句柄设为有效值，仅取流不解码时可设为空
  m_struPlayInfo.lChannel = channel;  // 预览通道号
  m_struPlayInfo.dwStreamType =
      streamType;  // 0-主码流，1-子码流，2-码流3，3-码流4，以此类推
  m_struPlayInfo.dwLinkMode =
      linkMode;                       // 0- TCP方式，1- UDP方式，2- 多播方式，3-
                                      // RTP方式，4-RTP/RTSP，5-RSTP/HTTP
  m_struPlayInfo.bBlocked = blocked;  // 0- 非阻塞取流，1- 阻塞取流

  m_realPlayHandle = NET_DVR_RealPlay_V40(m_userId, &m_struPlayInfo,
                                          g_RealDataCallBack_V30, NULL);

  if (m_realPlayHandle < 0) {
    printf("NET_DVR_RealPlay_V40 error\n");
    cleanup();
    return -1;
  }

  return 0;
}

int CameraController::doGetCapturePicture() {
  // 3. 获取 BMP 数据大小

  DWORD dwBmpSize = 0;

  if (!PlayM4_GetBMP(m_playPort, NULL, 0, &dwBmpSize)) {
    printf("Failed to get BMP size\n");

    return -1;
  }

  // 4. 分配缓冲区并获取 BMP 数据

  BYTE* pBmpData = new BYTE[dwBmpSize];

  if (!pBmpData) {
    printf("Memory allocation failed\n");

    return -1;
  }

  if (!PlayM4_GetBMP(m_playPort, pBmpData, dwBmpSize, &dwBmpSize)) {
    printf("PlayM4_GetBMP failed\n");

    delete[] pBmpData;

    return -1;
  }

  // 5. 保存 BMP 文件

  char filename[256];

  time_t now = time(0);

  struct tm* tm = localtime(&now);

  strftime(filename, sizeof(filename), "capture_%Y%m%d_%H%M%S.bmp", tm);

  FILE* pFile = fopen(filename, "wb");

  if (pFile) {
    fwrite(pBmpData, 1, dwBmpSize, pFile);

    fclose(pFile);

    printf("BMP image saved to %s\n", filename);

  } else {
    printf("Failed to create file %s\n", filename);
  }

  // 6. 清理

  delete[] pBmpData;

  return 0;
}
