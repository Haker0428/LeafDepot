#!/usr/bin/env python3
"""
Inventory Worker: 从 Redis 单bin队列消费任务，读取 gateway 已拍好的照片，执行检测，
将结果写回 Redis，供 gateway 收集。

gateway 负责拍照，worker 只负责检测。

用法:
    conda run -n tobacco_env python services/worker/inventory_worker.py

前置条件:
    - Redis 服务运行中
    - gateway 通过 push_single_bin_task() 推送任务
"""
import os
import sys
import asyncio
import logging
import signal
from pathlib import Path

# 设置 project_root
_current_file = Path(__file__).resolve()
_services_dir = _current_file.parent.parent  # services/
_project_root = _services_dir.parent  # LeafDepot 根目录
sys.path.insert(0, str(_project_root))

from services.api.shared.redis_queue import (
    pop_single_bin_task,
    push_bin_result,
    add_to_completed_set,
)
from services.api.shared.config import CAMERA_TEST_DIR, IS_SIM, logs_dir
from datetime import datetime

# 设置 worker 日志文件（独立于 gateway，不调用 set_service_name 避免覆盖 gateway 的 root logger）
_worker_log_file = logs_dir / f"worker_{datetime.now().strftime('%Y%m%d')}.log"

# 设置 root logger，让所有 services.api.* 子 logger 都写到 worker 文件
_root_logger = logging.getLogger()
_root_logger.handlers = []  # 清掉继承的 handler（gateway 可能已经配置过）
_root_logger.setLevel(logging.DEBUG)
_root_fh = logging.FileHandler(str(_worker_log_file), encoding='utf-8')
_root_fh.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'))
_root_logger.addHandler(_root_fh)

# worker 自己的 logger
logger = logging.getLogger("inventory_worker")

# 让 core.* 日志不传到 root logger，避免重复打印
_core_logger = logging.getLogger("core")
for h in list(_core_logger.handlers):
    _core_logger.removeHandler(h)
_core_logger.propagate = False
_core_logger.setLevel(logging.DEBUG)
_core_fh = logging.FileHandler(str(_worker_log_file), encoding='utf-8')
_core_fh.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'))
_core_logger.addHandler(_core_fh)


async def process_one_bin(task_no: str, bin_location: str, is_sim: bool) -> dict:
    """执行单个库位的检测，返回结果 dict"""
    from services.api.shared.detection_runner import run_detection
    return await run_detection(task_no, bin_location, is_sim)


async def run_worker_loop():
    """主循环：从单bin队列消费，检测，写 Redis"""
    logger.info("Inventory Worker 启动，等待任务...")

    while True:
        try:
            # 阻塞等待单bin任务（超时5秒，队列为空时循环继续）
            task = pop_single_bin_task(timeout=5)
            if task is None:
                continue

            task_no = task.get("task_no", "?")
            bin_location = task.get("bin_location", "?")
            # camera_test_dir 不为空时走模拟图片，worker 可以处理
            use_sim_images = IS_SIM or bool(CAMERA_TEST_DIR)

            logger.info(f"[{task_no}] 收到任务: bin={bin_location}")

            try:
                result = await process_one_bin(task_no, bin_location, use_sim_images)
                push_bin_result(task_no, bin_location, result)
                logger.info(f"[{task_no}] 库位 {bin_location} 检测完成: status={result.get('status')}, qty={result.get('actualQuantity')}")
            except Exception as e:
                logger.error(f"[{task_no}] 库位 {bin_location} 检测异常: {e}")
                result = {
                    "status": "异常",
                    "error": str(e),
                    "actualQuantity": -1,
                    "actualSpec": "未识别",
                    "photo3dPath": None,
                    "photoDepthPath": None,
                    "photoScan1Path": "",
                    "photoScan2Path": "",
                }
                push_bin_result(task_no, bin_location, result)

            # 标记 worker 完成
            add_to_completed_set(task_no, "worker_completed", bin_location)
            logger.info(f"[{task_no}] 库位 {bin_location} 已标记完成: worker_completed")

        except Exception as e:
            logger.error(f"Worker 主循环异常: {e}")
            await asyncio.sleep(5)


def main():
    logger.info("=" * 60)
    logger.info("Inventory Worker 进程启动")
    logger.info(f"PID: {os.getpid()}")
    logger.info("=" * 60)

    # SIGTERM / SIGINT 处理，确保优雅退出
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown(signum, frame):
        logger.info("收到退出信号，停止 Worker...")
        for task in asyncio.all_tasks(loop):
            task.cancel()
        loop.stop()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        loop.run_until_complete(run_worker_loop())
    except KeyboardInterrupt:
        logger.info("Worker 被中断，退出")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
