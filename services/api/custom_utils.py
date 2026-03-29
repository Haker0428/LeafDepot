'''
Author: big box big box@qq.com
Date: 2025-10-21 20:38:50
LastEditors: big box big box@qq.com
LastEditTime: 2025-10-21 20:39:14
FilePath: /app/utils.py
Description: 

Copyright (c) 2025 by lizh, All Rights Reserved. 
'''
import json
import zlib
import base64
from typing import List, Dict, Any


def compress_and_encode(data: Any) -> str:
    """将JSON数据压缩并base64编码"""
    json_str = json.dumps(data, ensure_ascii=False)
    compressed = zlib.compress(json_str.encode('utf-8'))
    return base64.b64encode(compressed).decode('utf-8')


def decompress_and_decode(encoded_data: str) -> Dict:
    """将base64编码数据解压缩并解析为JSON"""
    compressed = base64.b64decode(encoded_data)
    decompressed = zlib.decompress(compressed)
    return json.loads(decompressed.decode('utf-8'))
