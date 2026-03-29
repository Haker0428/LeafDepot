"""
操作日志功能
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from services.api.shared.models import OperationLog
from services.api.shared.config import debug_log_dir, logger

# 操作记录存储根目录
OPERATION_LOGS_DIR = debug_log_dir / "operation_logs"
OPERATION_LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 创建各类型子目录
LOG_TYPES = ["inventory", "user_login", "user_management", "system_cleanup", "other"]
for log_type in LOG_TYPES:
    (OPERATION_LOGS_DIR / log_type).mkdir(parents=True, exist_ok=True)


def generate_operation_id() -> str:
    """生成操作记录ID"""
    import time
    return datetime.now().strftime("%Y%m%d_%H%M%S_") + str(int(time.time() * 1000))[-3:]


def save_operation_log(operation_log: OperationLog) -> bool:
    """保存操作记录到文件"""
    try:
        log_type = operation_log.operation_type
        if log_type not in LOG_TYPES:
            log_type = "other"

        log_dir = OPERATION_LOGS_DIR / log_type
        filename = f"{operation_log.id}.json"
        filepath = log_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(operation_log.dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"操作记录已保存: {filepath}")
        return True
    except Exception as e:
        logger.error(f"保存操作记录失败: {str(e)}")
        return False


def log_operation(
    operation_type: str,
    action: str,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    target: Optional[str] = None,
    status: str = "success",
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """记录操作的辅助函数"""
    operation_log = OperationLog(
        id=generate_operation_id(),
        timestamp=datetime.now().isoformat(),
        operation_type=operation_type,
        user_id=user_id,
        user_name=user_name,
        action=action,
        target=target,
        status=status,
        details=details or {},
        ip_address=ip_address,
        metadata=metadata or {}
    )

    return save_operation_log(operation_log)


def get_recent_operations(limit: int = 5, days: int = 180, exclude_system: bool = True) -> List[Dict[str, Any]]:
    """获取最近的操作记录

    Args:
        limit: 返回记录数量限制
        days: 查询天数范围
        exclude_system: 是否排除系统操作（如服务启动）
    """
    try:
        all_operations = []
        cutoff_date = datetime.now() - timedelta(days=days)

        for log_type in LOG_TYPES:
            log_dir = OPERATION_LOGS_DIR / log_type
            if not log_dir.exists():
                continue

            json_files = list(log_dir.glob("*.json"))

            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # 排除系统操作（如服务启动、服务关闭）
                    if exclude_system and data.get("operation_type") == "system":
                        continue

                    log_time_str = data.get("timestamp", "")
                    if log_time_str:
                        try:
                            log_time = datetime.fromisoformat(log_time_str.replace('Z', '+00:00'))
                            if log_time < cutoff_date:
                                continue
                        except:
                            pass

                    all_operations.append(data)
                except Exception as e:
                    logger.warning(f"读取操作记录文件失败 {json_file}: {str(e)}")
                    continue

        all_operations.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return all_operations[:limit]

    except Exception as e:
        logger.error(f"获取操作记录失败: {str(e)}")
        return []


def get_all_operations(days: int = 180, exclude_system: bool = True) -> List[Dict[str, Any]]:
    """获取指定天数内的所有操作记录

    Args:
        days: 查询天数范围
        exclude_system: 是否排除系统操作（如服务启动）
    """
    try:
        all_operations = []
        cutoff_date = datetime.now() - timedelta(days=days)

        for log_type in LOG_TYPES:
            log_dir = OPERATION_LOGS_DIR / log_type
            if not log_dir.exists():
                continue

            json_files = list(log_dir.glob("*.json"))

            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # 排除系统操作（如服务启动、服务关闭）
                    if exclude_system and data.get("operation_type") == "system":
                        continue

                    log_time_str = data.get("timestamp", "")
                    if log_time_str:
                        try:
                            log_time = datetime.fromisoformat(log_time_str.replace('Z', '+00:00'))
                            if log_time < cutoff_date:
                                continue
                        except:
                            pass

                    all_operations.append(data)
                except Exception as e:
                    logger.warning(f"读取操作记录文件失败 {json_file}: {str(e)}")
                    continue

        all_operations.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return all_operations

    except Exception as e:
        logger.error(f"获取所有操作记录失败: {str(e)}")
        return []
