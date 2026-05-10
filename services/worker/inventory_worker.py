#!/usr/bin/env python3
"""
Inventory Worker: 从 Redis 队列消费盘点任务，执行 Phase 2（拍照+识别），
将结果写回 Redis，供 gateway 消费。

用法:
    conda run -n tobacco_env python services/worker/inventory_worker.py

前置条件:
    - Redis 服务运行中
    - gateway 已通过 push_task() 推送任务
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

from services.api.shared.redis_queue import pop_task, push_bin_result, set_task_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WORKER] %(levelname)s %(message)s",
)
logger = logging.getLogger("inventory_worker")


async def process_one_bin(task_no: str, bin_location: str, is_sim: bool) -> dict:
    """执行单个库位的检测，返回结果 dict"""
    from services.api.shared.detection_runner import run_detection
    return await run_detection(task_no, bin_location, is_sim)


async def run_worker_loop():
    """主循环：阻塞等待任务，完成后写入 Redis"""
    logger.info("Inventory Worker 启动，等待任务...")

    while True:
        try:
            # 阻塞等待任务（无限等待）
            task = pop_task(timeout=0)
            if task is None:
                await asyncio.sleep(1)
                continue

            task_no = task.get("task_no", "?")
            bin_locations = task.get("bin_locations", [])
            task_info = task.get("task_info", {})
            is_sim = task_info.get("is_sim", False)

            logger.info(f"[{task_no}] 收到任务: {len(bin_locations)} 个库位, is_sim={is_sim}")
            set_task_status(task_no, {"worker_status": "processing", "total": len(bin_locations), "done": 0})

            for i, bin_location in enumerate(bin_locations):
                logger.info(f"[{task_no}] 处理库位 {i+1}/{len(bin_locations)}: {bin_location}")
                try:
                    result = await process_one_bin(task_no, bin_location, is_sim)
                    push_bin_result(task_no, bin_location, result)
                    logger.info(f"[{task_no}] 库位 {bin_location} 完成: status={result.get('status')}, qty={result.get('actualQuantity')}")
                except Exception as e:
                    logger.error(f"[{task_no}] 库位 {bin_location} 异常: {e}")
                    error_result = {
                        "binLocation": bin_location,
                        "status": "异常",
                        "error": str(e),
                        "actualQuantity": None,
                        "actualSpec": "无",
                        "photo3dPath": None,
                        "photoDepthPath": None,
                        "photoScan1Path": "",
                        "photoScan2Path": "",
                    }
                    push_bin_result(task_no, bin_location, error_result)

                set_task_status(task_no, {"worker_status": "processing", "total": len(bin_locations), "done": i + 1})

            set_task_status(task_no, {"worker_status": "completed"})
            logger.info(f"[{task_no}] 全部 {len(bin_locations)} 个库位处理完成")

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
