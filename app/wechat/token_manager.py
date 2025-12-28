"""
微信公众号Access Token管理
"""
import time
from typing import Optional
import httpx
from ..config import get_config, WeChatConfig


class TokenManager:
    """Access Token管理器"""
    
    API_URL = "https://api.weixin.qq.com/cgi-bin/token"
    
    def __init__(self, config: Optional[WeChatConfig] = None):
        self.config = config or get_config().wechat
        self._access_token: Optional[str] = None
        self._expires_at: float = 0
    
    @property
    def is_configured(self) -> bool:
        """检查是否已配置AppID和AppSecret"""
        return bool(self.config.app_id and self.config.app_secret)
    
    async def get_access_token(self, force_refresh: bool = False) -> str:
        """获取Access Token
        
        Args:
            force_refresh: 是否强制刷新
            
        Returns:
            Access Token
            
        Raises:
            ValueError: 未配置AppID或AppSecret
            httpx.HTTPError: API调用失败
        """
        if not self.is_configured:
            raise ValueError("未配置微信公众号AppID或AppSecret")
        
        # 检查缓存
        if not force_refresh and self._access_token and time.time() < self._expires_at:
            return self._access_token
        
        # 请求新的Token
        params = {
            "grant_type": "client_credential",
            "appid": self.config.app_id,
            "secret": self.config.app_secret
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.API_URL, params=params)
            response.raise_for_status()
            data = response.json()
        
        if "errcode" in data and data["errcode"] != 0:
            raise ValueError(f"获取Access Token失败: {data.get('errmsg', '未知错误')}")
        
        self._access_token = data["access_token"]
        # 提前5分钟过期，避免边界问题
        self._expires_at = time.time() + data.get("expires_in", 7200) - 300
        
        return self._access_token
    
    def clear_cache(self):
        """清除Token缓存"""
        self._access_token = None
        self._expires_at = 0
    
    async def verify_token(self) -> dict:
        """验证Token并获取公众号基本信息
        
        Returns:
            公众号基本信息
        """
        token = await self.get_access_token()
        
        # 获取公众号基本信息
        url = "https://api.weixin.qq.com/cgi-bin/getcallbackip"
        params = {"access_token": token}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()
        
        if "errcode" in data and data["errcode"] != 0:
            raise ValueError(f"验证Token失败: {data.get('errmsg', '未知错误')}")
        
        return {
            "status": "success",
            "message": "Token验证成功",
            "ip_list": data.get("ip_list", [])
        }


# 全局Token管理器实例
_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """获取Token管理器实例"""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager


def reset_token_manager():
    """重置Token管理器（配置更新后调用）"""
    global _token_manager
    _token_manager = None
