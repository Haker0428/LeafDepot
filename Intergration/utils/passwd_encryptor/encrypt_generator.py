'''
Author: big box big box@qq.com
Date: 2025-10-15 00:29:36
LastEditors: big box big box@qq.com
LastEditTime: 2025-10-15 00:33:04
FilePath: /Intergration/utils/passwd_encryptor/encrypt_generator.py
Description: 

Copyright (c) 2025 by lizh, All Rights Reserved. 
'''
import json
import os
import hashlib
from cryptography.fernet import Fernet
import base64

original_password = None


def generate_encryption_key():
    """生成安全的加密密钥（使用用户输入的密码）"""
    while True:
        password = input("请输入密码（用于加密）: ")
        confirm_password = input("请确认密码: ")

        if password != confirm_password:
            print("错误：两次输入的密码不匹配！请重新输入。")
            continue

        original_password = confirm_password

        # 使用SHA-256哈希生成32字节密钥（Fernet要求）
        key = hashlib.sha256(original_password.encode()).digest()
        return key


def encrypt_password(password, key):
    """加密密码"""
    cipher = Fernet(key)
    encrypted_password = cipher.encrypt(password.encode())
    return encrypted_password


def save_config(encrypted_password, key):
    """保存加密配置到JSON文件"""
    # 将密钥转换为base64字符串（安全存储）
    key_b64 = base64.urlsafe_b64encode(key).decode()

    config = {
        "encryption_key": key_b64,
        "encrypted_password": encrypted_password.decode()
    }

    with open("encrypted_password.json", "w") as f:
        json.dump(config, f, indent=2)

    print("\n配置文件已生成！")
    print("请将以下密钥安全保存（用于解密）:")
    print(f"加密密钥: {key_b64}")
    print("\n注意：此密钥是唯一解密密钥，丢失将无法恢复密码！")


def main():
    print("=== LMS 密码加密配置生成器 ===")
    print("请设置用于加密的密码（两次确认）\n")

    # 生成加密密钥
    key = generate_encryption_key()

    # 加密密码
    encrypted_password = encrypt_password(original_password, key)

    # 保存配置
    save_config(encrypted_password, key)


if __name__ == "__main__":
    main()
