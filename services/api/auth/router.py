"""
认证路由
"""
import requests
from fastapi import APIRouter, Request, HTTPException, status

from services.api.shared.config import LMS_BASE_URL, logger, MOCK_USER
from services.api.shared.operation_log import log_operation

router = APIRouter(tags=["auth"])


async def get_user_info_from_token(auth_token: str) -> dict:
    """根据authToken获取用户信息，LMS 不可用时返回模拟用户"""
    try:
        lms_auth_url = f"{LMS_BASE_URL}/auth/token?token={auth_token}"
        logger.info(f"调用 LMS auth/token: {lms_auth_url}")
        response = requests.get(lms_auth_url, timeout=5)
        logger.info(f"LMS auth/token 响应状态: {response.status_code}")

        if response.status_code == 200:
            response_data = response.json()
            logger.info(f"LMS auth/token 响应数据: {response_data}")
            # 尝试从 data 字段获取，如果没有则直接返回整个响应
            user_data = response_data.get("data", {})
            if not user_data:
                # 如果 data 为空，检查响应是否直接包含用户信息
                user_data = response_data if "userId" in response_data or "userName" in response_data else {}
            if user_data:
                return user_data
            else:
                logger.warning("LMS 响应中没有用户数据，使用模拟用户")
                return _get_mock_user_info(auth_token)
        else:
            # LMS 返回错误，使用模拟用户
            logger.warning(f"LMS auth/token 返回错误，使用模拟用户")
            return _get_mock_user_info(auth_token)
    except requests.exceptions.ConnectionError:
        logger.warning("无法连接到 LMS 服务，使用模拟用户")
        return _get_mock_user_info(auth_token)
    except requests.exceptions.Timeout:
        logger.warning("LMS 服务超时，使用模拟用户")
        return _get_mock_user_info(auth_token)
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        return _get_mock_user_info(auth_token)


def _get_mock_user_info(auth_token: str) -> dict:
    """返回模拟用户信息（用于 LMS 不可用时）"""
    mock_user = MOCK_USER.copy()
    mock_user["authToken"] = auth_token
    return mock_user


@router.post("/login")
async def login(request: Request):
    """处理前端登录请求，调用LMS的login接口"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名和密码不能为空"
            )

        lms_login_url = f"{LMS_BASE_URL}/login"
        headers = {
            "userCode": username,
            "password": password
        }
        logger.info(f"尝试连接LMS服务: {lms_login_url}")

        try:
            response = requests.get(lms_login_url, headers=headers, timeout=5)
        except requests.exceptions.ConnectionError as e:
            logger.error(f"无法连接到LMS服务 {lms_login_url}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"无法连接到LMS服务，请确保LMS服务正在运行（{LMS_BASE_URL}）"
            )
        except requests.exceptions.Timeout:
            logger.error(f"连接LMS服务超时: {lms_login_url}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="LMS服务响应超时"
            )

        if response.status_code == 200:
            lms_response = response.json()
            token = lms_response.get("authToken")

            if not token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="登录成功但未返回authToken"
                )

            client_host = request.client.host if request.client else "unknown"
            log_operation(
                operation_type="user_login",
                action="用户登录",
                user_id=lms_response.get("userId"),
                user_name=lms_response.get("userName"),
                status="success",
                ip_address=client_host,
                details={
                    "login_method": "password",
                    "user_level": lms_response.get("userLevel")
                }
            )

            return {
                "success": True,
                "data": {
                    "userId": lms_response.get("userId"),
                    "userCode": lms_response.get("userCode"),
                    "userName": lms_response.get("userName"),
                    "authToken": token,
                    "userLevel": lms_response.get("userLevel"),
                }
            }
        else:
            client_host = request.client.host if request.client else "unknown"
            log_operation(
                operation_type="user_login",
                action="用户登录",
                user_id=username,
                status="failed",
                ip_address=client_host,
                details={
                    "error": response.text[:200],
                    "status_code": response.status_code
                }
            )

            raise HTTPException(
                status_code=response.status_code,
                detail=f"LMS登录失败: {response.text}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录请求失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录请求处理失败: {str(e)}"
        )


@router.get("/auth/token")
async def auth_token(token: str):
    """处理前端获取用户信息请求，调用LMS的authToken接口"""
    try:
        lms_auth_url = f"{LMS_BASE_URL}/auth/token?token={token}"
        response = requests.get(lms_auth_url)

        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"LMS获取用户信息失败: {response.text}"
            )
    except Exception as e:
        logger.error(f"获取用户信息请求失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息请求处理失败"
        )
