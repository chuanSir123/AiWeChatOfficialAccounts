"""
微信公众号素材管理
"""
from pathlib import Path
from typing import Optional, Union
import httpx
from .token_manager import get_token_manager


class MaterialManager:
    """素材管理器"""
    
    UPLOAD_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"
    UPLOAD_IMG_URL = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
    
    def __init__(self):
        self.token_manager = get_token_manager()
    
    async def upload_image(self, image_data: Union[bytes, str, Path]) -> str:
        """上传图片素材（永久素材，用于封面图）
        
        Args:
            image_data: 图片数据（字节或文件路径）
            
        Returns:
            media_id
        """
        token = await self.token_manager.get_access_token()
        
        # 处理输入
        if isinstance(image_data, (str, Path)):
            image_bytes = Path(image_data).read_bytes()
            filename = Path(image_data).name
        else:
            image_bytes = image_data
            filename = "image.png"
        
        url = f"{self.UPLOAD_URL}?access_token={token}&type=image"
        
        async with httpx.AsyncClient() as client:
            files = {"media": (filename, image_bytes, "image/png")}
            response = await client.post(url, files=files)
            data = response.json()
        
        if "errcode" in data and data["errcode"] != 0:
            raise ValueError(f"上传图片失败: {data.get('errmsg', '未知错误')}")
        
        return data["media_id"]
    
    async def upload_article_image(self, image_data: Union[bytes, str, Path]) -> str:
        """上传图文消息内的图片（返回URL，用于正文中的图片）
        
        Args:
            image_data: 图片数据（字节或文件路径）
            
        Returns:
            图片URL（可在图文正文中使用）
        """
        token = await self.token_manager.get_access_token()
        
        if isinstance(image_data, (str, Path)):
            image_bytes = Path(image_data).read_bytes()
            filename = Path(image_data).name
        else:
            image_bytes = image_data
            filename = "image.png"
        
        url = f"{self.UPLOAD_IMG_URL}?access_token={token}"
        
        async with httpx.AsyncClient() as client:
            files = {"media": (filename, image_bytes, "image/png")}
            response = await client.post(url, files=files)
            data = response.json()
        
        if "errcode" in data and data["errcode"] != 0:
            raise ValueError(f"上传图片失败: {data.get('errmsg', '未知错误')}")
        
        return data["url"]
    
    async def get_material_list(self, type: str = "image", offset: int = 0, count: int = 20) -> dict:
        """获取素材列表
        
        Args:
            type: 素材类型 (image, video, voice, news)
            offset: 偏移量
            count: 返回数量
            
        Returns:
            素材列表
        """
        token = await self.token_manager.get_access_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={token}"
        
        payload = {
            "type": type,
            "offset": offset,
            "count": count
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            data = response.json()
        
        if "errcode" in data and data["errcode"] != 0:
            raise ValueError(f"获取素材列表失败: {data.get('errmsg', '未知错误')}")
        
        return data
