import zmq
import time
import logging
import os
from PIL import Image
import io
import base64
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("rcs_simulator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RCSSimulator")


class RCSSimulator:
    """RCS系统模拟服务，负责执行任务、调用相机系统（HTTP）和与外部网关通信"""

    def __init__(self, external_gateway_addr: str = "tcp://localhost:6666"):
        """
        初始化RCS模拟器

        :param external_gateway_addr: 外部网关的RCS通信地址
        """
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(external_gateway_addr)
        logger.info(
            "RCS Simulator connected to external gateway at %s", external_gateway_addr)
        self.image_dir = "../cam_sys/camera_images"
        os.makedirs(self.image_dir, exist_ok=True)
        logger.info("Camera image directory created: %s", self.image_dir)

        # 配置cam_sys URL (假设cam_sys运行在localhost:5010)
        self.cam_sys_url = "http://localhost:5010/take_photo"

    def simulate_task_execution(self, task_id: str, bin_code: str):
        """模拟RCS任务执行流程，调用cam_sys拍照"""
        logger.info("RCS: Starting task %s for bin %s", task_id, bin_code)

        # 模拟任务执行过程（5秒）
        logger.info("RCS: Task in progress...")
        time.sleep(2)

        # 模拟就位状态
        # self._send_task_status(task_id, "positioned")
        logger.info("RCS: Positioning complete")

        # 调用cam_sys拍照 (HTTP POST)
        self._take_photo(task_id, bin_code)
        logger.info("RCS: Photo taken via cam_sys")

        # 模拟任务完成状态
        # self._send_task_status(task_id, "completed")
        logger.info("RCS: Task completed")

    def _take_photo(self, task_id: str, bin_code: str):
        """通过HTTP调用cam_sys拍照 (模拟请求-响应)"""
        try:
            # 发送HTTP POST请求到cam_sys
            payload = {
                "task_id": task_id,
                "bin_code": bin_code
            }
            response = requests.post(self.cam_sys_url, json=payload)
            response.raise_for_status()

            # 从cam_sys响应中获取照片信息
            result = response.json()
            logger.info("RCS: cam_sys response: %s", result)

            # 如果cam_sys返回成功，继续流程
            if result.get("status") == "success":
                logger.info("RCS: Photo saved by cam_sys at %s",
                            result.get("image_path"))
            else:
                logger.error("RCS: cam_sys error: %s",
                             result.get("message", "Unknown error"))
        except Exception as e:
            logger.error("RCS: Failed to call cam_sys: %s", str(e))
            # 回退到内部模拟拍照 (用于测试)
            self._simulate_internal_photo(task_id, bin_code)

    def _simulate_internal_photo(self, task_id: str, bin_code: str):
        """内部模拟拍照 (当cam_sys不可用时)"""
        # 创建模拟图片
        img = Image.new('RGB', (800, 600), color=(random.randint(
            0, 255), random.randint(0, 255), random.randint(0, 255)))
        img_io = io.BytesIO()
        img.save(img_io, format='PNG')
        img_data = img_io.getvalue()

        # 保存到SD卡 (使用模拟SD卡路径)
        image_path = os.path.join(
            self.image_dir, f"simulated_sd_{task_id}_{bin_code}.png")
        with open(image_path, "wb") as f:
            f.write(img_data)
        logger.info("RCS: Internal photo saved to %s", image_path)

    def _send_task_status(self, task_id: str, status: str):
        """发送任务状态到外部网关 (ZMQ)"""
        status_msg = f"task_status_update:{task_id},{status}"
        self.socket.send_string(status_msg)
        response = self.socket.recv_string()
        logger.info("RCS: Status update response: %s", response)

    def get_image(self, task_id: str):
        """获取指定任务的图片 (通过cam_sys的HTTP接口)"""
        # 实际系统中，这里会调用cam_sys的HTTP接口
        # 但为简化，我们直接从本地文件读取
        image_path = os.path.join(
            self.image_dir, f"simulated_sd_{task_id}_*.png")
        image_files = [f for f in os.listdir(
            self.image_dir) if f.startswith(f"simulated_sd_{task_id}_")]

        if image_files:
            image_file = image_files[0]
            image_path = os.path.join(self.image_dir, image_file)
            with open(image_path, "rb") as f:
                image_data = f.read()

            # 编码为Base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            return {
                "task_id": task_id,
                "image": image_base64,
                "format": "png"
            }
        else:
            logger.error("RCS: Image not found for task %s", task_id)
            return None


if __name__ == "__main__":
    # 初始化RCS模拟器
    rcs = RCSSimulator()

    # 模拟任务执行
    task_id = "TASK_001"
    bin_code = "BIN001"

    print("\n=== RCS SYSTEM SIMULATION ===")
    print(f"Starting task {task_id} for bin {bin_code}")
    rcs.simulate_task_execution(task_id, bin_code)

    print("\n=== RCS: Requesting image for task", task_id)
    image_data = rcs.get_image(task_id)
    if image_data:
        print("RCS: Image retrieved successfully (via cam_sys)")
        # 在实际系统中，这里会将图片发送给内部网关
    else:
        print("RCS: Failed to retrieve image")

    print("\n=== RCS SIMULATION COMPLETED ===")
