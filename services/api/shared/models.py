"""
共享数据模型
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class OperationLog(BaseModel):
    """操作记录模型"""
    id: str  # 格式: YYYYMMDD_HHMMSS_xxx
    timestamp: str  # ISO格式时间戳
    operation_type: str  # 操作类型
    user_id: Optional[str] = None  # 操作用户ID
    user_name: Optional[str] = None  # 操作用户名
    action: str  # 具体动作
    target: Optional[str] = None  # 操作目标（如任务ID、用户名）
    status: str  # 成功/失败/进行中
    details: Dict[str, Any] = {}  # 详细数据
    ip_address: Optional[str] = None  # 操作IP
    metadata: Dict[str, Any] = {}  # 元数据


class TaskStatus(BaseModel):
    """任务状态模型"""
    task_no: str
    status: str  # init, running, completed, failed
    current_step: int = 0
    total_steps: int = 0
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class BinLocationStatus(BaseModel):
    """储位状态模型"""
    bin_location: str
    status: str  # pending, running, completed, failed
    sequence: int = 0
    image_data: Optional[Dict[str, Any]] = None
    compute_result: Optional[Dict[str, Any]] = None
    capture_time: Optional[str] = None
    compute_time: Optional[str] = None
    detect_result: Optional[Dict[str, Any]] = None  # Detect模块识别结果
    barcode_result: Optional[Dict[str, Any]] = None  # Barcode模块识别结果
    recognition_time: Optional[str] = None  # 识别时间


class InventoryTaskProgress(BaseModel):
    """盘点任务进度模型"""
    task_no: str
    status: str
    current_step: int
    total_steps: int
    progress_percentage: float
    bin_locations: List[BinLocationStatus]
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class ScanAndRecognizeRequest(BaseModel):
    """扫码+识别请求模型"""
    taskNo: str  # 任务编号
    binLocation: str  # 库位号
    pile_id: int = 1  # 堆垛ID，默认为1
    code_type: str = "ucc128"  # 条码类型，默认ucc128


class FrontendLogRequest(BaseModel):
    """前端日志请求模型"""
    level: str  # log, info, warn, error
    message: str
    timestamp: Optional[str] = None
    source: Optional[str] = None  # 前端来源标识
    extra: Optional[Dict[str, Any]] = None  # 额外信息
