from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import Response
import json
import zlib
import base64
import os
import sys

import random
from datetime import datetime
from typing import List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware


# Add custom path to sys.path
sys.path.append('../../gateway')
import custom_utils # fmt:off


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

# @app.get("/login") #登陆接口
# @app.get("/auth/token") #获取用户信息接口
# @app.get("/third/api/v1/lmsToRcsService/getLmsBin") #获取储位信息接口
# @app.get("/third/api/v1/lmsToRcsService/getCountTasks") #获取盘点任务接口
# @app.post("/third/api/v1/RcsToLmsService/setTaskResults") # 盘点任务反馈接口


# 模拟数据
# 储位信息数据
bins_data = [
    {
"whCode": "110004",
"areaCode": "100301",
"areaName": "零烟区",
"binCode": "100301020403",
"binDesc": "LY-02-04-03",
"binStatus": "1",
"tobaccoName": "钻石(细支心世界)2",
"tobaccoCode": "130669",
"tobaccoQty": 1,
"maxQty": 50
},
{
"whCode": "110004",
"areaCode": "100301",
"areaName": "零烟区",
"binCode": "'100301010602",
"binDesc": "LY-01-06-02",
"binStatus": "1",
"tobaccoName": "红塔山(软经典)",
"tobaccoCode": "532437",
"tobaccoQty": 185005,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-01-03",
"binDesc": "20-01-03",
"binStatus": "1",
"tobaccoName": "钻石(硬迎宾)",
"tobaccoCode": "130690",
"tobaccoQty": 1279,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-02-01",
"binDesc": "20-02-01",
"binStatus": "1",
"tobaccoName": "长白山(777)",
"tobaccoCode": "222419",
"tobaccoQty": 1062,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-02-02",
"binDesc": "20-02-02",
"binStatus": "1",
"tobaccoName": "钻石(荷花)",
"tobaccoCode": "130679",
"tobaccoQty": 1014,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-02-03",
"binDesc": "20-02-03",
"binStatus": "1",
"tobaccoName": "钻石(硬红)",
"tobaccoCode": "130705",
"tobaccoQty": 1012,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-03-01",
"binDesc": "20-03-01",
"binStatus": "1",
"tobaccoName": "钻石(细支尚风)",
"tobaccoCode": "130688",
"tobaccoQty": 882,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-03-02",
"binDesc": "20-03-02",
"binStatus": "1",
"tobaccoName": "南京(炫赫门)",
"tobaccoCode": "320113",
"tobaccoQty": 835,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-03-03",
"binDesc": "20-03-03",
"binStatus": "1",
"tobaccoName": "钻石(硬玫瑰紫)",
"tobaccoCode": "130780",
"tobaccoQty": 766,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-04-01",
"binDesc": "20-04-01",
"binStatus": "1",
"tobaccoName": "钻石(玫瑰二代)",
"tobaccoCode": "130665",
"tobaccoQty": 751,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-04-02",
"binDesc": "20-04-02",
"binStatus": "1",
"tobaccoName": "黄山(印象一品)",
"tobaccoCode": "340364",
"tobaccoQty": 749,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-04-03",
"binDesc": "20-04-03",
"binStatus": "1",
"tobaccoName": "真龙(美人香草)",
"tobaccoCode": "450123",
"tobaccoQty": 712,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-05-01",
"binDesc": "20-05-01",
"binStatus": "1",
"tobaccoName": "钻石(绿石2代)",
"tobaccoCode": "130789",
"tobaccoQty": 678,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-05-02",
"binDesc": "20-05-02",
"binStatus": "1",
"tobaccoName": "红河(小熊猫世纪风)",
"tobaccoCode": "532515",
"tobaccoQty": 612,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-05-03",
"binDesc": "20-05-03",
"binStatus": "1",
"tobaccoName": "贵烟(跨越)",
"tobaccoCode": "520150",
"tobaccoQty": 540,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-06-01",
"binDesc": "20-06-01",
"binStatus": "1",
"tobaccoName": "泰山(红将军)",
"tobaccoCode": "370227",
"tobaccoQty": 483,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-06-02",
"binDesc": "20-06-02",
"binStatus": "1",
"tobaccoName": "娇子(格调细支)",
"tobaccoCode": "510125",
"tobaccoQty": 454,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-06-03",
"binDesc": "20-06-03",
"binStatus": "1",
"tobaccoName": "黄金叶(金满堂)",
"tobaccoCode": "410111",
"tobaccoQty": 449,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-07-01",
"binDesc": "20-07-01",
"binStatus": "1",
"tobaccoName": "黄鹤楼(天下名楼)",
"tobaccoCode": "420142",
"tobaccoQty": 436,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-07-02",
"binDesc": "20-07-02",
"binStatus": "1",
"tobaccoName": "红旗渠(芒果)",
"tobaccoCode": "410511",
"tobaccoQty": 423,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-07-03",
"binDesc": "20-07-03",
"binStatus": "1",
"tobaccoName": "红塔山（细支传奇）",
"tobaccoCode": "535321",
"tobaccoQty": 369,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-08-01",
"binDesc": "20-08-01",
"binStatus": "1",
"tobaccoName": "云烟(紫)",
"tobaccoCode": "530153",
"tobaccoQty": 352,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-08-02",
"binDesc": "20-08-02",
"binStatus": "1",
"tobaccoName": "中华(硬)",
"tobaccoCode": "310102",
"tobaccoQty": 349,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-08-03",
"binDesc": "20-08-03",
"binStatus": "1",
"tobaccoName": "钻石(细支心世界)2",
"tobaccoCode": "130669",
"tobaccoQty": 342,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-09-01",
"binDesc": "20-09-01",
"binStatus": "1",
"tobaccoName": "云烟(细支云龙)",
"tobaccoCode": "530197",
"tobaccoQty": 324,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-09-02",
"binDesc": "20-09-02",
"binStatus": "1",
"tobaccoName": "七匹狼(纯境)2",
"tobaccoCode": "352636",
"tobaccoQty": 307,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-09-03",
"binDesc": "20-09-03",
"binStatus": "1",
"tobaccoName": "泰山(心悦)",
"tobaccoCode": "370228",
"tobaccoQty": 282,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-10-01",
"binDesc": "20-10-01",
"binStatus": "1",
"tobaccoName": "长白山(蓝尚)",
"tobaccoCode": "222421",
"tobaccoQty": 259,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-10-02",
"binDesc": "20-10-02",
"binStatus": "1",
"tobaccoName": "芙蓉王(硬细支)",
"tobaccoCode": "430729",
"tobaccoQty": 251,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "20-10-03",
"binDesc": "20-10-03",
"binStatus": "1",
"tobaccoName": "黄鹤楼(软蓝)",
"tobaccoCode": "420108",
"tobaccoQty": 228,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-01-01",
"binDesc": "21-01-01",
"binStatus": "1",
"tobaccoName": "中华(软)",
"tobaccoCode": "310101",
"tobaccoQty": 212,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-01-02",
"binDesc": "21-01-02",
"binStatus": "1",
"tobaccoName": "红河(硬)",
"tobaccoCode": "532519",
"tobaccoQty": 185,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-01-03",
"binDesc": "21-01-03",
"binStatus": "1",
"tobaccoName": "黄山(新制皖烟)",
"tobaccoCode": "340347",
"tobaccoQty": 183,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-02-01",
"binDesc": "21-02-01",
"binStatus": "1",
"tobaccoName": "双喜(莲香)",
"tobaccoCode": "440119",
"tobaccoQty": 171,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-02-02",
"binDesc": "21-02-02",
"binStatus": "1",
"tobaccoName": "利群(软蓝)2",
"tobaccoCode": "330148",
"tobaccoQty": 171,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-02-03",
"binDesc": "21-02-03",
"binStatus": "1",
"tobaccoName": "娇子(宽窄好运细支)",
"tobaccoCode": "510139",
"tobaccoQty": 169,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-03-01",
"binDesc": "21-03-01",
"binStatus": "1",
"tobaccoName": "黄鹤楼(雪之梦5号)",
"tobaccoCode": "420198",
"tobaccoQty": 161,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-03-02",
"binDesc": "21-03-02",
"binStatus": "1",
"tobaccoName": "玉溪(软)",
"tobaccoCode": "532420",
"tobaccoQty": 159,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-03-03",
"binDesc": "21-03-03",
"binStatus": "1",
"tobaccoName": "利群(长嘴)",
"tobaccoCode": "330106",
"tobaccoQty": 150,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-04-01",
"binDesc": "21-04-01",
"binStatus": "1",
"tobaccoName": "黄金叶(乐途)",
"tobaccoCode": "410135",
"tobaccoQty": 147,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-04-02",
"binDesc": "21-04-02",
"binStatus": "1",
"tobaccoName": "人民大会堂(硬红细支)2",
"tobaccoCode": "210811",
"tobaccoQty": 144,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-04-03",
"binDesc": "21-04-03",
"binStatus": "1",
"tobaccoName": "钻石(细支荷花)",
"tobaccoCode": "130684",
"tobaccoQty": 137,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-05-01",
"binDesc": "21-05-01",
"binStatus": "1",
"tobaccoName": "利群(新版)",
"tobaccoCode": "330101",
"tobaccoQty": 132,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-05-02",
"binDesc": "21-05-02",
"binStatus": "1",
"tobaccoName": "牡丹(软)",
"tobaccoCode": "310108",
"tobaccoQty": 123,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-05-03",
"binDesc": "21-05-03",
"binStatus": "1",
"tobaccoName": "玉溪(鑫中支)",
"tobaccoCode": "532491",
"tobaccoQty": 123,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-06-01",
"binDesc": "21-06-01",
"binStatus": "1",
"tobaccoName": "苏烟(五星红杉树)",
"tobaccoCode": "320310",
"tobaccoQty": 120,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-06-02",
"binDesc": "21-06-02",
"binStatus": "1",
"tobaccoName": "黄山(红方印细支)",
"tobaccoCode": "340354",
"tobaccoQty": 118,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-06-03",
"binDesc": "21-06-03",
"binStatus": "1",
"tobaccoName": "芙蓉王(硬)",
"tobaccoCode": "430701",
"tobaccoQty": 99,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-07-01",
"binDesc": "21-07-01",
"binStatus": "1",
"tobaccoName": "云烟(软珍品)",
"tobaccoCode": "530113",
"tobaccoQty": 91,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-07-02",
"binDesc": "21-07-02",
"binStatus": "1",
"tobaccoName": "贵烟(萃)",
"tobaccoCode": "520158",
"tobaccoQty": 72,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-07-03",
"binDesc": "21-07-03",
"binStatus": "1",
"tobaccoName": "中华(双中支)",
"tobaccoCode": "310182",
"tobaccoQty": 67,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-08-01",
"binDesc": "21-08-01",
"binStatus": "1",
"tobaccoName": "黄金叶(天香细支)",
"tobaccoCode": "410123",
"tobaccoQty": 62,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-08-02",
"binDesc": "21-08-02",
"binStatus": "1",
"tobaccoName": "黄鹤楼(硬蓝)",
"tobaccoCode": "420179",
"tobaccoQty": 60,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-08-03",
"binDesc": "21-08-03",
"binStatus": "1",
"tobaccoName": "南京(雨花石)",
"tobaccoCode": "320112",
"tobaccoQty": 57,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-09-01",
"binDesc": "21-09-01",
"binStatus": "1",
"tobaccoName": "钻石（金石）(张家口)",
"tobaccoCode": "130792",
"tobaccoQty": 55,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-09-02",
"binDesc": "21-09-02",
"binStatus": "1",
"tobaccoName": "黄鹤楼(硬1916)",
"tobaccoCode": "420134",
"tobaccoQty": 54,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-09-03",
"binDesc": "21-09-03",
"binStatus": "1",
"tobaccoName": "白沙(软和天下)",
"tobaccoCode": "430132",
"tobaccoQty": 52,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "21-10-01",
"binDesc": "21-10-01",
"binStatus": "1",
"tobaccoName": "芙蓉王(硬中支)",
"tobaccoCode": "430734",
"tobaccoQty": 50,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "22-01-01",
"binDesc": "22-01-01",
"binStatus": "1",
"tobaccoName": "白沙(硬细支和天下)",
"tobaccoCode": "430130",
"tobaccoQty": 50,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "22-01-02",
"binDesc": "22-01-02",
"binStatus": "1",
"tobaccoName": "黄鹤楼(硬奇景)",
"tobaccoCode": "420177",
"tobaccoQty": 50,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "22-01-03",
"binDesc": "22-01-03",
"binStatus": "1",
"tobaccoName": "黄金叶(炫尚)",
"tobaccoCode": "415604",
"tobaccoQty": 42,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "22-02-01",
"binDesc": "22-02-01",
"binStatus": "1",
"tobaccoName": "钻石(软荷花)",
"tobaccoCode": "130801",
"tobaccoQty": 42,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "22-02-02",
"binDesc": "22-02-02",
"binStatus": "1",
"tobaccoName": "利群(软长嘴)",
"tobaccoCode": "330115",
"tobaccoQty": 40,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "22-02-03",
"binDesc": "22-02-03",
"binStatus": "1",
"tobaccoName": "泰山(颜悦)2",
"tobaccoCode": "370268",
"tobaccoQty": 40,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "22-03-01",
"binDesc": "22-03-01",
"binStatus": "1",
"tobaccoName": "长城(红色132)2",
"tobaccoCode": "510168",
"tobaccoQty": 39,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "22-03-02",
"binDesc": "22-03-02",
"binStatus": "1",
"tobaccoName": "黄鹤楼(硬峡谷柔情)",
"tobaccoCode": "420157",
"tobaccoQty": 37,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "22-03-03",
"binDesc": "22-03-03",
"binStatus": "1",
"tobaccoName": "云烟(软大重九)",
"tobaccoCode": "530180",
"tobaccoQty": 37,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "22-04-01",
"binDesc": "22-04-01",
"binStatus": "1",
"tobaccoName": "牡丹(红中支)",
"tobaccoCode": "310159",
"tobaccoQty": 36,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "22-04-02",
"binDesc": "22-04-02",
"binStatus": "1",
"tobaccoName": "黄山(徽商新概念细支)",
"tobaccoCode": "340362",
"tobaccoQty": 36,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "22-04-03",
"binDesc": "22-04-03",
"binStatus": "1",
"tobaccoName": "云烟(中支云龙)",
"tobaccoCode": "535323",
"tobaccoQty": 35,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "22-05-01",
"binDesc": "22-05-01",
"binStatus": "1",
"tobaccoName": "中华(金中支)",
"tobaccoCode": "310181",
"tobaccoQty": 33,
"maxQty": 50
},
{
"whCode": "WH001",
"areaCode": "A01",
"areaName": "A区",
"binCode": "22-05-02",
"binDesc": "22-05-02",
"binStatus": "1",
"tobaccoName": "兰州(硬珍品)",
"tobaccoCode": "620103",
"tobaccoQty": 30,
"maxQty": 50
},
]

# 盘点任务数据
tasks_data = [
    {
        "taskNo": "T20251021001",
        "taskDetailId": "T20251021001",
        "binId": "BIN-001",
        "binDesc": "20-01-01",
        "binCode": "20-01-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 26,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
    {
        "taskNo": "T20251021002",
        "taskDetailId": "T20251021002",
        "binId": "BIN-001",
        "binDesc": "20-02-01",
        "binCode": "20-02-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 28,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
    {
        "taskNo": "T20251021003",
        "taskDetailId": "T20251021003",
        "binId": "BIN-001",
        "binDesc": "20-03-01",
        "binCode": "20-03-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 26,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
    {
        "taskNo": "T20251021004",
        "taskDetailId": "T20251021004",
        "binId": "BIN-001",
        "binDesc": "20-04-01",
        "binCode": "20-04-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 26,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
    {
        "taskNo": "T20251021005",
        "taskDetailId": "T20251021005",
        "binId": "BIN-001",
        "binDesc": "20-05-01",
        "binCode": "20-05-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 27,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
    {
        "taskNo": "T20251021006",
        "taskDetailId": "T20251021006",
        "binId": "BIN-001",
        "binDesc": "20-06-01",
        "binCode": "20-06-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 28,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
    {
        "taskNo": "T20251021007",
        "taskDetailId": "T20251021007",
        "binId": "BIN-001",
        "binDesc": "20-07-01",
        "binCode": "20-07-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 30,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
    {
        "taskNo": "T20251021008",
        "taskDetailId": "T20251021008",
        "binId": "BIN-001",
        "binDesc": "20-08-01",
        "binCode": "20-08-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 30,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
    {
        "taskNo": "T20251021009",
        "taskDetailId": "T20251021009",
        "binId": "BIN-001",
        "binDesc": "20-09-01",
        "binCode": "20-09-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 24,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
    {
        "taskNo": "T20251021010",
        "taskDetailId": "T20251021010",
        "binId": "BIN-001",
        "binDesc": "20-10-01",
        "binCode": "20-10-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 25,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
    {
        "taskNo": "T20251021011",
        "taskDetailId": "T20251021011",
        "binId": "BIN-001",
        "binDesc": "20-11-01",
        "binCode": "20-11-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 28,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
        {
        "taskNo": "T20251021012",
        "taskDetailId": "T20251021012",
        "binId": "BIN-001",
        "binDesc": "20-12-01",
        "binCode": "20-12-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 28,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
                {
        "taskNo": "T20251021013",
        "taskDetailId": "T20251021013",
        "binId": "BIN-001",
        "binDesc": "20-13-01",
        "binCode": "20-13-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 30,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
                        {
        "taskNo": "T20251021014",
        "taskDetailId": "T20251021014",
        "binId": "BIN-001",
        "binDesc": "20-14-01",
        "binCode": "20-14-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 28,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
                                                {
        "taskNo": "T20251021015",
        "taskDetailId": "T20251021015",
        "binId": "BIN-001",
        "binDesc": "20-15-01",
        "binCode": "20-15-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 30,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
                                                                        {
        "taskNo": "T20251021016",
        "taskDetailId": "T20251021016",
        "binId": "BIN-001",
        "binDesc": "20-16-01",
        "binCode": "20-16-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 22,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
                                                                                                {
        "taskNo": "T20251021017",
        "taskDetailId": "T20251021017",
        "binId": "BIN-001",
        "binDesc": "20-17-01",
        "binCode": "20-17-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 28,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
                                                                                                                        {
        "taskNo": "T20251021018",
        "taskDetailId": "T20251021018",
        "binId": "BIN-001",
        "binDesc": "20-18-01",
        "binCode": "20-18-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 28,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
                                                                                                                                                {
        "taskNo": "T20251021019",
        "taskDetailId": "T20251021019",
        "binId": "BIN-001",
        "binDesc": "20-19-01",
        "binCode": "20-19-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 22,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
                                                                                                                                                                        {
        "taskNo": "T20251021020",
        "taskDetailId": "T20251021020",
        "binId": "BIN-001",
        "binDesc": "20-20-01",
        "binCode": "20-20-01",
        "itemId": "ITEM001",
        "itemCode": "130787",
        "itemDesc": "钻石(软红)",
        "invQty": 30,
        "qtyUnit": "件",
        "countQty": 0,
        "status": "未盘点"
    },
    # {
    #     "taskNo": "T20251021002",
    #     "taskDetailId": "T20251021002",
    #     "binId": "BIN-002",
    #     "binDesc": "20-01-03",
    #     "binCode": "20-01-03",
    #     "itemId": "ITEM002",
    #     "itemCode": "130690",
    #     "itemDesc": "钻石(硬迎宾)",
    #     "invQty": 1279,
    #     "qtyUnit": "件",
    #     "countQty": 0,
    #     "status": "未盘点"
    # },
    # {
    #     "taskNo": "T20251021003",
    #     "taskDetailId": "T20251021003",
    #     "binId": "BIN-003",
    #     "binDesc": "20-02-02",
    #     "binCode": "20-02-02",
    #     "itemId": "ITEM003",
    #     "itemCode": "130679",
    #     "itemDesc": "钻石(荷花)",
    #     "invQty": 1014,
    #     "qtyUnit": "件",
    #     "countQty": 0,
    #     "status": "未盘点"
    # },
    # {
    #     "taskNo": "T20251021004",
    #     "taskDetailId": "T20251021004",
    #     "binId": "BIN-004",
    #     "binDesc": "20-02-03",
    #     "binCode": "20-02-03",
    #     "itemId": "ITEM004",
    #     "itemCode": "130705",
    #     "itemDesc": "钻石(硬红)",
    #     "invQty": 1012,
    #     "qtyUnit": "件",
    #     "countQty": 0,
    #     "status": "未盘点"
    # },
    # {
    #     "taskNo": "T20251021005",
    #     "taskDetailId": "T20251021005",
    #     "binId": "BIN-005",
    #     "binDesc": "20-03-01",
    #     "binCode": "20-03-01",
    #     "itemId": "ITEM005",
    #     "itemCode": "130688",
    #     "itemDesc": "钻石(细支尚风)",
    #     "invQty": 882,
    #     "qtyUnit": "件",
    #     "countQty": 0,
    #     "status": "未盘点"
    # },
    # {
    #     "taskNo": "T20251021006",
    #     "taskDetailId": "T20251021006",
    #     "binId": "BIN-006",
    #     "binDesc": "20-03-03",
    #     "binCode": "20-03-03",
    #     "itemId": "ITEM006",
    #     "itemCode": "130780",
    #     "itemDesc": "钻石(硬玫瑰紫)",
    #     "invQty": 766,
    #     "qtyUnit": "件",
    #     "countQty": 0,
    #     "status": "未盘点"
    # },
    # {
    #     "taskNo": "T20251021007",
    #     "taskDetailId": "T20251021007",
    #     "binId": "BIN-007",
    #     "binDesc": "20-04-01",
    #     "binCode": "20-04-01",
    #     "itemId": "ITEM007",
    #     "itemCode": "130665",
    #     "itemDesc": "钻石(玫瑰二代)",
    #     "invQty": 751,
    #     "qtyUnit": "件",
    #     "countQty": 0,
    #     "status": "未盘点"
    # },
    # {
    #     "taskNo": "T20251021008",
    #     "taskDetailId": "T20251021008",
    #     "binId": "BIN-008",
    #     "binDesc": "20-05-01",
    #     "binCode": "20-05-01",
    #     "itemId": "ITEM008",
    #     "itemCode": "130789",
    #     "itemDesc": "钻石(绿石2代)",
    #     "invQty": 678,
    #     "qtyUnit": "件",
    #     "countQty": 0,
    #     "status": "未盘点"
    # },
    # {
    #     "taskNo": "T20251021009",
    #     "taskDetailId": "T20251021009",
    #     "binId": "BIN-009",
    #     "binDesc": "20-08-03",
    #     "binCode": "20-08-03",
    #     "itemId": "ITEM009",
    #     "itemCode": "130669",
    #     "itemDesc": "钻石(细支心世界)2",
    #     "invQty": 342,
    #     "qtyUnit": "件",
    #     "countQty": 0,
    #     "status": "未盘点"
    # },
    # {
    #     "taskNo": "T20251021010",
    #     "taskDetailId": "T20251021010",
    #     "binId": "BIN-010",
    #     "binDesc": "21-04-03",
    #     "binCode": "21-04-03",
    #     "itemId": "ITEM010",
    #     "itemCode": "130684",
    #     "itemDesc": "钻石(细支荷花)",
    #     "invQty": 137,
    #     "qtyUnit": "件",
    #     "countQty": 0,
    #     "status": "未盘点"
    # },
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

    # 返回储位信息
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
            detail="Invalid data format"
        )

    # # 模拟处理反馈结果
    # task_detail_id = task_data.get('taskDetailId')
    # count_qty = task_data.get('countQty')
    # item_id = task_data.get('itemId')

    # if task_detail_id and count_qty:
    #     feedback_results[task_detail_id] = {
    #         "itemId": item_id,
    #         "countQty": count_qty,
    #         "status": "已反馈",
    #         # "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #     }

        # 更新任务状态
        # for task in tasks_data:
        #     if task["taskDetailId"] == task_detail_id:
        #         task["countQty"] = float(count_qty)
        #         task["status"] = "已反馈"
        #         break

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required parameters"
        )


# @app.get("/api/v1/tasks")
# async def get_tasks():
#     """模拟API接口，用于前端展示"""
#     return tasks_data

if __name__ == "__main__":
    # # 确保数据目录存在
    # os.makedirs('data', exist_ok=True)

    # # 保存初始数据到文件
    # with open('data/bins.json', 'w', encoding='utf-8') as f:
    #     json.dump(bins_data, f, ensure_ascii=False, indent=2)

    # with open('data/tasks.json', 'w', encoding='utf-8') as f:
    #     json.dump(tasks_data, f, ensure_ascii=False, indent=2)

    print("LMS模拟服务已启动 (FastAPI)")

    # 使用uvicorn运行
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6000, log_level="info")
