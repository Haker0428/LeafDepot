import requests
import json
import uuid
import logging
from typing import Dict, List, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

service_prefix = "/rcs/rtas"


class RCSClient:
    def __init__(self, base_url: str = "http://localhost:4001"):
        """
        初始化RCS客户端

        Args:
            base_url: RCS服务器基础URL
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": 'nonce="wab1tkh",method="HMAC-SHA256",timestamp="2021-01-01T00:00:00+08:00"',
            "Content-Type": "application/json;charset=UTF-8",
            "x-lr-appkey": "a4f*******b324",
            "x-lr-request-id": str(uuid.uuid4()),
            "x-lr-version": "v1.0",
            "x-lr-trace-id": str(uuid.uuid4()),
            "x-lr-source": "app"
        }

    def create_task_group(self,
                          strategy: str,
                          data: List[Dict],
                          group_code: Optional[str] = None,
                          strategy_value: Optional[str] = None,
                          group_seq: Optional[int] = None,
                          target_route: Optional[Dict] = None) -> Dict:
        # 构建请求数据
        request_data = {
            "groupCode": group_code,
            "strategy": strategy,
            "strategyValue": strategy_value,
            "groupSeq": group_seq,
            "targetRoute": target_route,
            "data": data,
        }

        # 生成请求ID
        request_id = str(uuid.uuid4()).replace("-", "")[:16]
        headers = self.headers.copy()
        headers["x-lr-request-id"] = request_id

        url = f"{self.base_url}{service_prefix}/api/robot/controller/task/group"

        try:
            logger.info(f"发送任务组创建请求: {url}")
            logger.info(
                f"请求数据: {json.dumps(request_data, indent=2, ensure_ascii=False)}")

            response = requests.post(
                url=url,
                json=request_data,
                headers=headers,
                timeout=30
            )

            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应内容: {response.text}")

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == "SUCCESS":
                    logger.info("任务组创建成功")
                else:
                    logger.warning(f"任务组创建返回业务异常: {result.get('message')}")
                return result
            else:
                logger.error(f"HTTP请求失败: {response.status_code}")
                return {
                    "code": f"HTTP_ERROR_{response.status_code}",
                    "message": f"HTTP请求失败: {response.status_code}",
                    "data": None
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {str(e)}")
            return {
                "code": "REQUEST_ERROR",
                "message": f"请求异常: {str(e)}",
                "data": None
            }


def main():
    """主函数 - 演示如何使用RCS客户端"""

    # 初始化客户端
    client = RCSClient("http://localhost:4001")

    print("=" * 50)
    print("RCS-2000 任务组接口调用演示")
    print("=" * 50)

    # 示例1: 创建顺序执行任务组
    print("\n1. 创建顺序执行任务组")

    task_data = [
        {
            "robotTaskCode": "task_001_" + str(uuid.uuid4())[:8],
            "sequence": 1
        },
        {
            "robotTaskCode": "task_002_" + str(uuid.uuid4())[:8],
            "sequence": 2
        },
        {
            "robotTaskCode": "task_003_" + str(uuid.uuid4())[:8],
            "sequence": 3
        }
    ]

    target_route = {
        "type": "ZONE",
        "code": "A2"
    }

    result = client.create_task_group(
        group_code="test_group_" + str(uuid.uuid4())[:8],
        strategy="GROUP_SEQ",
        strategy_value="1",  # 组间及组内都有序
        group_seq=10,
        target_route=target_route,
        data=task_data
    )

    group_code = None
    if result.get("code") == "SUCCESS":
        # 从请求数据中获取group_code，实际应用中应该从响应中获取
        group_code = "test_group_demo"  # 这里简化处理


if __name__ == "__main__":
    main()
