import time
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import Response
# 在现有的导入语句中，确保包含 Body
from fastapi import FastAPI, Request, HTTPException, status, Body  # 添加 Body
from fastapi.responses import Response
import json
import zlib
import base64
import os
import sys
import pandas as pd
from pathlib import Path
import math
import time  # 添加 time 导入
import uuid  # 添加 uuid 导入
import random
from datetime import datetime
from typing import List, Dict, Any, Optional  # 添加 Optional
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import custom_utils

# LMS模拟服务配置
# 移除硬编码的用户名密码
USER_CODE = "admin"  # 保留作为默认值，但主要从Excel读取
PASSWORD = "admin"   # 保留作为默认值，但主要从Excel读取
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
USERS_FILE_PATH = Path("users_data.xlsx")  # 新增：用户信息Excel文件路径


def load_users_from_excel():
    """
    从Excel文件加载用户信息数据
    包含以下字段：
    1. userCode
    2. password
    3. userName
    4. companyId
    5. companyName
    6. employeeId
    7. deptId
    8. deptName
    9. dingUserId
    10. mobile
    11. shortName
    12. companyLevel
    13. nationalCode
    14. authToken
    15. userLevel (新增：admin/operator)
    """
    users_data = []

    if not USERS_FILE_PATH.exists():
        print(f"警告：用户Excel文件 '{USERS_FILE_PATH}' 不存在，使用默认管理员账号")
        # 返回默认的管理员账号
        return [
            {
                "userCode": "admin",
                "password": "admin",
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
                "authToken": AUTH_TOKEN,
                "userLevel": "admin"
            }
        ]

    try:
        # 读取Excel文件
        df = pd.read_excel(USERS_FILE_PATH)

        # 检查列数是否足够
        if df.shape[1] < 15:
            print(f"警告：用户Excel文件列数不足15列，实际有{df.shape[1]}列")
            # 返回默认管理员账号
            return [{
                "userCode": "admin",
                "password": "admin",
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
                "authToken": AUTH_TOKEN,
                "userLevel": "admin"
            }]

        # 将每行数据转换为字典
        for _, row in df.iterrows():
            # 确保行数据长度足够，不足的列用空值填充
            row_values = row.tolist()

            # 如果行数据不足15个值，用空值或默认值填充
            while len(row_values) < 15:
                row_values.append("")

            # 创建用户信息字典
            user_info = {
                "userCode": str(row_values[0]) if not pd.isna(row_values[0]) else "",
                "password": str(row_values[1]) if not pd.isna(row_values[1]) else "",
                "userName": str(row_values[2]) if not pd.isna(row_values[2]) else "",
                "companyId": str(row_values[3]) if not pd.isna(row_values[3]) else "",
                "companyName": str(row_values[4]) if not pd.isna(row_values[4]) else "",
                "employeeId": str(row_values[5]) if not pd.isna(row_values[5]) else "",
                "deptId": str(row_values[6]) if not pd.isna(row_values[6]) else "",
                "deptName": str(row_values[7]) if not pd.isna(row_values[7]) else "",
                "dingUserId": str(row_values[8]) if not pd.isna(row_values[8]) else "",
                "mobile": str(row_values[9]) if not pd.isna(row_values[9]) else "",
                "shortName": str(row_values[10]) if not pd.isna(row_values[10]) else "",
                "companyLevel": str(row_values[11]) if not pd.isna(row_values[11]) else "",
                "nationalCode": str(row_values[12]) if not pd.isna(row_values[12]) else "",
                "authToken": str(row_values[13]) if not pd.isna(row_values[13]) else "",
                # 默认操作员权限
                "userLevel": str(row_values[14]) if not pd.isna(row_values[14]) else "operator"
            }

            # 只添加有效的用户数据行（userCode不为空）
            if user_info["userCode"]:
                users_data.append(user_info)

        print(f"成功从Excel加载 {len(users_data)} 条用户信息")
        return users_data

    except Exception as e:
        print(f"读取用户Excel文件出错: {e}")
        # 返回默认管理员账号
        return [{
            "userCode": "admin",
            "password": "admin",
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
            "authToken": AUTH_TOKEN,
            "userLevel": "admin"
        }]

# 在 load_users_from_excel 函数后添加以下代码


class UserRegistration(BaseModel):
    """用户注册请求模型"""
    userCode: str
    password: str
    userName: str
    userLevel: str = "operator"
    companyId: str = ""
    companyName: str = ""
    employeeId: str = ""
    deptId: str = ""
    deptName: str = ""
    dingUserId: str = ""
    mobile: str = ""
    shortName: str = ""
    companyLevel: str = ""
    nationalCode: str = ""


class UserDelete(BaseModel):
    """用户删除请求模型"""
    userCode: str


def get_current_user(auth_token: str):
    """根据authToken获取当前用户信息"""
    if not auth_token:
        return None

    for user in users_data:
        if user.get("authToken") == auth_token:
            return user
    return None


def save_users_to_excel():
    """将用户数据保存到Excel文件"""
    try:
        if not USERS_FILE_PATH.exists():
            # 如果文件不存在，创建目录
            USERS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        # 创建DataFrame
        users_list = []
        for user in users_data:
            users_list.append([
                user.get("userCode", ""),
                user.get("password", ""),
                user.get("userName", ""),
                user.get("companyId", ""),
                user.get("companyName", ""),
                user.get("employeeId", ""),
                user.get("deptId", ""),
                user.get("deptName", ""),
                user.get("dingUserId", ""),
                user.get("mobile", ""),
                user.get("shortName", ""),
                user.get("companyLevel", ""),
                user.get("nationalCode", ""),
                user.get("authToken", ""),
                user.get("userLevel", "operator")
            ])

        df = pd.DataFrame(users_list, columns=[
            "userCode", "password", "userName", "companyId", "companyName",
            "employeeId", "deptId", "deptName", "dingUserId", "mobile",
            "shortName", "companyLevel", "nationalCode", "authToken", "userLevel"
        ])

        # 保存到Excel
        df.to_excel(USERS_FILE_PATH, index=False)
        print(f"用户数据已保存到Excel文件: {USERS_FILE_PATH}")
        return True
    except Exception as e:
        print(f"保存用户数据到Excel失败: {e}")
        return False


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
users_data = load_users_from_excel()  # 新增：加载用户数据

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
    """登录接口 - 从Excel文件验证用户"""
    user_code = request.headers.get('userCode')
    password = request.headers.get('password')

    # 在用户数据中查找匹配的用户
    user_found = None
    for user in users_data:
        if user["userCode"] == user_code and user["password"] == password:
            user_found = user
            break

    if user_found:
        response_data = {
            "userId": user_found.get("employeeId", "0000001"),
            "userCode": user_found.get("userCode", ""),
            "userName": user_found.get("userName", ""),
            "companyId": user_found.get("companyId", "188"),
            "companyName": user_found.get("companyName", "河北省烟草局"),
            "employeeId": user_found.get("employeeId", "1000000"),
            "deptId": user_found.get("deptId", "1000000"),
            "deptName": user_found.get("deptName", "省物流处"),
            "dingUserId": user_found.get("dingUserId", ""),
            "mobile": user_found.get("mobile", "131xxxx8792"),
            "shortName": user_found.get("shortName", "河北省局"),
            "companyLevel": user_found.get("companyLevel", "1"),
            "nationalCode": user_found.get("nationalCode", "11130001"),
            "authToken": user_found.get("authToken", AUTH_TOKEN),
            "userLevel": user_found.get("userLevel", "operator")
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

    # 在用户数据中查找匹配的token
    user_found = None
    for user in users_data:
        if user["authToken"] == token:
            user_found = user
            break

    if user_found:
        return {
            "userId": user_found.get("employeeId", "0000001"),
            "userCode": user_found.get("userCode", ""),
            "userName": user_found.get("userName", ""),
            "companyId": user_found.get("companyId", "188"),
            "companyName": user_found.get("companyName", "河北省烟草局"),
            "mobile": user_found.get("mobile", "131xxxx8792"),
            "userLevel": user_found.get("userLevel", "operator")  # 新增：用户权限
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


@app.get("/third/api/v1/userManagement/getUsers")
async def get_users(request: Request):
    """获取所有用户信息接口"""
    auth_token = request.headers.get('authToken')

    # 验证token
    current_user = get_current_user(auth_token)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )

    # 检查用户权限（只有管理员可以查看所有用户）
    if current_user.get("userLevel") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，只有管理员可以查看用户列表"
        )

    # 返回用户列表（排除密码字段）
    users_response = []
    for user in users_data:
        user_copy = user.copy()
        # 不返回密码
        user_copy.pop("password", None)
        users_response.append(user_copy)

    return {
        "code": 200,
        "message": "success",
        "data": users_response
    }


@app.post("/third/api/v1/userManagement/registerUser")
async def register_user(request: Request, user_data: UserRegistration = Body(...)):
    """用户注册接口"""
    auth_token = request.headers.get('authToken')

    # 验证token
    current_user = get_current_user(auth_token)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )

    # 检查用户权限（只有管理员可以注册用户）
    if current_user.get("userLevel") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，只有管理员可以注册用户"
        )

    # 检查用户代码是否已存在
    for user in users_data:
        if user.get("userCode") == user_data.userCode:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"用户代码 '{user_data.userCode}' 已存在"
            )

    # 生成唯一的authToken和employeeId
    new_auth_token = str(uuid.uuid4()).replace("-", "")
    new_employee_id = str(int(time.time() * 1000))[-8:]  # 使用时间戳生成员工ID

    # 创建新用户 - 修复：使用新生成的authToken，而不是硬编码的AUTH_TOKEN
    new_user = {
        "userCode": user_data.userCode,
        "password": user_data.password,
        "userName": user_data.userName,
        "companyId": user_data.companyId or current_user.get("companyId", "188"),
        "companyName": user_data.companyName or current_user.get("companyName", "河北省烟草局"),
        "employeeId": new_employee_id,
        "deptId": user_data.deptId or current_user.get("deptId", "1000000"),
        "deptName": user_data.deptName or current_user.get("deptName", "省物流处"),
        "dingUserId": user_data.dingUserId,
        "mobile": user_data.mobile,
        "shortName": user_data.shortName or current_user.get("shortName", "河北省局"),
        "companyLevel": user_data.companyLevel or current_user.get("companyLevel", "1"),
        "nationalCode": user_data.nationalCode or current_user.get("nationalCode", "11130001"),
        "authToken": new_auth_token,  # 修复：使用新生成的唯一token
        "userLevel": user_data.userLevel
    }

    # 添加到用户列表
    users_data.append(new_user)

    # 保存到Excel文件
    save_success = save_users_to_excel()

    if save_success:
        return {
            "code": 200,
            "message": "用户注册成功",
            "data": {
                "userCode": new_user["userCode"],
                "userName": new_user["userName"],
                "authToken": new_user["authToken"],
                "employeeId": new_user["employeeId"]
            }
        }
    else:
        # 回滚：从内存中移除新用户
        users_data.remove(new_user)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="用户注册失败，无法保存到文件"
        )


@app.post("/third/api/v1/userManagement/deleteUser")
async def delete_user(request: Request, delete_data: UserDelete = Body(...)):
    """用户删除接口"""
    auth_token = request.headers.get('authToken')

    # 验证token
    current_user = get_current_user(auth_token)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )

    # 检查用户权限（只有管理员可以删除用户）
    if current_user.get("userLevel") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，只有管理员可以删除用户"
        )

    user_code_to_delete = delete_data.userCode

    # 不能删除自己
    if current_user.get("userCode") == user_code_to_delete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账户"
        )

    # 查找要删除的用户
    user_to_delete = None
    for user in users_data:
        if user.get("userCode") == user_code_to_delete:
            user_to_delete = user
            break

    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 '{user_code_to_delete}' 不存在"
        )

    # 从用户列表中移除
    users_data.remove(user_to_delete)

    # 保存到Excel文件
    save_success = save_users_to_excel()

    if save_success:
        return {
            "code": 200,
            "message": f"用户 '{user_code_to_delete}' 删除成功",
            "data": None
        }
    else:
        # 回滚：将用户添加回列表
        users_data.append(user_to_delete)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="用户删除失败，无法保存到文件"
        )


# 在 __main__ 部分添加导入

# 修改启动信息部分，添加用户管理接口信息
if __name__ == "__main__":
    print("LMS模拟服务已启动 (FastAPI)")
    print(f"当前储位信息数量: {len(bins_data)} 条")
    print(f"当前用户信息数量: {len(users_data)} 条")

    # 打印用户数据示例
    if users_data:
        print("用户数据示例:")
        for i, user_info in enumerate(users_data[:3]):
            print(
                f"  第{i+1}条: {user_info['userCode']} - {user_info['userName']} - 权限: {user_info.get('userLevel', 'operator')} - token: {user_info.get('authToken', '')[0:10]}...")

    print("\n用户管理接口:")
    print("  GET  /third/api/v1/userManagement/getUsers - 获取所有用户信息")
    print("  POST /third/api/v1/userManagement/registerUser - 注册新用户")
    print("  POST /third/api/v1/userManagement/deleteUser - 删除用户")

    # 使用uvicorn运行
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6000, log_level="info")
