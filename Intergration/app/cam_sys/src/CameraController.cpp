#include "CameraController.h"

#include <dirent.h>
#include <stdio.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#include <cstring>
#include <iostream>

CameraController::CameraController()
    : m_userId(-1), m_isConnected(false), m_isInitialized(false) {
  memset(&m_lastFoundPicture, 0, sizeof(m_lastFoundPicture));
}

CameraController::~CameraController() { cleanup(); }

bool CameraController::initialize() {
  if (m_isInitialized) {
    return true;
  }

  NET_DVR_Init();
  m_isInitialized = true;

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
  if (m_isConnected) {
    logout();
  }

  if (m_isInitialized) {
    NET_DVR_Cleanup();
    m_isInitialized = false;
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

  NET_DVR_FIND_PICTURE_V50 fileInfo = {0};
  int fileCount = doFindPicture(channel, startTime, endTime, fileInfo);

  if (fileCount > 0) {
    std::cout << "Found " << fileCount << " pictures. Downloading..."
              << std::endl;
    // 保存最后找到的图片信息
    m_lastFoundPicture = fileInfo;
    if (doGetPicture(fileInfo)) {
      std::cout << "Picture downloaded successfully" << std::endl;
    } else {
      std::cout << "Failed to download picture" << std::endl;
    }
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

int CameraController::doFindPicture(int channel,
                                    const LinuxSystemTime& startTime,
                                    const LinuxSystemTime& endTime,
                                    NET_DVR_FIND_PICTURE_V50& fileInfo) {
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
  NET_DVR_FIND_PICTURE_V50 fileInfoV50 = {0};

  while (keepFinding) {
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
  fileInfo = fileInfoV50;
  return fileCount;
}

bool CameraController::doGetPicture(const NET_DVR_FIND_PICTURE_V50& fileInfo) {
  NET_DVR_PIC_PARAM picParam = {0};
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