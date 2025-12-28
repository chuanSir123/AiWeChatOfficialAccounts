"""
新闻抓取模块
"""
from .base import BaseScraper
from .aibase_scraper import AIBaseScraper
from .aibot_scraper import AIBotScraper

__all__ = ['BaseScraper', 'AIBaseScraper', 'AIBotScraper']
