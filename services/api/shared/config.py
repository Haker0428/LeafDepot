"""
配置常量
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# 项目根目录
project_root = Path(__file__).parent.parent.parent.parent

# 日志目录（与 manage.sh 重定向路径保持一致）
logs_dir = project_root / "logs"
try:
    logs_dir.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"[FATAL] 无法创建日志目录 {logs_dir}: {e}")

# 创建日志文件路径（按日期命名）
_log_filename = logs_dir / \
    f"gateway_{datetime.now().strftime('%Y%m%d')}.log"

# 配置根日志记录器（basicConfig 只在 root handler 为空时生效）
_handlers = []
_stream_handler = logging.StreamHandler()
_stream_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'))
_handlers.append(_stream_handler)

try:
    _file_handler = logging.FileHandler(str(_log_filename), encoding='utf-8')
    _file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'))
    _handlers.append(_file_handler)
    print(f"[LOG] 日志文件: {_log_filename}")
except Exception as e:
    print(f"[WARN] 无法创建日志文件 {_log_filename}: {e}")

_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)
_root_logger.handlers = _handlers  # 替换而非追加，避免重复 handler
logger = logging.getLogger(__name__)

# 专用 RCS 日志：写入 rcs_*.log
_rcs_log_file = logs_dir / f"rcs_{datetime.now().strftime('%Y%m%d')}.log"
try:
    _rcs_handler = logging.FileHandler(str(_rcs_log_file), encoding='utf-8')
    _rcs_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'))
    _rcs_logger = logging.getLogger("rcs")
    _rcs_logger.setLevel(logging.INFO)
    _rcs_logger.addHandler(_rcs_handler)
    _rcs_logger.propagate = False
    print(f"[LOG] RCS 日志文件: {_rcs_log_file}")
except Exception as e:
    print(f"[WARN] 无法创建 RCS 日志文件 {_rcs_log_file}: {e}")
    _rcs_logger = logging.getLogger("rcs")

rcs_logger = _rcs_logger  # 导出供其他模块使用

# 从 JSON 配置文件读取配置
_config_file = project_root / "config.json"
_config = {}

if _config_file.exists():
    try:
        with open(_config_file, 'r', encoding='utf-8') as f:
            _config = json.load(f)
        logger.info(f"已加载配置文件: {_config_file}")
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")

# 服务地址统一从 config.json 派生（修改 host 即可全局生效）
_HOST = _config.get("host", "localhost")
_PORTS = _config.get("ports", {})
LMS_PORT = _PORTS.get("lms", 6000)
RCS_PORT = _PORTS.get("rcs", 4001)
GATEWAY_PORT = _PORTS.get("gateway", 8000)
CAMSYS_PORT = _PORTS.get("camsys", 5000)
FRONTEND_PORT = _config.get("frontend_port", 5173)

LMS_BASE_URL = os.getenv("LMS_BASE_URL", f"http://{_HOST}:{LMS_PORT}")
RCS_BASE_URL = os.getenv("RCS_BASE_URL", f"http://{_HOST}:{RCS_PORT}")
RCS_PREFIX = os.getenv("RCS_PREFIX") or _config.get("rcs_prefix", "/rcs/rtas")
LMS_PREFIX = os.getenv("LMS_PREFIX") or _config.get("lms_prefix", "/lms/srm")

# 完整的 RCS URL（base + prefix），避免两个变量分开导入的拼接问题
RCS_FULL_URL = RCS_BASE_URL.rstrip("/") + RCS_PREFIX

# 真实 RCS 配置（用于 is_sim=False 模式）
RCS_REAL = _config.get("rcs_real", {})

# RCS 回调地址（真实模式由 RCS 回调此地址通知任务状态）
# 优先使用 config.json 中 rcs_real.callback_url，否则从 host + gateway_port 派生
RCS_CALLBACK_URL = RCS_REAL.get("callback_url", f"http://{_HOST}:{GATEWAY_PORT}/api/robot/reporter/task")

logger.info(f"[{datetime.now().isoformat()}] HOST={_HOST}, LMS_BASE_URL={LMS_BASE_URL}, RCS_BASE_URL={RCS_BASE_URL}, RCS_FULL_URL={RCS_FULL_URL}")

# 模拟模式配置（从 JSON 文件读取）
IS_SIM = _config.get("is_sim", True)

# 模拟模式下是否执行真实相机脚本
WITH_CAMERA = _config.get("with_camera", False)

# 本地测试图片目录（使用本地图片替代真实相机，用于无相机环境调试）
# 格式：目录中放 3d_camera/main.jpg, 3d_camera/depth.jpg,
#       scan_camera_1/main.jpg, scan_camera_2/main.jpg
CAMERA_TEST_DIR = _config.get("camera_test_dir", "")

# 检测调试配置（从 JSON 文件读取）
ENABLE_DEBUG = _config.get("enable_debug", False)
ENABLE_VISUALIZATION = _config.get("enable_visualization", False)

# CORS 配置（从 JSON 文件读取）
CORS_ORIGINS = _config.get("cors_origins", [
    f"http://{_HOST}", f"http://{_HOST}:{GATEWAY_PORT}",
    f"http://{_HOST}:{FRONTEND_PORT}", "http://localhost", f"http://localhost:{GATEWAY_PORT}",
    f"http://localhost:{FRONTEND_PORT}",
])

# 模拟用户配置（LMS 不可用时使用）
MOCK_USER = {
    "userId": "1000000",
    "userName": "管理员账号",
    "userCode": "admin",
    "userLevel": "admin"
}

logger.info(f"配置加载完成: CORS_ORIGINS={len(CORS_ORIGINS)}个")

# 抓图脚本路径
CAPTURE_SCRIPTS = [
    str(project_root / "hardware" / "cam_sys" / "build" / "scan_1_capture.py"),
    str(project_root / "hardware" / "cam_sys" / "build" / "scan_2_capture.py"),
    str(project_root / "hardware" / "cam_sys" / "build" / "3d_capture.py"),
]

# 垛型字符串 → 垛型编码 映射
STACK_TYPE_TO_CODE = {
    "5*8": 0,
    "5*6": 1,
    "5*5": 2,
    "3*10": 3,
    "4*7+2": 4,
}

# 垛型编码 → pile_id 映射（对应 pile_config.json）
STACK_TYPE_CODE_TO_PILE_ID = {
    0: 2,   # "5*8"   → pile_id=2
    1: 3,   # "5*6"   → pile_id=3
    2: 5,   # "5*5"   → pile_id=5
    3: 1,   # "3*10"  → pile_id=1
    4: 4,   # "4*7+2" → pile_id=4
    -1: 1,  # unknown → default
}

# Barcode功能开关
ENABLE_BARCODE = os.getenv(
    "ENABLE_BARCODE", "true").lower() in ("true", "1", "yes")

# 检测模块可用性
try:
    from core.detection import count_boxes
    DETECT_MODULE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"检测模块导入失败: {e}")
    DETECT_MODULE_AVAILABLE = False

# 条码识别模块可用性
BARCODE_MODULE_AVAILABLE = False
if ENABLE_BARCODE:
    try:
        from core.vision.barcode_recognizer import BarcodeRecognizer
        BARCODE_MODULE_AVAILABLE = True
        logger.info("条形码识别模块已启用")
    except ImportError as e:
        logger.warning(f"条形码识别模块导入失败: {e}")
        BARCODE_MODULE_AVAILABLE = False
else:
    logger.info("条形码识别模块已禁用（ENABLE_BARCODE=false）")
