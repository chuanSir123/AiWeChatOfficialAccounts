"""
AI-Bot新闻抓取器
"""
import re
import hashlib
from typing import List, Optional
from .base import BaseScraper
from ..models.news import NewsItem, NewsDetail


class AIBotScraper(BaseScraper):
    """AI-Bot (ai-bot.cn) 新闻抓取器"""
    
    BASE_URL = "https://ai-bot.cn/daily-ai-news/"
    
    @property
    def source_name(self) -> str:
        return "AI-Bot"
    
    def _do_scrape(self, max_count: int = 10) -> List[NewsItem]:
        """抓取AI-Bot新闻列表"""
        news_list = []
        
        page = self.new_page()
        try:
            # 禁用图片、字体、媒体等资源加载，避免页面崩溃
            page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font", "stylesheet"]
                else route.continue_())
            
            # 该网站有403保护，需要模拟真实浏览器
            page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            })
            
            # 使用 commit 等待策略，最轻量级
            page.goto(self.BASE_URL, wait_until='commit', timeout=60000)
            page.wait_for_timeout(5000)
            
            # 等待新闻列表加载
            try:
                page.wait_for_selector('.news-item', timeout=10000)
            except:
                print("等待 .news-item 超时")
            
            # 根据实际HTML结构获取新闻项
            news_items = page.query_selector_all('.news-item')
            print(f"找到 {len(news_items)} 个新闻项")
            
            for item in news_items[:max_count]:
                try:
                    # 获取标题和链接 - 在 .news-content h2 a 中
                    title_el = item.query_selector('.news-content h2 a')
                    if not title_el:
                        continue
                    
                    title = title_el.inner_text().strip()
                    href = title_el.get_attribute('href')
                    
                    if not title or not href:
                        continue
                    
                    # 获取摘要 - 在 p.text-muted 中
                    summary_el = item.query_selector('.news-content p.text-muted')
                    summary = ""
                    if summary_el:
                        summary = summary_el.inner_text().strip()
                        # 移除来源信息
                        if '来源：' in summary:
                            summary = summary.split('来源：')[0].strip()
                    
                    # 生成ID
                    news_id = hashlib.md5(href.encode()).hexdigest()[:12]
                    
                    news = NewsItem(
                        id=news_id,
                        title=title,
                        summary=summary,
                        url=href,
                        source=self.source_name
                    )
                    
                    # 去重
                    if not any(n.url == news.url for n in news_list):
                        news_list.append(news)
                        print(f"抓取到: {title[:30]}...")
                        
                except Exception as e:
                    print(f"Error parsing AI-Bot news item: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error scraping AI-Bot: {e}")
        finally:
            page.close()
        
        return news_list
    
    def _do_get_detail(self, url: str) -> Optional[NewsDetail]:
        """获取AI-Bot新闻详情"""
        page = self.new_page()
        try:
            page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            })
            
            # 禁用图片、字体、媒体等资源加载，加速页面加载
            page.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "media", "font", "stylesheet"]
                else route.continue_())
            
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(2000)
            
            # 获取标题
            title_el = page.query_selector('h1, .entry-title, .post-title')
            title = title_el.inner_text() if title_el else ""
            
            # 获取正文 - 尝试多种选择器
            content = ""
            # 优先尝试 .post-content
            content_el = page.query_selector('.post-content')
            if content_el:
                content = content_el.inner_text()
            else:
                # 回退到其他选择器
                content_el = page.query_selector('.entry-content, article, .content')
                if content_el:
                    content = content_el.inner_text()
            
            # 如果仍然没有内容，尝试获取带textstyle属性的span元素（微信公众号文章）
            if not content or len(content.strip()) < 50:
                span_elements = page.query_selector_all('span[textstyle]')
                if span_elements:
                    texts = []
                    for span in span_elements:
                        text = span.inner_text()
                        if text and text.strip():
                            texts.append(text.strip())
                    if texts:
                        content = '\n'.join(texts)
            
            # 获取图片
            images = []
            img_elements = page.query_selector_all('.entry-content img, .post-content img')
            for img in img_elements:
                src = img.get_attribute('src')
                if src and src.startswith('http'):
                    images.append(src)
            
            news_id = hashlib.md5(url.encode()).hexdigest()[:12]
            
            return NewsDetail(
                id=news_id,
                title=title.strip(),
                content=content,
                url=url,
                source=self.source_name,
                images=images
            )
            
        except Exception as e:
            print(f"Error getting AI-Bot detail: {e}")
            return None
        finally:
            page.close()
