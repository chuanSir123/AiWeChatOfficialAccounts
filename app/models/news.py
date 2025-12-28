"""
新闻数据模型
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    """新闻条目"""
    id: str = Field(description="新闻ID")
    title: str = Field(description="新闻标题")
    summary: str = Field(default="", description="新闻摘要")
    content: str = Field(default="", description="新闻正文内容（预抓取）")
    url: str = Field(description="新闻链接")
    source: str = Field(description="来源网站")
    published_at: Optional[str] = Field(default=None, description="发布时间")
    scraped_at: datetime = Field(default_factory=datetime.now, description="抓取时间")
    views: Optional[int] = Field(default=None, description="阅读量")


class NewsDetail(BaseModel):
    """新闻详情"""
    id: str
    title: str
    content: str = Field(description="新闻正文内容")
    summary: str = ""
    url: str
    source: str
    author: Optional[str] = None
    published_at: Optional[str] = None
    images: List[str] = Field(default_factory=list, description="文章中的图片URL")


class NewsList(BaseModel):
    """新闻列表"""
    items: List[NewsItem] = Field(default_factory=list)
    total: int = 0
    source: str = ""
    scraped_at: datetime = Field(default_factory=datetime.now)
