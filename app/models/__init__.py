"""
数据模型模块
"""
from .news import NewsItem, NewsDetail
from .article import Article, ArticleStatus
from .config import ConfigUpdate

__all__ = ['NewsItem', 'NewsDetail', 'Article', 'ArticleStatus', 'ConfigUpdate']
