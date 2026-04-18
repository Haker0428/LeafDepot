"""
任务持久化状态管理
将任务运行状态写入 task_state.json，服务器重启后可识别中断任务
"""
import json
from pathlib import Path
from datetime import datetime

from services.api.shared.config import logger, project_root

STATE_FILE = project_root / "output" / "task_state.json"


def _load() -> dict:
    """加载状态文件"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"加载 task_state.json 失败: {e}")
    return {}


def _save(data: dict):
    """保存状态文件"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error(f"保存 task_state.json 失败: {e}")


def mark_running(task_no: str, total_bins: int):
    """工作流启动时调用，标记任务为 running"""
    data = _load()
    data[task_no] = {
        "status": "running",
        "total_bins": total_bins,
        "completed_bins": 0,
        "started_at": datetime.now().isoformat(),
    }
    _save(data)
    logger.info(f"[task_state] 任务启动: {task_no}")


def update_progress(task_no: str, completed_bins: int):
    """每处理完一个 bin 后调用，更新完成进度"""
    data = _load()
    if task_no in data and data[task_no].get("status") == "running":
        data[task_no]["completed_bins"] = completed_bins
        _save(data)


def mark_finished(task_no: str, final_status: str):
    """工作流正常结束时调用，标记最终状态"""
    data = _load()
    if task_no in data:
        data[task_no]["status"] = final_status
        data[task_no]["finished_at"] = datetime.now().isoformat()
        _save(data)
        logger.info(f"[task_state] 任务结束: {task_no} -> {final_status}")


def get_running_tasks() -> dict:
    """返回所有 status == 'running' 的任务（服务器重启后扫描用）"""
    data = _load()
    return {k: v for k, v in data.items() if v.get("status") == "running"}


def clear_task(task_no: str):
    """取消任务时调用，移除持久化状态"""
    data = _load()
    if task_no in data:
        del data[task_no]
        _save(data)
        logger.info(f"[task_state] 任务已清除: {task_no}")


def on_server_startup():
    """Gateway 启动时自动调用：把所有 running 任务标记为 interrupted"""
    running = get_running_tasks()
    if not running:
        return
    for task_no in list(running.keys()):
        data = _load()
        if task_no in data and data[task_no].get("status") == "running":
            data[task_no]["status"] = "interrupted"
            data[task_no]["finished_at"] = datetime.now().isoformat()
            _save(data)
            logger.info(f"[task_state] 检测到中断任务，已标记为 interrupted: {task_no}")
