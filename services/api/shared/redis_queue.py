"""
Redis 队列工具：用于 gateway 和 inventory_worker 之间的任务分发
"""
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Redis 连接（lazy init）
_redis_client: Optional[Any] = None
_redis_last_fail: float = 0.0  # 上次连接失败的时间戳
_REDIS_RETRY_INTERVAL = 30     # 连接失败后 30 秒内不重试
_REDIS_HOST = "localhost"
_REDIS_PORT = 6379

# 队列/键名常量
PENDING_QUEUE = "inventory:pending_queue"           # 旧批量队列（废弃，仅保留接口兼容）
SINGLE_BIN_QUEUE = "inventory:single_bin_queue"   # 单bin队列（gateway → worker，逐个推送）
_RESULT_KEY_BASE = "inventory:task"               # 统一前缀
RESULT_KEY_PREFIX = "inventory:task:results:"     # 向后兼容，结果 key = results:{task_no}


def _get_redis():
    """获取 Redis 连接（lazy init，失败后 30 秒内不重试）"""
    import time as _time
    global _redis_client, _redis_last_fail
    if _redis_client is None:
        now = _time.time()
        if now - _redis_last_fail < _REDIS_RETRY_INTERVAL:
            return None
        try:
            import redis
            _redis_client = redis.Redis(host=_REDIS_HOST, port=_REDIS_PORT, decode_responses=True)
            _redis_client.ping()
            logger.info(f"[Redis] 连接成功: {_REDIS_HOST}:{_REDIS_PORT}")
        except Exception as e:
            logger.warning(f"[Redis] 连接失败: {e}，{_REDIS_RETRY_INTERVAL}秒后重试")
            _redis_client = None
            _redis_last_fail = now
    return _redis_client


def _to_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _from_json(s: str) -> Any:
    return json.loads(s)


# ==================== Gateway → Worker ====================

def push_task(task_no: str, bin_locations: List[str], task_info: Dict) -> bool:
    """
    gateway 调用：将盘点任务推入待处理队列
    task_info 包含：operator_name, is_sim, task_id 等元信息
    """
    client = _get_redis()
    if client is None:
        return False
    try:
        payload = _to_json({
            "task_no": task_no,
            "bin_locations": bin_locations,
            "task_info": task_info,
        })
        client.lpush(PENDING_QUEUE, payload)
        logger.info(f"[Redis] 任务入队: {task_no}, {len(bin_locations)} 个库位")
        return True
    except Exception as e:
        logger.error(f"[Redis] 入队失败: {e}")
        return False


def pop_task(timeout: int = 0) -> Optional[Dict]:
    """
    worker 调用：阻塞等待任务（BRPOP）
    timeout=0 表示无限等待
    返回: {"task_no": ..., "bin_locations": [...], "task_info": {...}}
    """
    client = _get_redis()
    if client is None:
        return None
    try:
        result = client.brpop(PENDING_QUEUE, timeout=timeout)
        if result:
            _, payload = result
            return _from_json(payload)
        return None
    except Exception as e:
        # BRPOP 超时是正常行为（队列为空），不记录为错误
        if "Timeout" in str(e):
            return None
        logger.error(f"[Redis] 读取任务失败: {e}")
        return None


# ==================== Worker → Gateway ====================

def push_bin_result(task_no: str, bin_location: str, result: Dict) -> bool:
    """
    worker 调用：写入单个库位的处理结果
    """
    client = _get_redis()
    if client is None:
        return False
    try:
        key = f"{RESULT_KEY_PREFIX}{task_no}"
        payload = _to_json({
            "bin_location": bin_location,
            "result": result,
        })
        client.lpush(key, payload)
        return True
    except Exception as e:
        logger.error(f"[Redis] 写入结果失败: {e}")
        return False


def get_bin_results(task_no: str) -> List[Dict]:
    """
    gateway 调用：读取某任务的所有已处理结果
    """
    client = _get_redis()
    if client is None:
        return []
    try:
        key = f"{RESULT_KEY_PREFIX}{task_no}"
        items = client.lrange(key, 0, -1)
        return [_from_json(item) for item in items]
    except Exception as e:
        logger.error(f"[Redis] 读取结果失败: {e}")
        return []


def clear_task_results(task_no: str) -> bool:
    """
    gateway 调用：任务完成后清除结果缓存
    """
    client = _get_redis()
    if client is None:
        return False
    try:
        key = f"{RESULT_KEY_PREFIX}{task_no}"
        client.delete(key)
        return True
    except Exception as e:
        logger.error(f"[Redis] 清除结果失败: {e}")
        return False


# ==================== 任务状态（Redis） ====================

def set_task_status(task_no: str, status: Dict) -> bool:
    """写入任务状态（gateway/worker 共用）"""
    client = _get_redis()
    if client is None:
        return False
    try:
        key = f"inventory:task:status:{task_no}"
        client.set(key, _to_json(status), ex=86400 * 7)  # 7天过期
        return True
    except Exception as e:
        logger.error(f"[Redis] 写入任务状态失败: {e}")
        return False


def get_task_status(task_no: str) -> Optional[Dict]:
    """读取任务状态"""
    client = _get_redis()
    if client is None:
        return None
    try:
        key = f"inventory:task:status:{task_no}"
        data = client.get(key)
        return _from_json(data) if data else None
    except Exception as e:
        logger.error(f"[Redis] 读取任务状态失败: {e}")
        return None


def delete_task_status(task_no: str) -> bool:
    """删除任务状态"""
    client = _get_redis()
    if client is None:
        return False
    try:
        key = f"inventory:task:status:{task_no}"
        client.delete(key)
        return True
    except Exception as e:
        logger.error(f"[Redis] 删除任务状态失败: {e}")
        return False


# ==================== 进度更新（Worker → Gateway） ====================

def append_bin_progress(task_no: str, bin_location: str, step: int) -> bool:
    """worker 每处理完一个库位，上报进度"""
    client = _get_redis()
    if client is None:
        return False
    try:
        key = f"inventory:task:progress:{task_no}"
        payload = _to_json({"bin_location": bin_location, "step": step})
        client.lpush(key, payload)
        return True
    except Exception as e:
        logger.error(f"[Redis] 写入进度失败: {e}")
        return False


def get_progress(task_no: str) -> List[Dict]:
    """gateway 读取进度"""
    client = _get_redis()
    if client is None:
        return []
    try:
        key = f"inventory:task:progress:{task_no}"
        items = client.lrange(key, 0, -1)
        return [_from_json(item) for item in items]
    except Exception as e:
        logger.error(f"[Redis] 读取进度失败: {e}")
        return []


# ==================== 轮询等待（Gateway 用） ====================

# ==================== 单bin队列（Gateway → Worker）====================

def push_single_bin_task(task_no: str, bin_location: str) -> bool:
    """
    gateway 调用：推送单个 bin 给 worker 处理
    """
    client = _get_redis()
    if client is None:
        return False
    try:
        payload = _to_json({
            "task_no": task_no,
            "bin_location": bin_location,
        })
        client.lpush(SINGLE_BIN_QUEUE, payload)
        logger.info(f"[Redis] 单bin入队: task={task_no}, bin={bin_location}")
        return True
    except Exception as e:
        logger.error(f"[Redis] 单bin入队失败: {e}")
        return False


def pop_single_bin_task(timeout: int = 5) -> Optional[Dict]:
    """
    worker 调用：阻塞消费单个 bin（timeout=5秒）
    返回: {"task_no": ..., "bin_location": ...}
    """
    client = _get_redis()
    if client is None:
        return None
    try:
        result = client.brpop(SINGLE_BIN_QUEUE, timeout=timeout)
        if result:
            _, payload = result
            return _from_json(payload)
        return None
    except Exception as e:
        # BRPOP 超时是正常行为（队列为空），不记录为错误
        if "Timeout" in str(e):
            return None
        logger.error(f"[Redis] 读取单bin任务失败: {e}")
        return None


def flush_single_bin_queue_by_task(task_no: str) -> int:
    """
    取消时清空队列中属于指定任务的条目，返回清空的数量。
    通过 LPOP 逐一弹出，非目标任务的条目暂存后全部推回。
    """
    client = _get_redis()
    if client is None:
        return 0
    try:
        other_tasks = []
        flushed = 0
        while True:
            result = client.lpop(SINGLE_BIN_QUEUE)
            if result is None:
                break
            parsed = _from_json(result)
            if parsed.get("task_no") == task_no:
                flushed += 1
            else:
                other_tasks.append(result)
        # 非目标任务推回队列头部（保持原有顺序）
        for item in reversed(other_tasks):
            client.rpush(SINGLE_BIN_QUEUE, item)
        if flushed > 0:
            logger.info(f"[Redis] 清空队列: task={task_no}, 清空 {flushed} 条")
        return flushed
    except Exception as e:
        logger.error(f"[Redis] 清空队列失败: {e}")
        return 0


# ==================== 已完成集合（Gateway 用）========================

def add_to_completed_set(task_no: str, set_name: str, bin_location: str) -> bool:
    """
    添加 bin 到已完成集合
    set_name: "rcs_completed" 或 "worker_completed"
    """
    client = _get_redis()
    if client is None:
        return False
    try:
        key = f"{_RESULT_KEY_BASE}:{set_name}:{task_no}"
        client.sadd(key, bin_location)
        return True
    except Exception as e:
        logger.error(f"[Redis] 添加到已完成集合失败: {e}")
        return False


def get_completed_count(task_no: str, set_name: str) -> int:
    """获取已完成集合中的 bin 数量"""
    client = _get_redis()
    if client is None:
        return 0
    try:
        key = f"{_RESULT_KEY_BASE}:{set_name}:{task_no}"
        return client.scard(key)
    except Exception:
        return 0


def is_bin_completed(task_no: str, set_name: str, bin_location: str) -> bool:
    """判断 bin 是否已在已完成集合中"""
    client = _get_redis()
    if client is None:
        return False
    try:
        key = f"{_RESULT_KEY_BASE}:{set_name}:{task_no}"
        return client.sismember(key, bin_location)
    except Exception:
        return False


def clear_task_sets(task_no: str) -> bool:
    """任务结束时清空 rcs_completed 和 worker_completed 两个集合"""
    client = _get_redis()
    if client is None:
        return False
    try:
        rcs_key = f"{_RESULT_KEY_BASE}:rcs_completed:{task_no}"
        worker_key = f"{_RESULT_KEY_BASE}:worker_completed:{task_no}"
        client.delete(rcs_key, worker_key)
        logger.info(f"[Redis] 清空任务集合: task={task_no}")
        return True
    except Exception as e:
        logger.error(f"[Redis] 清空任务集合失败: {e}")
        return False


async def wait_for_bin_result(task_no: str, bin_location: str, timeout: int = 0) -> Optional[Dict]:
    """
    Gateway 轮询等待某个库位的检测结果（async，不阻塞事件循环）。
    timeout=0 表示无限等待（直到任务完成或 Redis 不可用）。
    返回: {"bin_location": ..., "result": {...}}
    """
    import asyncio
    client = _get_redis()
    if client is None:
        return None
    key = f"{RESULT_KEY_PREFIX}{task_no}"
    elapsed = 0
    interval = 0.5
    while timeout == 0 or elapsed < timeout:
        try:
            items = client.lrange(key, 0, -1)
            for item in items:
                parsed = _from_json(item)
                if parsed.get("bin_location") == bin_location:
                    client.lrem(key, 1, item)
                    return parsed
        except Exception as e:
            logger.error(f"[Redis] 轮询结果失败: {e}")
            return None
        await asyncio.sleep(interval)
        elapsed += interval
    logger.warning(f"[Redis] 等待库位 {bin_location} 结果超时（{timeout}s）")
    return None
