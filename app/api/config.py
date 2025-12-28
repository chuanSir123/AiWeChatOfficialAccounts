"""
配置相关API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..config import get_config, update_config, AppConfig
from ..models.config import ConfigUpdate
from ..scheduler import get_scheduler


router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
async def get_current_config():
    """获取当前配置"""
    config = get_config()
    
    # 隐藏敏感信息
    return {
        "wechat": {
            "app_id": mask_secret(config.wechat.app_id),
            "app_secret": mask_secret(config.wechat.app_secret),
            "configured": bool(config.wechat.app_id and config.wechat.app_secret)
        },
        "llm": {
            "api_base": config.llm.api_base,
            "api_key": mask_secret(config.llm.api_key),
            "model": config.llm.model,
            "temperature": config.llm.temperature,
            "max_tokens": config.llm.max_tokens
        },
        "image": {
            "api_url": config.image.api_url,
            "default_prompt_prefix": config.image.default_prompt_prefix
        },
        "scheduler": {
            "auto_cron": config.scheduler.auto_cron,
            "enabled": config.scheduler.enabled
        }
    }


@router.put("")
async def update_current_config(data: ConfigUpdate):
    """更新配置"""
    config = get_config()
    
    # 更新微信配置
    if data.wechat:
        if data.wechat.app_id is not None:
            config.wechat.app_id = data.wechat.app_id
        if data.wechat.app_secret is not None:
            config.wechat.app_secret = data.wechat.app_secret
    
    # 更新LLM配置
    if data.llm:
        if data.llm.api_base is not None:
            config.llm.api_base = data.llm.api_base
        if data.llm.api_key is not None:
            config.llm.api_key = data.llm.api_key
        if data.llm.model is not None:
            config.llm.model = data.llm.model
        if data.llm.temperature is not None:
            config.llm.temperature = data.llm.temperature
        if data.llm.max_tokens is not None:
            config.llm.max_tokens = data.llm.max_tokens
    
    # 更新图片配置
    if data.image:
        if data.image.api_url is not None:
            config.image.api_url = data.image.api_url
        if data.image.default_prompt_prefix is not None:
            config.image.default_prompt_prefix = data.image.default_prompt_prefix
    
    # 更新定时任务配置
    if data.scheduler:
        if data.scheduler.auto_cron is not None:
            config.scheduler.auto_cron = data.scheduler.auto_cron
        if data.scheduler.enabled is not None:
            config.scheduler.enabled = data.scheduler.enabled
        
        # 实时更新定时任务
        scheduler = get_scheduler()
        from ..main import auto_publish_task
        
        # 先移除旧任务
        try:
            scheduler.remove_job("auto_publish")
        except Exception:
            pass
        
        # 如果启用，添加新任务
        if config.scheduler.enabled:
            scheduler.add_cron_job(
                "auto_publish",
                auto_publish_task,
                config.scheduler.auto_cron
            )
            if not scheduler.scheduler.running:
                scheduler.start()
    
    update_config(config)
    
    return {"success": True, "message": "配置已更新，定时任务已实时更新"}


@router.get("/scheduler/jobs")
async def get_scheduler_jobs():
    """获取定时任务列表"""
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()
    return {"jobs": jobs}


@router.get("/scheduler/history")
async def get_scheduler_history(limit: int = 20):
    """获取任务执行历史"""
    scheduler = get_scheduler()
    history = scheduler.get_history(limit)
    return {"history": history}


def mask_secret(value: str, show_chars: int = 4) -> str:
    """隐藏敏感信息"""
    if not value:
        return ""
    if len(value) <= show_chars * 2:
        return "*" * len(value)
    return value[:show_chars] + "*" * (len(value) - show_chars * 2) + value[-show_chars:]
