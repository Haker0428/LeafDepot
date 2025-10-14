from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import Response
import json
import zlib
import base64
import os
import random
from datetime import datetime
from typing import List, Dict, Any

# LMS模拟服务配置
SIMULATOR_BASE_URL = "http://localhost:5000"
PORT = 5000
USER_CODE = "test"
PASSWORD = "test"
AUTH_TOKEN = "d7e8d8fe17fbfcdb6e41efbfbd6d6befbfbd7aefbfbd53634fefbfbd1a7e050c16e3b"

app = FastAPI(title="LMS Mock Service", version="1.0.0")

# 模拟数据
# 储位信息数据
bins_data = [
    {"whCode": "WH001", "areaCode": "A01", "areaName": "A区", "binCode": "BIN001",
        "binDesc": "A区-01排-02层", "binQty": 10000.0, "binStatus": "1"},
    {"whCode": "WH001", "areaCode": "A01", "areaName": "A区", "binCode": "BIN002",
        "binDesc": "A区-02排-03层", "binQty": 15000.0, "binStatus": "1"},
    {"whCode": "WH001", "areaCode": "B01", "areaName": "B区", "binCode": "BIN003",
        "binDesc": "B区-01排-01层", "binQty": 20000.0, "binStatus": "2"},
    {"whCode": "WH002", "areaCode": "C01", "areaName": "C区", "binCode": "BIN004",
        "binDesc": "C区-01排-02层", "binQty": 8000.0, "binStatus": "1"},
    {"whCode": "WH002", "areaCode": "D01", "areaName": "D区", "binCode": "BIN005",
        "binDesc": "D区-02排-03层", "binQty": 12000.0, "binStatus": "3"},
    {"whCode": "WH003", "areaCode": "E01", "areaName": "E区", "binCode": "BIN006",
        "binDesc": "E区-01排-01层", "binQty": 18000.0, "binStatus": "4"}
]

# 盘点任务数据
tasks_data = [
    {
        "taskNo": "T20230815001",
        "taskDetailId": "DT20230815001",
        "binId": "BIN001",
        "binDesc": "A区-01排-02层",
        "binCode": "A-01-02",
        "itemId": "ITEM001",
        "itemCode": "YC-ZHONGHUA",
        "itemDesc": "中华(硬盒)",
        "invQty": 150.0,
        "qtyUnit": "条",
        "countQty": 148.0,
        "status": "未盘点"
    },
    {
        "taskNo": "T20230815002",
        "taskDetailId": "DT20230815002",
        "binId": "BIN002",
        "binDesc": "A区-02排-03层",
        "binCode": "A-02-03",
        "itemId": "ITEM002",
        "itemCode": "YC-HUANGHE",
        "itemDesc": "黄鹤楼(软蓝)",
        "invQty": 200.0,
        "qtyUnit": "条",
        "countQty": 195.0,
        "status": "未盘点"
    },
    {
        "taskNo": "T20230815003",
        "taskDetailId": "DT20230815003",
        "binId": "BIN003",
        "binDesc": "B区-01排-01层",
        "binCode": "B-01-01",
        "itemId": "ITEM003",
        "itemCode": "YC-CAOYUAN",
        "itemDesc": "中华(软盒)",
        "invQty": 300.0,
        "qtyUnit": "条",
        "countQty": 298.0,
        "status": "未盘点"
    }
]

# 用于存储任务反馈结果
feedback_results = {}


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


@app.get("/login")
async def login(request: Request):
    """登录接口"""
    user_code = request.headers.get('userCode')
    password = request.headers.get('password')

    if user_code == "test" and password == "test":
        response_data = {
            "userId": "1000000",
            "userCode": user_code,
            "userName": "测试账号",
            "companyId": "1",
            "companyName": "河北省",
            "employeeId": "1000000",
            "deptId": "1000000",
            "deptName": "省物流处",
            "dingUserId": None,
            "mobile": "",
            "shortName": "河北省",
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
            "userId": "1000000",
            "userCode": "test",
            "userName": "",
            "companyId": "1",
            "companyName": "河北省",
            "mobile": ""
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

    # 返回储位信息
    encoded_data = compress_and_encode(bins_data)
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
    encoded_data = compress_and_encode(tasks_data)
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
        task_data = decompress_and_decode(encoded_data_str)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data format"
        )

    # 模拟处理反馈结果
    task_detail_id = task_data.get('taskDetailId')
    count_qty = task_data.get('countQty')

    if task_detail_id and count_qty:
        feedback_results[task_detail_id] = {
            "countQty": count_qty,
            "status": "已反馈",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 更新任务状态
        for task in tasks_data:
            if task["taskDetailId"] == task_detail_id:
                task["countQty"] = float(count_qty)
                task["status"] = "已反馈"
                break

        return "OK"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required parameters"
        )


@app.get("/api/v1/tasks")
async def get_tasks():
    """模拟API接口，用于前端展示"""
    return tasks_data

if __name__ == "__main__":
    # 确保数据目录存在
    os.makedirs('data', exist_ok=True)

    # 保存初始数据到文件
    with open('data/bins.json', 'w', encoding='utf-8') as f:
        json.dump(bins_data, f, ensure_ascii=False, indent=2)

    with open('data/tasks.json', 'w', encoding='utf-8') as f:
        json.dump(tasks_data, f, ensure_ascii=False, indent=2)

    print("="*50)
    print("LMS 模拟服务已启动 (FastAPI)")
    print(f"访问地址: http://localhost:{PORT}")
    print("测试账号: userCode=test, password=test")
    print("认证令牌: " + AUTH_TOKEN[:20] + "...")
    print("="*50)

    # 使用uvicorn运行
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
