"""
微信公众号草稿管理
"""
from typing import Optional, List
from pathlib import Path
import re
import httpx
from .token_manager import get_token_manager
from .material import MaterialManager
from ..models.article import Article


class DraftManager:
    """草稿管理器"""
    
    ADD_DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"
    GET_DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/get"
    DELETE_DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/delete"
    BATCHGET_DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/batchget"
    PUBLISH_URL = "https://api.weixin.qq.com/cgi-bin/freepublish/submit"
    
    def __init__(self):
        self.token_manager = get_token_manager()
        self.material_manager = MaterialManager()
    
    async def _process_content_images(self, content: str, figure_urls: List[str]) -> str:
        """处理文章内容中的图片，上传到微信并替换URL
        
        Args:
            content: 文章HTML内容
            figure_urls: 本地图片路径列表
            
        Returns:
            替换后的内容
        """
        processed_content = content
        
        # 处理所有插图（/api/articles/figure/xxx/n 格式的URL）
        # 匹配 src="/api/articles/figure/xxx/1" 这种格式
        pattern = r'src="(/api/articles/figure/[^"]+/(\d+))"'
        matches = re.findall(pattern, content)
        
        for local_url, index in matches:
            idx = int(index) - 1
            if idx < len(figure_urls) and figure_urls[idx]:
                try:
                    # 读取本地图片并上传到微信
                    image_path = Path(figure_urls[idx])
                    if image_path.exists():
                        wechat_url = await self.material_manager.upload_article_image(image_path)
                        processed_content = processed_content.replace(f'src="{local_url}"', f'src="{wechat_url}"')
                        print(f"成功上传插图{index}到微信: {wechat_url}")
                except Exception as e:
                    print(f"上传插图{index}失败: {e}")
        
        return processed_content
    
    async def add_draft(self, article: Article, cover_image: Optional[bytes] = None) -> str:
        """新增草稿
        
        Args:
            article: 文章对象
            cover_image: 封面图片字节（可选，如果文章已有cover_media_id则不需要）
            
        Returns:
            草稿media_id
        """
        token = await self.token_manager.get_access_token()
        
        # 如果有封面图片，先上传
        thumb_media_id = article.cover_media_id
        if cover_image and not thumb_media_id:
            thumb_media_id = await self.material_manager.upload_image(cover_image)
        
        if not thumb_media_id:
            raise ValueError("缺少封面图片，请先生成或上传封面图")
        
        # 处理文章内容中的图片，上传到微信
        processed_content = await self._process_content_images(
            article.content, 
            article.figure_urls or []
        )
        
        # 构建草稿数据
        draft_data = {
            "articles": [
                {
                    "title": article.title,
                    "author": article.author,
                    "digest": article.digest,
                    "content": processed_content,
                    "thumb_media_id": thumb_media_id,
                    "need_open_comment": 0,
                    "only_fans_can_comment": 0
                }
            ]
        }
        
        url = f"{self.ADD_DRAFT_URL}?access_token={token}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=draft_data)
            data = response.json()
        
        if "errcode" in data and data["errcode"] != 0:
            raise ValueError(f"新增草稿失败: {data.get('errmsg', '未知错误')}")
        
        return data["media_id"]
    
    async def get_draft(self, media_id: str) -> dict:
        """获取草稿详情
        
        Args:
            media_id: 草稿media_id
            
        Returns:
            草稿详情
        """
        token = await self.token_manager.get_access_token()
        url = f"{self.GET_DRAFT_URL}?access_token={token}"
        
        payload = {"media_id": media_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            data = response.json()
        
        if "errcode" in data and data["errcode"] != 0:
            raise ValueError(f"获取草稿失败: {data.get('errmsg', '未知错误')}")
        
        return data
    
    async def delete_draft(self, media_id: str) -> bool:
        """删除草稿
        
        Args:
            media_id: 草稿media_id
            
        Returns:
            是否成功
        """
        token = await self.token_manager.get_access_token()
        url = f"{self.DELETE_DRAFT_URL}?access_token={token}"
        
        payload = {"media_id": media_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            data = response.json()
        
        if "errcode" in data and data["errcode"] != 0:
            raise ValueError(f"删除草稿失败: {data.get('errmsg', '未知错误')}")
        
        return True
    
    async def get_draft_list(self, offset: int = 0, count: int = 20, no_content: bool = True) -> dict:
        """获取草稿列表
        
        Args:
            offset: 偏移量
            count: 返回数量（最大20）
            no_content: 是否返回content字段
            
        Returns:
            草稿列表
        """
        token = await self.token_manager.get_access_token()
        url = f"{self.BATCHGET_DRAFT_URL}?access_token={token}"
        
        payload = {
            "offset": offset,
            "count": min(count, 20),
            "no_content": 1 if no_content else 0
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            data = response.json()
        
        if "errcode" in data and data["errcode"] != 0:
            raise ValueError(f"获取草稿列表失败: {data.get('errmsg', '未知错误')}")
        
        return data
    
    async def publish_draft(self, media_id: str) -> str:
        """发布草稿
        
        Args:
            media_id: 草稿media_id
            
        Returns:
            发布任务ID (publish_id)
        """
        token = await self.token_manager.get_access_token()
        url = f"{self.PUBLISH_URL}?access_token={token}"
        
        payload = {"media_id": media_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            data = response.json()
        
        if "errcode" in data and data["errcode"] != 0:
            raise ValueError(f"发布草稿失败: {data.get('errmsg', '未知错误')}")
        
        return data.get("publish_id", "")
