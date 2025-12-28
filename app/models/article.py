"""
文章数据模型
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ArticleStatus(str, Enum):
    """文章状态"""
    DRAFT = "draft"           # 本地草稿
    GENERATED = "generated"   # AI已生成
    UPLOADED = "uploaded"     # 已上传到微信
    PUBLISHED = "published"   # 已发布


class Article(BaseModel):
    """公众号文章"""
    id: str = Field(description="文章ID")
    title: str = Field(description="文章标题")
    author: str = Field(default="AI助手", description="作者")
    digest: str = Field(default="", description="文章摘要")
    content: str = Field(description="文章HTML内容")
    cover_url: Optional[str] = Field(default=None, description="封面图URL")
    cover_media_id: Optional[str] = Field(default=None, description="封面图media_id")
    cover_prompt: Optional[str] = Field(default=None, description="封面图生成提示词")
    figure_prompt_list: List[str] = Field(default_factory=list, description="插图生成提示词列表（0-5张）")
    figure_urls: List[str] = Field(default_factory=list, description="已生成的插图URL列表")
    source_news: List[str] = Field(default_factory=list, description="来源新闻ID列表")
    status: ArticleStatus = Field(default=ArticleStatus.DRAFT)
    wechat_media_id: Optional[str] = Field(default=None, description="微信草稿media_id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ArticleCreateRequest(BaseModel):
    """创建文章请求"""
    news_ids: List[str] = Field(description="选择的新闻ID列表")
    custom_prompt: Optional[str] = Field(default=None, description="自定义提示词")


class ArticleList(BaseModel):
    """文章列表"""
    items: List[Article] = Field(default_factory=list)
    total: int = 0
