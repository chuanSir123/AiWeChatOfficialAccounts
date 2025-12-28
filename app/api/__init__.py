"""
API路由模块
"""
from .news import router as news_router
from .articles import router as articles_router
from .wechat import router as wechat_router
from .config import router as config_router

__all__ = ['news_router', 'articles_router', 'wechat_router', 'config_router']
