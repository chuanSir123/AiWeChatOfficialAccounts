"""
配置更新模型
"""
from typing import Optional
from pydantic import BaseModel


class WeChatConfigUpdate(BaseModel):
    """微信配置更新"""
    app_id: Optional[str] = None
    app_secret: Optional[str] = None


class LLMConfigUpdate(BaseModel):
    """LLM配置更新"""
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ImageConfigUpdate(BaseModel):
    """图片配置更新"""
    api_url: Optional[str] = None
    default_prompt_prefix: Optional[str] = None


class SchedulerConfigUpdate(BaseModel):
    """定时任务配置更新"""
    auto_cron: Optional[str] = None
    enabled: Optional[bool] = None


class ConfigUpdate(BaseModel):
    """完整配置更新"""
    wechat: Optional[WeChatConfigUpdate] = None
    llm: Optional[LLMConfigUpdate] = None
    image: Optional[ImageConfigUpdate] = None
    scheduler: Optional[SchedulerConfigUpdate] = None
