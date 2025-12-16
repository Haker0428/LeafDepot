from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import Response
import json
import zlib
import base64
import os
import sys
import pandas as pd
from pathlib import Path
import math

import random
from datetime import datetime
from typing import List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

import custom_utils

# LMS模拟服务配置
USER_CODE = "admin"
PASSWORD = "admin"
AUTH_TOKEN = "d7e8d8fe17fbfcdb6e41efbfbd6d6befbfbd7aefbfbd53634fefbfbd1a7e050c16e3b"

app = FastAPI(title="LMS Mock Service", version="1.0.0")
# 定义允许的源列表
origins = [
    "http://localhost",
    "http://localhost:8000",  # 内部网关端口
]

# 将 CORS 中间件添加到应用
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义Excel文件路径
EXCEL_FILE_PATH = Path("bins_data.xlsx")


def load_bins_from_excel():
    """
    从Excel文件加载储位信息数据
    按照新的列顺序：
    1. whCode
    2. areaCode
    3. areaName
    4. binCode
    5. binDesc
    6. maxQty
    7. binStatus
    8. tobaccoQty
    9. tobaccoCode
    10. tobaccoName
    11. rcsCode
    """
    bins_data = []

    if not EXCEL_FILE_PATH.exists():
        print(f"警告：Excel文件 '{EXCEL_FILE_PATH}' 不存在，使用默认数据")
        # 返回默认的示例数据
        return [
            {
                "whCode": "110004",
                "areaCode": "100301",
                "areaName": "零烟区",
                "binCode": "100301020403",
                "binDesc": "LY-02-04-03",
                "maxQty": 50,
                "binStatus": "1",
                "tobaccoQty": 1,
                "tobaccoCode": "130669",
                "tobaccoName": "钻石(细支心世界)2",
                "rcsCode": "0200000XY0201220"
            }
        ]

    try:
        # 读取Excel文件
        df = pd.read_excel(EXCEL_FILE_PATH)

        # 检查列数是否足够
        if df.shape[1] < 10:
            print(f"警告：Excel文件列数不足10列，实际有{df.shape[1]}列")
            return []

        # 将每行数据转换为字典
        for _, row in df.iterrows():
            # 确保行数据长度足够，不足的列用空值填充
            row_values = row.tolist()

            # 如果行数据不足11个值，用空值或默认值填充
            while len(row_values) < 11:
                row_values.append("")

            # 处理tobaccoQty，向上取整
            tobacco_qty = row_values[7]  # 第8列是tobaccoQty
            if pd.isna(tobacco_qty):
                tobacco_qty = 0
            else:
                try:
                    # 尝试转换为浮点数再向上取整
                    tobacco_qty = math.ceil(float(tobacco_qty))
                except (ValueError, TypeError):
                    tobacco_qty = 0

            # 创建字典对象，按照新的顺序
            bin_info = {
                "whCode": str(row_values[0]) if not pd.isna(row_values[0]) else "",
                "areaCode": str(row_values[1]) if not pd.isna(row_values[1]) else "",
                "areaName": str(row_values[2]) if not pd.isna(row_values[2]) else "",
                "binCode": str(row_values[3]) if not pd.isna(row_values[3]) else "",
                "binDesc": str(row_values[4]) if not pd.isna(row_values[4]) else "",
                "maxQty": int(row_values[5]) if not pd.isna(row_values[5]) else 0,
                "binStatus": str(row_values[6]) if not pd.isna(row_values[6]) else "",
                "tobaccoQty": tobacco_qty,  # 已向上取整
                "tobaccoCode": str(row_values[8]) if not pd.isna(row_values[8]) else "",
                "tobaccoName": str(row_values[9]) if not pd.isna(row_values[9]) else "",
                "rcsCode": str(row_values[10]) if not pd.isna(row_values[9]) else ""
            }

            # 只添加有效的数据行（binCode不为空）
            if bin_info["binCode"]:
                bins_data.append(bin_info)

        print(f"成功从Excel加载 {len(bins_data)} 条储位信息")
        return bins_data

    except Exception as e:
        print(f"读取Excel文件出错: {e}")
        return []


# 程序启动时加载Excel数据
bins_data = load_bins_from_excel()

# 盘点任务数据（保持不变）
tasks_data = [
    {
        "taskID": "T001",
        "whCode": "110004",
        "areaCode": "100301",
        "areaName": "零烟区",
        "binCode": "100301020403",
        "binDesc": "LY-02-04-03",
        "maxQty": 50,
        "binStatus": "1",
        "tobaccoQty": 1,
        "tobaccoCode": "130669",
        "tobaccoName": "钻石(细支心世界)2",
        "rcsCode": "0200000XY0201220"
    },
    {
        "taskID": "T001",
        "whCode": "110004",
        "areaCode": "100301",
        "areaName": "零烟区",
        "binCode": "100301010602",
        "binDesc": "LY-01-06-02",
        "maxQty": 50,
        "binStatus": "1",
        "tobaccoQty": 1,
        "tobaccoCode": "130684",
        "tobaccoName": "钻石(细支荷花)",
        "rcsCode": "0200000XY0202440"
    },
]

# 用于存储任务反馈结果
feedback_results = {}


@app.get("/login")
async def login(request: Request):
    """登录接口"""
    user_code = request.headers.get('userCode')
    password = request.headers.get('password')

    if user_code == USER_CODE and password == PASSWORD:
        response_data = {
            "userId": "0000001",
            "userCode": USER_CODE,
            "userName": "管理员账号",
            "companyId": "188",
            "companyName": "河北省烟草局",
            "employeeId": "1000000",
            "deptId": "1000000",
            "deptName": "省物流处",
            "dingUserId": "",
            "mobile": "131xxxx8792",
            "shortName": "河北省局",
            "companyLevel": "1",
            "nationalCode": "11130001",
            "authToken": AUTH_TOKEN
        }
        return response_data
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@app.get("/auth/token")
async def auth_token(request: Request):
    """根据token获取用户信息"""
    token = request.query_params.get('token')

    if token == AUTH_TOKEN:
        return {
            "userId": "0000001",
            "userCode": USER_CODE,
            "userName": "管理员账号",
            "companyId": "188",
            "companyName": "河北省烟草局",
            "mobile": "131xxxx8792"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@app.get("/third/api/v1/lmsToRcsService/getLmsBin")
async def get_lms_bin(request: Request):
    """储位信息接口"""
    auth_token = request.headers.get('authToken')

    if not auth_token or auth_token != AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )

    # 返回储位信息（从已加载的数据中获取）
    encoded_data = custom_utils.compress_and_encode(bins_data)
    return Response(content=encoded_data, media_type="text/plain")


@app.get("/third/api/v1/lmsToRcsService/getCountTasks")
async def get_count_tasks(request: Request):
    """盘点任务接口"""
    auth_token = request.headers.get('authToken')

    if not auth_token or auth_token != AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )

    # 返回盘点任务
    encoded_data = custom_utils.compress_and_encode(tasks_data)
    return Response(content=encoded_data, media_type="text/plain")


@app.post("/third/api/v1/RcsToLmsService/setTaskResults")
async def set_task_results(request: Request):
    """盘点任务反馈接口"""
    auth_token = request.headers.get('authToken')

    if not auth_token or auth_token != AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )

    if request.headers.get('Content-Type') != 'text/plain':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Content-Type"
        )

    try:
        # 解码并解析请求体
        encoded_data = await request.body()
        encoded_data_str = encoded_data.decode('utf-8')
        task_data = custom_utils.decompress_and_decode(encoded_data_str)
        return "update countQty success"

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data format: {str(e)}"
        )


if __name__ == "__main__":
    print("LMS模拟服务已启动 (FastAPI)")
    print(f"当前储位信息数量: {len(bins_data)} 条")

    # 打印前几条数据示例
    if bins_data:
        print("示例数据:")
        for i, bin_info in enumerate(bins_data[:3]):
            print(f"  第{i+1}条: {bin_info}")

    # 使用uvicorn运行
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6000, log_level="info")
