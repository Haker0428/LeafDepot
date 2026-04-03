"""
共享模块 - 提供跨模块的通用功能
"""
from services.api.shared.models import (
    OperationLog,
    TaskStatus,
    BinLocationStatus,
    InventoryTaskProgress,
    ScanAndRecognizeRequest,
    FrontendLogRequest,
)
from services.api.shared.config import (
    LMS_BASE_URL,
    RCS_BASE_URL,
    RCS_PREFIX,
    CAPTURE_SCRIPTS,
    STACK_TYPE_TO_CODE,
    STACK_TYPE_CODE_TO_PILE_ID,
    ENABLE_BARCODE,
    logger,
    logs_dir,
    project_root,
)
from services.api.shared.operation_log import (
    generate_operation_id,
    save_operation_log,
    log_operation,
    get_recent_operations,
    get_all_operations,
    OPERATION_LOGS_DIR,
    LOG_TYPES,
)
from services.api.shared.tobacco_resolver import (
    TobaccoCaseInfoResolver,
    get_tobacco_case_resolver,
)

__all__ = [
    # Models
    "OperationLog",
    "TaskStatus",
    "BinLocationStatus",
    "InventoryTaskProgress",
    "ScanAndRecognizeRequest",
    "FrontendLogRequest",
    # Config
    "LMS_BASE_URL",
    "RCS_BASE_URL",
    "RCS_PREFIX",
    "CAPTURE_SCRIPTS",
    "STACK_TYPE_TO_CODE",
    "STACK_TYPE_CODE_TO_PILE_ID",
    "ENABLE_BARCODE",
    "logger",
    "logs_dir",
    "project_root",
    # Operation Log
    "generate_operation_id",
    "save_operation_log",
    "log_operation",
    "get_recent_operations",
    "get_all_operations",
    "OPERATION_LOGS_DIR",
    "LOG_TYPES",
    # Tobacco Resolver
    "TobaccoCaseInfoResolver",
    "get_tobacco_case_resolver",
]
