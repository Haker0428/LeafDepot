"""
公共配置路由：向前端提供网关地址等运行时配置
"""
from fastapi import APIRouter
from services.api.shared.config import _HOST, GATEWAY_PORT

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/gateway")
async def get_gateway_url():
    """
    返回网关 URL，供前端动态发现
    """
    return {"gateway_url": f"http://{_HOST}:{GATEWAY_PORT}"}
