"""
AI公众号自动托管系统 - 配置管理
"""
import os
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class WeChatConfig(BaseModel):
    """微信公众号配置"""
    app_id: str = ""
    app_secret: str = ""
    account_name: str = ""  # 公众号名称，用作文章作者名


class LLMConfig(BaseModel):
    """LLM配置 (OpenAI格式)"""
    api_base: str = "https://huang123chuan-antigravity-api.hf.space/v1"
    api_key: str = "sk-"
    model: str = "gemini-3-flash"
    temperature: float = 0.7
    max_tokens: int = 4096


class ImageConfig(BaseModel):
    """图片生成配置"""
    api_url: str = ""
    default_prompt_prefix: str = "公众号封面图，"


class ScraperConfig(BaseModel):
    """新闻抓取配置"""
    aibase_url: str = "https://news.aibase.com/zh/news"
    aibot_url: str = "https://ai-bot.cn/daily-ai-news/"
    max_news_count: int = 10


class SchedulerConfig(BaseModel):
    """定时任务配置"""
    # 自动化任务cron表达式 (抓取+生成文章+生成图片+上传草稿)
    auto_cron: str = "0 8 * * *"
    enabled: bool = False


class AppConfig(BaseModel):
    """应用配置"""
    wechat: WeChatConfig = WeChatConfig()
    llm: LLMConfig = LLMConfig()
    image: ImageConfig = ImageConfig()
    scraper: ScraperConfig = ScraperConfig()
    scheduler: SchedulerConfig = SchedulerConfig()


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.yaml"
DATA_DIR = PROJECT_ROOT / "data"
NEWS_DIR = DATA_DIR / "news"
ARTICLES_DIR = DATA_DIR / "articles"
IMAGES_DIR = DATA_DIR / "images"


def ensure_dirs():
    """确保必要的目录存在"""
    for d in [DATA_DIR, NEWS_DIR, ARTICLES_DIR, IMAGES_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    """加载配置文件"""
    ensure_dirs()
    
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        return AppConfig(**data)
    return AppConfig()


def save_config(config: AppConfig):
    """保存配置文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(config.model_dump(), f, allow_unicode=True, default_flow_style=False)


# 全局配置实例
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """获取配置实例"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def update_config(new_config: AppConfig):
    """更新配置"""
    global _config
    _config = new_config
    save_config(new_config)
