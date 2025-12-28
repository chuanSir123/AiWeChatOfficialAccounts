"""
文章相关API
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from ..models.article import Article, ArticleStatus, ArticleCreateRequest, ArticleList
from ..models.news import NewsItem
from ..ai import LLMClient, ImageGenerator
from ..config import ARTICLES_DIR, NEWS_DIR


router = APIRouter(prefix="/api/articles", tags=["articles"])


class GenerateArticleRequest(BaseModel):
    """生成文章请求"""
    news_ids: List[str]
    custom_prompt: Optional[str] = None


class GenerateCoverRequest(BaseModel):
    """生成封面请求"""
    article_id: str
    custom_prompt: Optional[str] = None


@router.post("/generate")
async def generate_article(request: GenerateArticleRequest):
    """根据新闻生成文章"""
    # 加载选中的新闻
    news_list = load_news()
    selected_news = [n for n in news_list if n.id in request.news_ids]
    
    if not selected_news:
        raise HTTPException(status_code=400, detail="未找到选中的新闻")
    
    try:
        # 使用预抓取的正文内容（存储在NewsItem.content中）
        from ..models.news import NewsDetail
        
        # 创建新闻详情列表，使用预抓取的内容
        news_details = []
        for news in selected_news:
            news_details.append(NewsDetail(
                id=news.id,
                title=news.title,
                content=news.content,  # 使用预抓取的内容
                url=news.url,
                source=news.source
            ))
        
        llm = LLMClient()
        article = await llm.generate_article(
            selected_news, 
            request.custom_prompt,
            news_details=news_details
        )
        
        # 保存文章
        save_article(article)
        
        return {
            "success": True,
            "message": "文章生成成功",
            "article": article
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-images")
async def generate_images(request: GenerateCoverRequest):
    """生成文章封面图和插图"""
    articles = load_articles()
    article = next((a for a in articles if a.id == request.article_id), None)
    
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    try:
        generator = ImageGenerator()
        figure_urls = []
        
        # 1. 生成封面图
        if request.custom_prompt:
            image_bytes, filepath = await generator.generate_with_custom_prompt(request.custom_prompt)
        elif article.cover_prompt:
            image_bytes, filepath = await generator.generate_with_custom_prompt(article.cover_prompt)
        else:
            image_bytes, filepath = await generator.generate_cover(article.title, article.digest)
        
        article.cover_url = filepath
        
        # 2. 生成插图并替换占位符
        content = article.content
        for i, prompt in enumerate(article.figure_prompt_list, 1):
            try:
                _, figure_path = await generator.generate_with_custom_prompt(prompt)
                figure_urls.append(figure_path)
                
                # 替换占位符为实际图片HTML
                placeholder = f"<figure{i}>"
                img_html = f'<p style="text-align:center;margin:20px 0;"><img src="/api/articles/figure/{article.id}/{i}" style="max-width:100%;border-radius:8px;" alt="插图{i}"></p>'
                content = content.replace(placeholder, img_html)
            except Exception as e:
                print(f"生成插图{i}失败: {e}")
                # 移除未生成的占位符
                content = content.replace(f"<figure{i}>", "")
        
        article.content = content
        article.figure_urls = figure_urls
        save_article(article)
        
        return {
            "success": True,
            "message": f"成功生成封面图和{len(figure_urls)}张插图",
            "cover_path": filepath,
            "figure_count": len(figure_urls)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RegenerateSingleImageRequest(BaseModel):
    article_id: str
    image_type: str  # "cover" or "figure"
    figure_index: Optional[int] = None  # 1-based index for figures
    prompt: str


@router.post("/regenerate-image")
async def regenerate_single_image(request: RegenerateSingleImageRequest):
    """重新生成单张图片（封面或插图）"""
    articles = load_articles()
    article = next((a for a in articles if a.id == request.article_id), None)
    
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    try:
        generator = ImageGenerator()
        _, filepath = await generator.generate_with_custom_prompt(request.prompt)
        
        if request.image_type == "cover":
            # 更新封面
            article.cover_url = filepath
            article.cover_prompt = request.prompt
            save_article(article)
            return {
                "success": True,
                "message": "封面图重新生成成功",
                "image_url": f"/api/articles/cover/{article.id}"
            }
        elif request.image_type == "figure" and request.figure_index:
            # 更新插图
            idx = request.figure_index - 1
            if idx < 0:
                raise HTTPException(status_code=400, detail="插图索引无效")
            
            # 确保figure_urls列表足够长
            while len(article.figure_urls) <= idx:
                article.figure_urls.append("")
            article.figure_urls[idx] = filepath
            
            # 更新提示词列表
            while len(article.figure_prompt_list) <= idx:
                article.figure_prompt_list.append("")
            article.figure_prompt_list[idx] = request.prompt
            
            save_article(article)
            return {
                "success": True,
                "message": f"插图{request.figure_index}重新生成成功",
                "image_url": f"/api/articles/figure/{article.id}/{request.figure_index}"
            }
        else:
            raise HTTPException(status_code=400, detail="无效的图片类型")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/figure/{article_id}/{figure_index}")
async def get_figure_image(article_id: str, figure_index: int):
    """获取插图图片"""
    articles = load_articles()
    article = next((a for a in articles if a.id == article_id), None)
    
    if not article or not article.figure_urls:
        raise HTTPException(status_code=404, detail="插图不存在")
    
    if figure_index < 1 or figure_index > len(article.figure_urls):
        raise HTTPException(status_code=404, detail="插图索引无效")
    
    try:
        image_bytes = Path(article.figure_urls[figure_index - 1]).read_bytes()
        return Response(content=image_bytes, media_type="image/png")
    except Exception:
        raise HTTPException(status_code=404, detail="插图文件不存在")


@router.get("/cover/{article_id}")
async def get_cover_image(article_id: str):
    """获取封面图片"""
    articles = load_articles()
    article = next((a for a in articles if a.id == article_id), None)
    
    if not article or not article.cover_url:
        raise HTTPException(status_code=404, detail="封面图不存在")
    
    try:
        image_bytes = Path(article.cover_url).read_bytes()
        return Response(content=image_bytes, media_type="image/png")
    except Exception:
        raise HTTPException(status_code=404, detail="封面图文件不存在")


@router.get("/list", response_model=ArticleList)
async def get_article_list():
    """获取文章列表"""
    articles = load_articles()
    return ArticleList(items=articles, total=len(articles))


@router.get("/{article_id}")
async def get_article(article_id: str):
    """获取文章详情"""
    articles = load_articles()
    article = next((a for a in articles if a.id == article_id), None)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return article


@router.put("/{article_id}")
async def update_article(article_id: str, data: dict):
    """更新文章"""
    articles = load_articles()
    article = next((a for a in articles if a.id == article_id), None)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    # 更新字段
    for key, value in data.items():
        if hasattr(article, key) and key not in ['id', 'created_at']:
            setattr(article, key, value)
    
    article.updated_at = datetime.now()
    save_article(article)
    
    return {"success": True, "message": "更新成功", "article": article}


@router.post("/{article_id}/regenerate")
async def regenerate_article(article_id: str, custom_prompt: Optional[str] = None):
    """重新生成文章内容"""
    articles = load_articles()
    article = next((a for a in articles if a.id == article_id), None)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    if not article.source_news:
        raise HTTPException(status_code=400, detail="文章没有关联的新闻源")
    
    try:
        # 加载原始新闻
        news_list = load_news()
        selected_news = [n for n in news_list if n.id in article.source_news]
        
        if not selected_news:
            raise HTTPException(status_code=400, detail="关联的新闻已不存在")
        
        # 获取新闻详情
        from ..scrapers import AIBaseScraper, AIBotScraper
        from ..models.news import NewsDetail
        
        news_details = []
        for news in selected_news:
            try:
                if news.source == "AIBase":
                    scraper = AIBaseScraper()
                else:
                    scraper = AIBotScraper()
                detail = await scraper.get_detail(news.url)
                if detail:
                    news_details.append(detail)
                else:
                    news_details.append(NewsDetail(
                        id=news.id, title=news.title, content="",
                        url=news.url, source=news.source
                    ))
            except Exception:
                news_details.append(NewsDetail(
                    id=news.id, title=news.title, content="",
                    url=news.url, source=news.source
                ))
        
        # 重新生成
        llm = LLMClient()
        new_article = await llm.generate_article(
            selected_news, custom_prompt, news_details=news_details
        )
        
        # 保留原有信息
        article.title = new_article.title
        article.digest = new_article.digest
        article.content = new_article.content
        article.updated_at = datetime.now()
        save_article(article)
        
        return {"success": True, "message": "文章重新生成成功", "article": article}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{article_id}")
async def delete_article(article_id: str):
    """删除文章"""
    articles = load_articles()
    new_list = [a for a in articles if a.id != article_id]
    if len(new_list) == len(articles):
        raise HTTPException(status_code=404, detail="文章不存在")
    
    # 重新保存
    filepath = ARTICLES_DIR / "articles.json"
    data = [a.model_dump() for a in new_list]
    for item in data:
        for key in ['created_at', 'updated_at']:
            if key in item and hasattr(item[key], 'isoformat'):
                item[key] = item[key].isoformat()
    filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    
    return {"success": True, "message": "删除成功"}


def load_news() -> List[NewsItem]:
    """加载新闻"""
    filepath = NEWS_DIR / "news.json"
    if not filepath.exists():
        return []
    try:
        data = json.loads(filepath.read_text(encoding='utf-8'))
        return [NewsItem(**item) for item in data]
    except Exception:
        return []


def save_article(article: Article):
    """保存文章"""
    articles = load_articles()
    
    # 更新或添加
    found = False
    for i, a in enumerate(articles):
        if a.id == article.id:
            articles[i] = article
            found = True
            break
    
    if not found:
        articles.append(article)
    
    # 保存
    filepath = ARTICLES_DIR / "articles.json"
    data = [a.model_dump() for a in articles]
    for item in data:
        for key in ['created_at', 'updated_at']:
            if key in item and hasattr(item[key], 'isoformat'):
                item[key] = item[key].isoformat()
    filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def load_articles() -> List[Article]:
    """加载文章"""
    filepath = ARTICLES_DIR / "articles.json"
    if not filepath.exists():
        return []
    try:
        data = json.loads(filepath.read_text(encoding='utf-8'))
        return [Article(**item) for item in data]
    except Exception:
        return []
