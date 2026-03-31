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

# 配置日志
debug_log_dir = project_root / "debug"
debug_log_dir.mkdir(parents=True, exist_ok=True)

# 创建日志文件路径（按日期命名）
_log_filename = debug_log_dir / \
    f"gateway_{datetime.now().strftime('%Y%m%d')}.log"

# 配置根日志记录器
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # 控制台输出
        logging.FileHandler(str(_log_filename), encoding='utf-8')  # 文件输出
    ]
)
logger = logging.getLogger(__name__)

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

# 服务地址配置
LMS_BASE_URL = os.getenv("LMS_BASE_URL", "http://10.16.82.95:6000")
RCS_BASE_URL = os.getenv("RCS_BASE_URL", "http://10.16.82.95:4001")
RCS_PREFIX = os.getenv("RCS_PREFIX", "")

# 模拟模式配置（从 JSON 文件读取）
IS_SIM = _config.get("is_sim", True)

# 模拟模式下是否执行真实相机脚本
WITH_CAMERA = _config.get("with_camera", False)

# 检测调试配置（从 JSON 文件读取）
ENABLE_DEBUG = _config.get("enable_debug", False)
ENABLE_VISUALIZATION = _config.get("enable_visualization", False)

# CORS 配置（从 JSON 文件读取）
CORS_ORIGINS = _config.get("cors_origins", [
    "http://10.16.82.95",
    "http://10.16.82.95:8000",
    "http://10.16.82.95:5173",
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5173",
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
