"""
AIBase新闻抓取器
"""
import re
import hashlib
from typing import List, Optional
from .base import BaseScraper
from ..models.news import NewsItem, NewsDetail


class AIBaseScraper(BaseScraper):
    """AIBase (news.aibase.com) 新闻抓取器"""
    
    BASE_URL = "https://news.aibase.com/zh/news"
    
    @property
    def source_name(self) -> str:
        return "AIBase"
    
    def _do_scrape(self, max_count: int = 10) -> List[NewsItem]:
        """抓取AIBase新闻列表"""
        news_list = []
        
        page = self.new_page()
        try:
            # 禁用图片、字体、媒体等资源加载，加速页面加载
            page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font", "stylesheet"]
                else route.continue_())
            
            page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(2000)
            
            # 获取新闻列表项
            news_items = page.query_selector_all('a[href^="/zh/news/"]')
            
            for item in news_items[:max_count * 2]:  # 获取更多以便过滤
                try:
                    href = item.get_attribute('href')
                    if not href or not re.match(r'/zh/news/\d+', href):
                        continue
                    
                    # 获取文本内容
                    text = item.inner_text()
                    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
                    
                    if not lines:
                        continue
                    
                    title = lines[0]
                    summary = lines[1] if len(lines) > 1 else ""
                    
                    # 提取其他信息
                    published_at = None
                    views = None
                    for line in lines:
                        if '天前' in line or '小时前' in line:
                            published_at = line.strip()
                        if 'K' in line and line.replace('.', '').replace('K', '').isdigit():
                            views_str = line.replace('K', '').strip()
                            try:
                                views = int(float(views_str) * 1000)
                            except:
                                pass
                    
                    # 生成ID
                    news_id = hashlib.md5(href.encode()).hexdigest()[:12]
                    url = f"https://news.aibase.com{href}"
                    
                    news = NewsItem(
                        id=news_id,
                        title=title,
                        summary=summary,
                        url=url,
                        source=self.source_name,
                        published_at=published_at,
                        views=views
                    )
                    
                    # 去重
                    if not any(n.url == news.url for n in news_list):
                        news_list.append(news)
                        
                    if len(news_list) >= max_count:
                        break
                        
                except Exception as e:
                    print(f"Error parsing news item: {e}")
                    continue
                    
        finally:
            page.close()
        
        return news_list
    
    def _do_get_detail(self, url: str) -> Optional[NewsDetail]:
        """获取AIBase新闻详情"""
        page = self.new_page()
        try:
            # 禁用图片、字体、媒体等资源加载，加速页面加载
            page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font", "stylesheet"]
                else route.continue_())
            
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(2000)
            
            # 获取标题
            title_el = page.query_selector('h1')
            title = title_el.inner_text() if title_el else ""
            
            # 获取正文内容
            content_el = page.query_selector('article, .article-content, .content')
            content = content_el.inner_html() if content_el else ""
            
            # 获取图片
            images = []
            img_elements = page.query_selector_all('article img, .article-content img')
            for img in img_elements:
                src = img.get_attribute('src')
                if src:
                    if not src.startswith('http'):
                        src = f"https://news.aibase.com{src}"
                    images.append(src)
            
            news_id = hashlib.md5(url.encode()).hexdigest()[:12]
            
            return NewsDetail(
                id=news_id,
                title=title,
                content=content,
                url=url,
                source=self.source_name,
                images=images
            )
            
        except Exception as e:
            print(f"Error getting detail: {e}")
            return None
        finally:
            page.close()
