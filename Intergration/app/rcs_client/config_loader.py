'''
Author: big box big box@qq.com
Date: 2025-10-15 00:14:40
LastEditors: big box big box@qq.com
LastEditTime: 2025-10-15 00:18:20
FilePath: /rcs_client/config_loader.py
Description: 

Copyright (c) 2025 by lizh, All Rights Reserved. 
'''
import json
import os
from pathlib import Path

class ConfigLoader:
    """LMS 系统配置加载器"""
    
    def __init__(self, config_path="config.json"):
        """
        初始化配置加载器
        
        :param config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self):
        """加载并验证配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件 {self.config_path} 未找到")
        
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
            self._validate_config(config)
            return config
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件解析错误: {e}")
    
    def _validate_config(self, config):
        """验证配置结构"""
        required_sections = ["lms"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"配置文件缺少必要部分: {section}")
        
        # 验证 LMS 配置
        lms_required = ["base_url", "user_code", "password"]
        for key in lms_required:
            if key not in config["lms"]:
                raise ValueError(f"LMS 配置缺少必要字段: {key}")
    
    def get_lms_base_url(self):
        """获取 LMS 基础 URL"""
        return self.config["lms"]["base_url"]
    
    def get_user_code(self):
        """获取用户代码"""
        return self.config["lms"]["user_code"]
    
    def get_password(self):
        """获取密码（注意：生产环境应使用安全方式处理密码）"""
        return self.config["lms"]["password"]