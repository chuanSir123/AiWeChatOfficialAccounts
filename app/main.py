"""
AI公众号自动托管系统 - FastAPI入口
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .config import ensure_dirs, get_config
from .api import news_router, articles_router, wechat_router, config_router
from .scheduler import get_scheduler
from .scrapers import AIBaseScraper
from .ai import LLMClient, ImageGenerator
from .wechat import DraftManager
from .models.article import ArticleStatus


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    ensure_dirs()
    
    # 启动调度器
    config = get_config()
    scheduler = get_scheduler()
    
    if config.scheduler.enabled:
        scheduler.start()
        # 添加自动化任务 (抓取+全选生成文章+生成图片+上传草稿)
        scheduler.add_cron_job(
            "auto_publish",
            auto_publish_task,
            config.scheduler.auto_cron
        )
    
    yield
    
    # 关闭时
    scheduler.shutdown()


app = FastAPI(
    title="AI公众号自动托管系统",
    description="基于AI的微信公众号自动化管理系统",
    version="1.0.0",
    lifespan=lifespan
)

# 注册API路由
app.include_router(news_router)
app.include_router(articles_router)
app.include_router(wechat_router)
app.include_router(config_router)

# 静态文件
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    """首页"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "AI公众号自动托管系统", "docs": "/docs"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# 定时任务函数
async def auto_publish_task():
    """自动化发布任务: 抓取新闻 -> 全选生成文章 -> 生成图片 -> 上传草稿"""
    from .api.news import save_news, load_news
    from .api.articles import save_article
    from .models.news import NewsDetail
    
    print("[自动化任务] 开始执行...")
    
    # 1. 抓取新闻 (AIBase + AIBot 各最多10条)
    print("[自动化任务] 步骤1: 抓取新闻...")
    all_news = []
    try:
        # 抓取 AIBase
        print("[自动化任务] 抓取 AIBase 新闻...")
        scraper_aibase = AIBaseScraper()
        news_aibase = await scraper_aibase.scrape(10)
        all_news.extend(news_aibase)
        print(f"[自动化任务] AIBase 抓取到 {len(news_aibase)} 条新闻")
        
        # 抓取 AIBot
        print("[自动化任务] 抓取 AIBot 新闻...")
        from .scrapers import AIBotScraper
        scraper_aibot = AIBotScraper()
        news_aibot = await scraper_aibot.scrape(10)
        all_news.extend(news_aibot)
        print(f"[自动化任务] AIBot 抓取到 {len(news_aibot)} 条新闻")
        
        if all_news:
            save_news(all_news)
            print(f"[自动化任务] 共抓取到 {len(all_news)} 条新闻")
        else:
            print("[自动化任务] 未抓取到新闻，任务结束")
            return None
    except Exception as e:
        print(f"[自动化任务] 抓取新闻失败: {e}")
        return None
    
    # 2. 加载所有新闻并生成文章
    print("[自动化任务] 步骤2: 生成文章...")
    news_list = load_news()
    if not news_list:
        print("[自动化任务] 无新闻可生成文章，任务结束")
        return None
    
    try:
        # 创建新闻详情列表
        news_details = []
        for news in news_list:
            news_details.append(NewsDetail(
                id=news.id,
                title=news.title,
                content=news.content,
                url=news.url,
                source=news.source
            ))
        
        llm = LLMClient()
        article = await llm.generate_article(
            news_list, 
            custom_prompt=None,
            news_details=news_details
        )
        save_article(article)
        print(f"[自动化任务] 文章生成成功: {article.title}")
    except Exception as e:
        print(f"[自动化任务] 生成文章失败: {e}")
        return None
    
    # 3. 生成封面图和插图
    print("[自动化任务] 步骤3: 生成图片...")
    try:
        generator = ImageGenerator()
        figure_urls = []
        
        # 生成封面图
        if article.cover_prompt:
            _, filepath = await generator.generate_with_custom_prompt(article.cover_prompt)
        else:
            _, filepath = await generator.generate_cover(article.title, article.digest)
        article.cover_url = filepath
        print(f"[自动化任务] 封面图生成成功")
        
        # 生成插图并替换占位符
        content = article.content
        for i, prompt in enumerate(article.figure_prompt_list, 1):
            try:
                _, figure_path = await generator.generate_with_custom_prompt(prompt)
                figure_urls.append(figure_path)
                placeholder = f"<figure{i}>"
                img_html = f'<p style="text-align:center;margin:20px 0;"><img src="/api/articles/figure/{article.id}/{i}" style="max-width:100%;border-radius:8px;" alt="插图{i}"></p>'
                content = content.replace(placeholder, img_html)
                print(f"[自动化任务] 插图{i}生成成功")
            except Exception as e:
                print(f"[自动化任务] 生成插图{i}失败: {e}")
                content = content.replace(f"<figure{i}>", "")
        
        article.content = content
        article.figure_urls = figure_urls
        save_article(article)
        print(f"[自动化任务] 共生成 {len(figure_urls)} 张插图")
    except Exception as e:
        print(f"[自动化任务] 生成图片失败: {e}")
        # 继续执行，即使图片生成失败也尝试上传
    
    # 4. 上传到微信草稿箱
    print("[自动化任务] 步骤4: 上传草稿...")
    if not article.cover_url:
        print("[自动化任务] 无封面图，无法上传草稿")
        return article.id
    
    try:
        draft_manager = DraftManager()
        cover_bytes = Path(article.cover_url).read_bytes()
        media_id = await draft_manager.add_draft(article, cover_bytes)
        
        article.wechat_media_id = media_id
        article.status = ArticleStatus.UPLOADED
        save_article(article)
        print(f"[自动化任务] 草稿上传成功, media_id: {media_id}")
    except Exception as e:
        print(f"[自动化任务] 上传草稿失败: {e}")
    
    print("[自动化任务] 任务完成!")
    return article.id


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
