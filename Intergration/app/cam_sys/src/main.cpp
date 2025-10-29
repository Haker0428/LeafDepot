#include <iostream>

#include "CameraController.h"

int main() {
  CameraController camera;

  // 初始化相机控制器
  if (!camera.initialize()) {
    std::cerr << "Failed to initialize camera controller: "
              << camera.getLastError() << std::endl;
    return -1;
  }

  // 连接到设备
  if (!camera.login("10.17.34.28", 8000, "admin", "abc12345")) {
    std::cerr << "Login failed: " << camera.getLastError() << std::endl;
    return -1;
  }

  std::cout << "=== Camera Controller Demo ===" << std::endl;

  int channel = 3;

  // 方法1：使用默认时间范围（当天）
  std::cout << "\n1. Searching pictures with default time range (today)..."
            << std::endl;
  int pictureCount1 = camera.findPictures(channel);

  if (pictureCount1 == 0) {
    std::cout << "No pictures found on channel " << channel
              << " with default time range." << std::endl;

    // 方法2：使用指定时间范围（示例：前一天）
    std::cout << "\n2. Trying with custom time range (previous day)..."
              << std::endl;

    // 获取当前时间
    LinuxSystemTime currentTime = camera.getLocalTime();

    // 设置前一天的时间范围
    LinuxSystemTime startTime(currentTime.year, currentTime.month,
                              currentTime.day - 1, 0, 0, 0);
    LinuxSystemTime endTime(currentTime.year, currentTime.month,
                            currentTime.day - 1, 23, 59, 59);

    int pictureCount2 = camera.findPictures(channel, startTime, endTime);

    if (pictureCount2 == 0) {
      std::cout << "No pictures found on channel " << channel
                << " with custom time range either." << std::endl;
    }
  } else {
    std::cout << "Successfully found and downloaded " << pictureCount1
              << " pictures." << std::endl;
  }

  // 方法3：直接使用硬编码的时间范围
  std::cout << "\n3. Searching with hardcoded time range..." << std::endl;
  LinuxSystemTime customStart(2024, 1, 1, 0, 0, 0);
  LinuxSystemTime customEnd(2024, 12, 31, 23, 59, 59);
  int pictureCount3 = camera.findPictures(channel, customStart, customEnd);

  if (pictureCount3 > 0) {
    std::cout << "Found " << pictureCount3 << " pictures in custom time range."
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