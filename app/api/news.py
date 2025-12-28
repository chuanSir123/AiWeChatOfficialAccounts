"""
新闻相关API
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..scrapers import AIBaseScraper, AIBotScraper
from ..models.news import NewsItem, NewsList
from ..config import NEWS_DIR, get_config


router = APIRouter(prefix="/api/news", tags=["news"])


class ScrapeRequest(BaseModel):
    """抓取请求"""
    source: str  # "aibase" | "aibot" | "all"
    max_count: int = 10


class ScrapeResponse(BaseModel):
    """抓取响应"""
    success: bool
    message: str
    news_count: int
    news: List[NewsItem]


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_news(request: ScrapeRequest):
    """抓取热点新闻（包含正文内容并发预抓取）"""
    import asyncio
    import re
    
    all_news: List[NewsItem] = []
    config = get_config()
    
    async def fetch_detail_aibase(item):
        """获取AIBase新闻详情 - 使用独立的scraper实例"""
        try:
            scraper = AIBaseScraper()  # 每个任务使用独立实例
            detail = await scraper.get_detail(item.url)
            if detail and detail.content:
                clean_content = re.sub(r'<[^>]+>', '', detail.content)
                item.content = clean_content[:3000]
        except Exception as e:
            print(f"获取新闻详情失败: {item.url}, 错误: {e}")
    
    async def fetch_detail_aibot(item):
        """获取AIBot新闻详情 - 使用独立的scraper实例"""
        try:
            scraper = AIBotScraper()  # 每个任务使用独立实例
            detail = await scraper.get_detail(item.url)
            if detail and detail.content:
                clean_content = re.sub(r'<[^>]+>', '', detail.content)
                item.content = clean_content[:3000]
        except Exception as e:
            print(f"获取新闻详情失败: {item.url}, 错误: {e}")
    
    try:
        if request.source in ["aibase", "all"]:
            scraper = AIBaseScraper()
            news = await scraper.scrape(request.max_count)
            # 并发获取所有新闻详情（每个详情请求使用独立的scraper实例）
            if news:
                await asyncio.gather(*[fetch_detail_aibase(item) for item in news])
                all_news.extend(news)
        
        if request.source in ["aibot", "all"]:
            scraper = AIBotScraper()
            news = await scraper.scrape(request.max_count)
            # 并发获取所有新闻详情（每个详情请求使用独立的scraper实例）
            if news:
                await asyncio.gather(*[fetch_detail_aibot(item) for item in news])
                all_news.extend(news)
        
        # 保存到本地
        if all_news:
            save_news(all_news)
        
        return ScrapeResponse(
            success=True,
            message=f"成功抓取 {len(all_news)} 条新闻",
            news_count=len(all_news),
            news=all_news
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=NewsList)
async def get_news_list():
    """获取已抓取的新闻列表"""
    news_list = load_news()
    return NewsList(
        items=news_list,
        total=len(news_list),
        source="local"
    )


@router.get("/{news_id}")
async def get_news_detail(news_id: str):
    """获取新闻详情"""
    news_list = load_news()
    for news in news_list:
        if news.id == news_id:
            return news
    raise HTTPException(status_code=404, detail="新闻不存在")


@router.delete("/{news_id}")
async def delete_news(news_id: str):
    """删除新闻"""
    news_list = load_news()
    new_list = [n for n in news_list if n.id != news_id]
    if len(new_list) == len(news_list):
        raise HTTPException(status_code=404, detail="新闻不存在")
    save_news(new_list)
    return {"success": True, "message": "删除成功"}


def save_news(news_list: List[NewsItem]):
    """保存新闻到本地"""
    filepath = NEWS_DIR / "news.json"
    data = [n.model_dump() for n in news_list]
    for item in data:
        if 'scraped_at' in item and hasattr(item['scraped_at'], 'isoformat'):
            item['scraped_at'] = item['scraped_at'].isoformat()
    filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def load_news() -> List[NewsItem]:
    """从本地加载新闻"""
    filepath = NEWS_DIR / "news.json"
    if not filepath.exists():
        return []
    try:
        data = json.loads(filepath.read_text(encoding='utf-8'))
        return [NewsItem(**item) for item in data]
    except Exception:
        return []
