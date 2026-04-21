"""
WebSocket 连接管理器

负责：
- 管理所有 WebSocket 客户端连接
- 广播任务状态变更通知（如其他人的任务完成）
"""
import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger("websocket")


class WebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # task_no -> set of websocket connections watching this task
        self._task_subscriptions: Dict[str, Set[WebSocket]] = {}
        # all connections (for broadcast)
        self._all_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, task_no: str = ""):
        """客户端连接并订阅任务"""
        await websocket.accept()
        async with self._lock:
            self._all_connections.add(websocket)
            if task_no:
                if task_no not in self._task_subscriptions:
                    self._task_subscriptions[task_no] = set()
                self._task_subscriptions[task_no].add(websocket)
        logger.info(f"[WS] 客户端连接，当前总数={len(self._all_connections)}，订阅任务={task_no or '全局'}")

    async def disconnect(self, websocket: WebSocket, task_no: str = ""):
        """客户端断开连接"""
        async with self._lock:
            self._all_connections.discard(websocket)
            if task_no and task_no in self._task_subscriptions:
                self._task_subscriptions[task_no].discard(websocket)
                if not self._task_subscriptions[task_no]:
                    del self._task_subscriptions[task_no]
        logger.info(f"[WS] 客户端断开，当前总数={len(self._all_connections)}")

    async def subscribe(self, websocket: WebSocket, task_no: str):
        """订阅指定任务的更新"""
        async with self._lock:
            if task_no not in self._task_subscriptions:
                self._task_subscriptions[task_no] = set()
            self._task_subscriptions[task_no].add(websocket)

    async def broadcast_task_event(self, event: str, task_no: str, data: dict = None):
        """广播任务事件给所有连接的客户端

        event 类型：
        - "task_completed": 任务完成
        - "task_failed": 任务失败
        - "task_cancelled": 任务被取消
        """
        message = json.dumps({
            "event": event,
            "taskNo": task_no,
            "data": data or {},
        }, ensure_ascii=False)

        async with self._lock:
            dead_connections = set()
            for conn in self._all_connections:
                try:
                    await conn.send_text(message)
                except Exception:
                    dead_connections.add(conn)

            # 清理断开的连接
            for conn in dead_connections:
                self._all_connections.discard(conn)

            logger.info(f"[WS] 广播事件 {event} taskNo={task_no}，共 {len(self._all_connections) - len(dead_connections)} 个客户端")


# 全局单例
ws_manager = WebSocketManager()
