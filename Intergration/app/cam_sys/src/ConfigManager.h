/*
 * @Author: big box big box@qq.com
 * @Date: 2025-11-13
 * @Description: 配置文件管理类
 */
#ifndef CONFIG_MANAGER_H
#define CONFIG_MANAGER_H

#include <fstream>
#include <nlohmann/json.hpp>
#include <string>

using json = nlohmann::json;

class ConfigManager {
 public:
  ConfigManager(const std::string& configFile = "config.json");

  bool loadConfig();
  bool saveConfig();

  // Camera 配置
  std::string getCameraIP() const;
  int getCameraPort() const;
  std::string getCameraUsername() const;
  std::string getCameraPassword() const;
  int getCameraChannel() const;
  int getStreamType() const;
  int getConnectionType() const;
  int getStreamMode() const;

  // Search 配置
  int getPictureSearchSeconds() const;

  // 设置方法（可选）
  void setCameraIP(const std::string& ip);
  void setCameraPort(int port);
  void setCameraCredentials(const std::string& username,
                            const std::string& password);

  // 错误信息
  std::string getLastError() const;

 private:
  std::string configFile_;
  json config_;
  std::string lastError_;

  // 默认配置
  void setDefaultConfig();
};

#endif  // CONFIG_MANAGER_H