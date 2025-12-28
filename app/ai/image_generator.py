"""
图片生成器
"""
import uuid
from pathlib import Path
from typing import Optional
import httpx
from ..config import get_config, ImageConfig, IMAGES_DIR


class ImageGenerator:
    """图片生成器"""
    
    def __init__(self, config: Optional[ImageConfig] = None):
        self.config = config or get_config().image
    
    async def generate(self, prompt: str) -> bytes:
        """生成图片，返回图片字节"""
        payload = {"prompt": prompt,"width":"1080","height":"686"}
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                self.config.api_url,
                json=payload
            )
            response.raise_for_status()
            return response.content
    
    async def generate_cover(self, title: str, summary: str = "") -> tuple[bytes, str]:
        """生成封面图
        
        Args:
            title: 文章标题
            summary: 文章摘要
            
        Returns:
            tuple: (图片字节, 保存的文件路径)
        """
        # 构建提示词
        prompt = f"{self.config.default_prompt_prefix}{title}"
        if summary:
            prompt += f"，{summary[:50]}"
        # 生成图片
        image_bytes = await self.generate(prompt)
        
        # 保存到本地
        filename = f"cover_{uuid.uuid4().hex[:8]}.png"
        filepath = IMAGES_DIR / filename
        filepath.write_bytes(image_bytes)
        
        return image_bytes, str(filepath)
    
    async def generate_with_custom_prompt(self, prompt: str) -> tuple[bytes, str]:
        """使用自定义提示词生成图片
        
        Args:
            prompt: 完整的提示词
            
        Returns:
            tuple: (图片字节, 保存的文件路径)
        """
        image_bytes = await self.generate(prompt)
        
        filename = f"image_{uuid.uuid4().hex[:8]}.png"
        filepath = IMAGES_DIR / filename
        filepath.write_bytes(image_bytes)
        
        return image_bytes, str(filepath)
