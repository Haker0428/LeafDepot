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
_REDIS_HOST = "10.16.82.95"
_REDIS_PORT = 6379

# 队列/键名常量
PENDING_QUEUE = "inventory:pending_queue"           # 待处理任务队列（gateway → worker）
RESULT_KEY_PREFIX = "inventory:task:results:"     # 结果存储（worker → gateway），格式: results:{task_no}


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
