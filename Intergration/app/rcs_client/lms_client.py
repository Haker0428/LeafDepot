import requests
import json
import zlib
import base64
import os
import time
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("lms_client.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LMSClient")


class LMSClient:
    def __init__(self, base_url, user_code, password):
        self.base_url = base_url
        self.user_code = user_code
        self.password = password
        self.auth_token = None
        self.data_dir = "data"

        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)

    def login(self):
        """登录获取authToken"""
        url = f"{self.base_url}/login"
        headers = {
            "userCode": self.user_code,
            "password": self.password
        }

        logger.info("正在登录LMS系统...")
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            try:
                data = response.json()
                self.auth_token = data.get("authToken")
                if self.auth_token:
                    logger.info("登录成功，获取到authToken: %s",
                                self.auth_token[:10] + "...")
                    return True
                else:
                    logger.error("登录响应中缺少authToken: %s", data)
                    return False
            except json.JSONDecodeError:
                logger.error("响应不是有效的JSON: %s", response.text)
                return False
        else:
            logger.error("登录失败，状态码: %d, 响应: %s",
                         response.status_code, response.text)
            return False

    def _compress_and_encode(self, data):
        """将JSON数据压缩并base64编码"""
        json_str = json.dumps(data)
        compressed = zlib.compress(json_str.encode('utf-8'))
        return base64.b64encode(compressed).decode('utf-8')

    def _decompress_and_decode(self, encoded_data):
        """将base64编码数据解压缩并解析为JSON"""
        compressed = base64.b64decode(encoded_data)
        decompressed = zlib.decompress(compressed)
        return json.loads(decompressed.decode('utf-8'))

    def get_bins(self):
        """获取储位信息"""
        if not self.auth_token:
            logger.error("未获取authToken，无法获取储位信息")
            return None

        url = f"{self.base_url}/third/api/v1/lmsToRcsService/getLmsBin"
        headers = {
            "userCode": self.user_code,
            "authToken": self.auth_token
        }

        logger.info("正在获取储位信息...")
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            try:
                # 解析压缩的响应
                compressed_data = response.text
                bins_data = self._decompress_and_decode(compressed_data)

                # 保存到文件
                self._save_to_file("bins.json", bins_data)
                logger.info("成功获取并存储 %d 个储位信息", len(bins_data))
                return bins_data
            except Exception as e:
                logger.error("处理储位信息响应失败: %s", str(e))
                return None
        else:
            logger.error("获取储位信息失败，状态码: %d, 响应: %s",
                         response.status_code, response.text)
            return None

    def get_tasks(self):
        """获取盘点任务"""
        if not self.auth_token:
            logger.error("未获取authToken，无法获取盘点任务")
            return None

        url = f"{self.base_url}/third/api/v1/lmsToRcsService/getCountTasks"
        headers = {
            "userCode": self.user_code,
            "authToken": self.auth_token
        }

        logger.info("正在获取盘点任务...")
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            try:
                # 解析压缩的响应
                compressed_data = response.text
                tasks_data = self._decompress_and_decode(compressed_data)

                # 保存到文件
                self._save_to_file("tasks.json", tasks_data)
                logger.info("成功获取并存储 %d 个盘点任务", len(tasks_data))
                return tasks_data
            except Exception as e:
                logger.error("处理盘点任务响应失败: %s", str(e))
                return None
        else:
            logger.error("获取盘点任务失败，状态码: %d, 响应: %s",
                         response.status_code, response.text)
            return None

    def feedback_task(self, task_detail_id, count_qty, item_id):
        """反馈盘点任务结果"""
        if not self.auth_token:
            logger.error("未获取authToken，无法反馈盘点任务")
            return False

        url = f"{self.base_url}/third/api/v1/RcsToLmsService/setTaskResults"
        headers = {
            "userCode": self.user_code,
            "authToken": self.auth_token,
            "Content-Type": "text/plain",
            "Accept": "text/plain"
        }

        # 准备请求数据
        data = {
            "taskDetailId": task_detail_id,
            "countQty": str(count_qty),
            "itemId": item_id
        }

        # 压缩并编码
        encoded_data = self._compress_and_encode(data)

        logger.info("正在反馈盘点任务: %s, 数量: %s", task_detail_id, count_qty)
        response = requests.post(url, data=encoded_data, headers=headers)

        if response.status_code == 200:
            logger.info("盘点任务反馈成功: %s", task_detail_id)
            return True
        else:
            logger.error("盘点任务反馈失败，状态码: %d, 响应: %s",
                         response.status_code, response.text)
            return False

    def _save_to_file(self, filename, data):
        """将数据保存到JSON文件"""
        file_path = os.path.join(self.data_dir, filename)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("数据已保存到: %s", file_path)
        except Exception as e:
            logger.error("保存文件失败: %s", str(e))

    def process_tasks(self):
        """处理盘点任务（模拟）"""
        tasks = self.get_tasks()
        if not tasks:
            return

        logger.info("开始处理盘点任务...")
        for task in tasks:
            # 模拟盘点结果（实际应用中应从LMS系统获取）
            count_qty = task.get("invQty", 0) * 0.95  # 模拟95%的盘点率

            # 反馈结果
            success = self.feedback_task(
                task_detail_id=task["taskDetailId"],
                count_qty=round(count_qty, 2),
                item_id=task["itemId"]
            )

            if success:
                # 更新任务状态（模拟）
                task["status"] = "已反馈"
            else:
                task["status"] = "反馈失败"

            # 保存更新后的任务
            self._save_to_file("tasks_updated.json", tasks)

            # 模拟等待
            time.sleep(1)

    def run(self):
        """主运行流程"""
        if not self.login():
            return

        self.get_bins()
        self.get_tasks()
        self.process_tasks()
        logger.info("LMS接口交互流程完成")