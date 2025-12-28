"""
认证模块 - 使用环境变量进行身份验证
"""
import os
from typing import Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import RedirectResponse


# 从环境变量获取认证信息
AUTH_USERNAME = os.environ.get("AUTH_USERNAME", "")
AUTH_PASSWORD = os.environ.get("AUTH_PASSWORD", "")

# Cookie 名称
AUTH_COOKIE_NAME = "auth_token"
# 简单的认证 token (实际生产环境应使用更安全的方式)
AUTH_TOKEN = "authenticated_user_token_12345"


def is_auth_enabled() -> bool:
    """检查是否启用了认证"""
    return bool(AUTH_USERNAME and AUTH_PASSWORD)


def verify_credentials(username: str, password: str) -> bool:
    """验证用户名和密码"""
    if not is_auth_enabled():
        return True
    return username == AUTH_USERNAME and password == AUTH_PASSWORD


def is_authenticated(request: Request) -> bool:
    """检查请求是否已认证"""
    if not is_auth_enabled():
        return True
    token = request.cookies.get(AUTH_COOKIE_NAME)
    return token == AUTH_TOKEN


def set_auth_cookie(response: Response) -> None:
    """设置认证 Cookie"""
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=AUTH_TOKEN,
        httponly=True,
        max_age=86400 * 7,  # 7 天
        samesite="lax"
    )


def clear_auth_cookie(response: Response) -> None:
    """清除认证 Cookie"""
    response.delete_cookie(key=AUTH_COOKIE_NAME)


def require_auth(request: Request) -> Optional[RedirectResponse]:
    """
    检查认证状态，未认证则返回重定向响应
    返回 None 表示已认证，返回 RedirectResponse 表示需要重定向到登录页
    """
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return None
