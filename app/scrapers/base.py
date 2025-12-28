"""
抓取器基类
"""
import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright, Browser, Page
from ..models.news import NewsItem, NewsDetail


# Windows兼容性：使用线程池执行Playwright，增加worker数量支持并发
_executor = ThreadPoolExecutor(max_workers=10)


class BaseScraper(ABC):
    """新闻抓取器基类"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None
    
    def _start_browser(self):
        """启动浏览器（同步）"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            channel='chrome',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-setuid-sandbox',
                '--single-process',
            ]
        )
    
    def _stop_browser(self):
        """关闭浏览器（同步）"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def new_page(self) -> Page:
        """创建新页面"""
        if not self.browser:
            raise RuntimeError("Browser not initialized")
        context = self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        return context.new_page()
    
    async def scrape(self, max_count: int = 10) -> List[NewsItem]:
        """抓取新闻列表（异步包装）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._scrape_sync, max_count)
    
    def _scrape_sync(self, max_count: int = 10) -> List[NewsItem]:
        """同步抓取（在线程中执行）"""
        try:
            self._start_browser()
            return self._do_scrape(max_count)
        finally:
            self._stop_browser()
    
    @abstractmethod
    def _do_scrape(self, max_count: int = 10) -> List[NewsItem]:
        """实际抓取逻辑（子类实现）"""
        pass
    
    async def get_detail(self, url: str) -> Optional[NewsDetail]:
        """获取新闻详情（异步包装）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._get_detail_sync, url)
    
    def _get_detail_sync(self, url: str) -> Optional[NewsDetail]:
        """同步获取详情 - 每次调用都使用独立的浏览器实例"""
        try:
            self._start_browser()
            return self._do_get_detail(url)
        finally:
            self._stop_browser()
    
    @abstractmethod
    def _do_get_detail(self, url: str) -> Optional[NewsDetail]:
        """实际获取详情逻辑（子类实现）"""
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """来源名称"""
        pass
