"""
微信相关API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..wechat import TokenManager, DraftManager, MaterialManager
from ..wechat.token_manager import get_token_manager, reset_token_manager
from ..config import get_config, update_config
from .articles import load_articles, save_article
from ..models.article import ArticleStatus


router = APIRouter(prefix="/api/wechat", tags=["wechat"])


class BindAccountRequest(BaseModel):
    """绑定公众号请求"""
    app_id: str
    app_secret: str
    account_name: str = ""  # 公众号名称


class UploadDraftRequest(BaseModel):
    """上传草稿请求"""
    article_id: str


@router.post("/bind")
async def bind_account(request: BindAccountRequest):
    """绑定微信公众号"""
    try:
        # 更新配置
        config = get_config()
        config.wechat.app_id = request.app_id
        config.wechat.app_secret = request.app_secret
        config.wechat.account_name = request.account_name
        update_config(config)
        
        # 重置Token管理器
        reset_token_manager()
        
        # 验证配置
        token_manager = get_token_manager()
        result = await token_manager.verify_token()
        
        return {
            "success": True,
            "message": "公众号绑定成功",
            "account_name": request.account_name,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def get_wechat_status():
    """获取微信公众号绑定状态"""
    config = get_config()
    token_manager = get_token_manager()
    
    is_bound = token_manager.is_configured
    
    if is_bound:
        try:
            await token_manager.verify_token()
            return {
                "bound": True,
                "valid": True,
                "app_id": config.wechat.app_id[:8] + "***" if len(config.wechat.app_id) > 8 else "***",
                "account_name": config.wechat.account_name
            }
        except Exception as e:
            return {
                "bound": True,
                "valid": False,
                "account_name": config.wechat.account_name,
                "error": str(e)
            }
    
    return {"bound": False, "valid": False, "account_name": ""}


@router.post("/draft/upload")
async def upload_draft(request: UploadDraftRequest):
    """上传文章到微信草稿箱"""
    # 获取文章
    articles = load_articles()
    article = next((a for a in articles if a.id == request.article_id), None)
    
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    if not article.cover_url:
        raise HTTPException(status_code=400, detail="请先生成封面图")
    
    try:
        draft_manager = DraftManager()
        
        # 读取封面图
        from pathlib import Path
        cover_bytes = Path(article.cover_url).read_bytes()
        
        # 上传草稿
        media_id = await draft_manager.add_draft(article, cover_bytes)
        
        # 更新文章状态
        article.wechat_media_id = media_id
        article.status = ArticleStatus.UPLOADED
        save_article(article)
        
        return {
            "success": True,
            "message": "草稿上传成功",
            "media_id": media_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/draft/update")
async def update_draft(request: UploadDraftRequest):
    """更新微信草稿（删除旧草稿并上传新草稿）"""
    # 获取文章
    articles = load_articles()
    article = next((a for a in articles if a.id == request.article_id), None)
    
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    if not article.cover_url:
        raise HTTPException(status_code=400, detail="请先生成封面图")
    
    try:
        draft_manager = DraftManager()
        
        # 如果有旧的草稿，先删除
        if article.wechat_media_id:
            try:
                await draft_manager.delete_draft(article.wechat_media_id)
            except Exception as e:
                print(f"删除旧草稿失败: {e}")
        
        # 读取封面图
        from pathlib import Path
        cover_bytes = Path(article.cover_url).read_bytes()
        
        # 上传新草稿
        media_id = await draft_manager.add_draft(article, cover_bytes)
        
        # 更新文章状态
        article.wechat_media_id = media_id
        article.status = ArticleStatus.UPLOADED
        save_article(article)
        
        return {
            "success": True,
            "message": "草稿更新成功",
            "media_id": media_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/draft/list")
async def get_draft_list(offset: int = 0, count: int = 20):
    """获取微信草稿列表"""
    try:
        draft_manager = DraftManager()
        result = await draft_manager.get_draft_list(offset, count)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/draft/{media_id}")
async def get_draft_detail(media_id: str):
    """获取草稿详情"""
    try:
        draft_manager = DraftManager()
        result = await draft_manager.get_draft(media_id)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/draft/{media_id}")
async def delete_draft(media_id: str):
    """删除草稿"""
    try:
        draft_manager = DraftManager()
        await draft_manager.delete_draft(media_id)
        return {"success": True, "message": "草稿删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/draft/{media_id}/publish")
async def publish_draft(media_id: str):
    """发布草稿"""
    try:
        draft_manager = DraftManager()
        publish_id = await draft_manager.publish_draft(media_id)
        return {
            "success": True,
            "message": "发布任务已提交",
            "publish_id": publish_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
