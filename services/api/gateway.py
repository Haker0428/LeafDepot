"""
Gateway服务 - API 网关入口点

将所有服务模块的路由聚合到一起，提供统一的 API 入口。
"""
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入共享配置和日志
from services.api.shared.config import logger, logs_dir, CORS_ORIGINS
from services.api.shared.operation_log import log_operation

# 导入各服务模块的路由
from services.api.auth.router import router as auth_router
from services.api.inventory.router import router as inventory_router
from services.api.lms.router import router as lms_router
from services.api.robot.router import router as robot_router
from services.api.log.router import router as log_router
from services.api.history.router import router as history_router
from services.api.common.router import router as common_router
from services.api.config.router import router as config_router

# 条形码路由（可选）
ENABLE_BARCODE = os.getenv("ENABLE_BARCODE", "true").lower() in ("true", "1", "yes")
if ENABLE_BARCODE:
    try:
        from services.api.routers.barcode import router as barcode_router
        BARCODE_ROUTER_AVAILABLE = True
    except ImportError:
        logger.warning("条形码路由模块未找到，跳过注册")
        BARCODE_ROUTER_AVAILABLE = False
else:
    BARCODE_ROUTER_AVAILABLE = False

# 创建 FastAPI 应用实例
app = FastAPI(
    title="LeafDepot API Gateway",
    description="LeafDepot 烟草码垛系统 API 网关服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS（从配置文件读取）
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# 注册各服务模块的路由
app.include_router(auth_router)
app.include_router(inventory_router)
app.include_router(lms_router)
app.include_router(robot_router)
app.include_router(log_router)
app.include_router(history_router)
app.include_router(common_router)
app.include_router(config_router)

# 注册条形码路由（可选）
if ENABLE_BARCODE and BARCODE_ROUTER_AVAILABLE:
    app.include_router(barcode_router)
    logger.info("条形码路由已启用")

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "gateway"}

# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "LeafDepot API Gateway",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("🚀 Gateway服务启动")
    logger.info("📡 API地址: http://0.0.0.0:8000")
    logger.info("📚 API文档: http://10.16.82.95:8000/docs")
    logger.info(f"📝 日志目录: {logs_dir}")

    # 记录启动日志
    log_operation(
        operation_type="system",
        action="服务启动",
        status="success",
        details={"version": "1.0.0"}
    )


# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Gateway服务关闭")
    log_operation(
        operation_type="system",
        action="服务关闭",
        status="success"
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
