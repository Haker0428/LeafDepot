/*
 * @Author: big box big box@qq.com
 * @Date: 2025-11-13
 * @Description: 配置文件管理类实现
 */
#include "ConfigManager.h"

#include <iostream>

ConfigManager::ConfigManager(const std::string& configFile)
    : configFile_(configFile) {
  setDefaultConfig();
}

bool ConfigManager::loadConfig() {
  try {
    std::ifstream file(configFile_);
    if (!file.is_open()) {
      lastError_ = "Cannot open config file: " + configFile_;
      return false;
    }

    file >> config_;
    file.close();

    std::cout << "Configuration loaded successfully from: " << configFile_
              << std::endl;
    return true;

  } catch (const std::exception& e) {
    lastError_ = "Error parsing config file: ";
    lastError_ += e.what();
    return false;
  }
}

bool ConfigManager::saveConfig() {
  try {
    std::ofstream file(configFile_);
    if (!file.is_open()) {
      lastError_ = "Cannot create config file: " + configFile_;
      return false;
    }

    file << config_.dump(4);  // 缩进4个空格，美化输出
    file.close();

    std::cout << "Configuration saved successfully to: " << configFile_
              << std::endl;
    return true;

  } catch (const std::exception& e) {
    lastError_ = "Error saving config file: ";
    lastError_ += e.what();
    return false;
  }
}

void ConfigManager::setDefaultConfig() {
  config_ = {{"camera",
              {{"ip", "192.168.1.64"},
               {"port", 8000},
               {"username", "admin"},
               {"password", "leafdepot2025"},
               {"channel", 1},
               {"stream_type", 0},
               {"connection_type", 1},
               {"stream_mode", 0}}},
             {"search", {{"picture_search_seconds", 30}}}};
}

// Getter 方法实现
std::string ConfigManager::getCameraIP() const {
  return config_["camera"]["ip"];
}

int ConfigManager::getCameraPort() const { return config_["camera"]["port"]; }

std::string ConfigManager::getCameraUsername() const {
  return config_["camera"]["username"];
}

std::string ConfigManager::getCameraPassword() const {
  return config_["camera"]["password"];
}

int ConfigManager::getCameraChannel() const {
  return config_["camera"]["channel"];
}

int ConfigManager::getStreamType() const {
  return config_["camera"]["stream_type"];
}

int ConfigManager::getConnectionType() const {
  return config_["camera"]["connection_type"];
}

int ConfigManager::getStreamMode() const {
  return config_["camera"]["stream_mode"];
}

int ConfigManager::getPictureSearchSeconds() const {
  return config_["search"]["picture_search_seconds"];
}

// Setter 方法实现
void ConfigManager::setCameraIP(const std::string& ip) {
  config_["camera"]["ip"] = ip;
}

void ConfigManager::setCameraPort(int port) {
  config_["camera"]["port"] = port;
}

void ConfigManager::setCameraCredentials(const std::string& username,
                                         const std::string& password) {
  config_["camera"]["username"] = username;
  config_["camera"]["password"] = password;
}

std::string ConfigManager::getLastError() const { return lastError_; }