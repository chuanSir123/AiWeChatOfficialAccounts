/**
 * AI公众号自动托管系统 - 前端脚本
 */

// ===== 全局状态 =====
let selectedNews = new Set();
let currentArticle = null;
let currentNewsList = [];  // 保存当前新闻列表用于全选
let currentImageRegenerate = null;  // {type: 'cover'|'figure', figureIndex: number}

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    loadNews();
    loadConfig();
    checkWeChatStatus();
});

// ===== 导航 =====
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            switchPage(page);
        });
    });
}

function switchPage(pageName) {
    // 更新导航高亮
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === pageName);
    });

    // 切换页面
    document.querySelectorAll('.page').forEach(page => {
        page.classList.toggle('active', page.id === `page-${pageName}`);
    });

    // 加载页面数据
    switch (pageName) {
        case 'news':
            loadNews();
            break;
        case 'articles':
            loadArticles();
            break;
        case 'drafts':
            loadDrafts();
            break;
        case 'config':
            loadConfig();
            break;
    }
}

// ===== 新闻相关 =====
async function loadNews() {
    try {
        const response = await fetch('/api/news/list');
        const data = await response.json();
        renderNewsList(data.items || []);
    } catch (error) {
        console.error('加载新闻失败:', error);
    }
}

async function scrapeNews(source) {
    showLoading('正在抓取新闻...');
    try {
        const response = await fetch('/api/news/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source, max_count: 10 })
        });
        const data = await response.json();

        if (data.success) {
            showToast(`成功抓取 ${data.news_count} 条新闻`, 'success');
            loadNews();
        } else {
            showToast('抓取失败: ' + (data.detail || '未知错误'), 'error');
        }
    } catch (error) {
        showToast('抓取失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function renderNewsList(news) {
    const container = document.getElementById('newsList');
    currentNewsList = news;  // 保存当前列表

    if (news.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📭</span>
                <p>暂无新闻，点击上方按钮抓取</p>
            </div>
        `;
        updateSelectAllButton();
        return;
    }

    container.innerHTML = news.map(item => `
        <div class="news-item ${selectedNews.has(item.id) ? 'selected' : ''}" 
             onclick="toggleNewsSelection('${item.id}')">
            <input type="checkbox" class="news-checkbox" 
                   ${selectedNews.has(item.id) ? 'checked' : ''}
                   onclick="event.stopPropagation()">
            <div class="news-content">
                <div class="news-title">${escapeHtml(item.title)}</div>
                <div class="news-summary">${escapeHtml(item.summary || '')}</div>
                <div class="news-meta">
                    <span class="news-source">${escapeHtml(item.source)}</span>
                    ${item.published_at ? `<span>📅 ${item.published_at}</span>` : ''}
                    ${item.views ? `<span>👁 ${formatNumber(item.views)}</span>` : ''}
                </div>
            </div>
        </div>
    `).join('');

    updateSelectedCount();
    updateSelectAllButton();
}

function toggleSelectAll() {
    if (currentNewsList.length === 0) return;

    if (selectedNews.size === currentNewsList.length) {
        // 取消全选
        selectedNews.clear();
    } else {
        // 全选
        currentNewsList.forEach(item => selectedNews.add(item.id));
    }

    renderNewsList(currentNewsList);
}

function updateSelectAllButton() {
    const btn = document.getElementById('selectAllBtn');
    if (!btn) return;

    if (currentNewsList.length > 0 && selectedNews.size === currentNewsList.length) {
        btn.innerHTML = '<span>☐</span> 取消全选';
    } else {
        btn.innerHTML = '<span>☑️</span> 全选';
    }
}

function toggleNewsSelection(newsId) {
    if (selectedNews.has(newsId)) {
        selectedNews.delete(newsId);
    } else {
        selectedNews.add(newsId);
    }

    // 更新UI
    const item = document.querySelector(`.news-item[onclick*="${newsId}"]`);
    if (item) {
        item.classList.toggle('selected', selectedNews.has(newsId));
        const checkbox = item.querySelector('.news-checkbox');
        if (checkbox) checkbox.checked = selectedNews.has(newsId);
    }

    updateSelectedCount();
}

function updateSelectedCount() {
    const count = selectedNews.size;
    document.getElementById('selectedCount').textContent = count;
    document.getElementById('generateArticleBtn').disabled = count === 0;
}

// ===== 文章相关 =====
async function generateArticle() {
    if (selectedNews.size === 0) {
        showToast('请先选择新闻', 'error');
        return;
    }

    showLoading('AI正在创作文章...');
    try {
        const response = await fetch('/api/articles/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                news_ids: Array.from(selectedNews)
            })
        });
        const data = await response.json();

        if (data.success) {
            showToast('文章生成成功！', 'success');
            selectedNews.clear();
            updateSelectedCount();
            loadNews();
            switchPage('articles');
        } else {
            showToast('生成失败: ' + (data.detail || '未知错误'), 'error');
        }
    } catch (error) {
        showToast('生成失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function loadArticles() {
    try {
        const response = await fetch('/api/articles/list');
        const data = await response.json();
        renderArticleList(data.items || []);
    } catch (error) {
        console.error('加载文章失败:', error);
    }
}

function renderArticleList(articles) {
    const container = document.getElementById('articleList');

    if (articles.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📄</span>
                <p>暂无文章，请先抓取新闻并生成</p>
            </div>
        `;
        return;
    }

    container.innerHTML = articles.map(article => `
        <div class="article-card">
            ${article.cover_url
            ? `<img class="article-cover-img" src="/api/articles/cover/${article.id}" alt="封面">`
            : `<div class="article-cover-placeholder">🖼️</div>`
        }
            <div class="article-card-body">
                <div class="article-card-title">${escapeHtml(article.title)}</div>
                <div class="article-card-digest">${escapeHtml(article.digest || '')}</div>
                <div class="article-card-meta">
                    <span>${formatDate(article.created_at)}</span>
                    <span class="article-status ${article.status}">${getStatusText(article.status)}</span>
                </div>
            </div>
            <div class="article-card-actions">
                <button class="btn btn-sm btn-secondary" onclick="previewArticle('${article.id}')">
                    预览
                </button>
                <button class="btn btn-sm btn-primary" onclick="generateImagesFor('${article.id}')">
                    生成图片
                </button>
                <button class="btn btn-sm btn-accent" onclick="handleDraftForArticle('${article.id}', ${!!article.wechat_media_id})" 
                        ${!article.cover_url ? 'disabled' : ''}>
                    ${article.wechat_media_id ? '修改草稿' : '上传草稿'}
                </button>
            </div>
        </div>
    `).join('');
}

async function previewArticle(articleId) {
    try {
        const response = await fetch(`/api/articles/${articleId}`);
        const article = await response.json();
        currentArticle = article;

        document.getElementById('modalArticleTitle').value = article.title;
        document.getElementById('modalArticleAuthor').textContent = article.author;
        document.getElementById('modalArticleStatus').textContent = getStatusText(article.status);
        document.getElementById('modalArticleDigest').value = article.digest || '';
        document.getElementById('modalArticleContent').innerHTML = article.content;

        if (article.cover_url) {
            document.getElementById('modalArticleCover').innerHTML =
                `<img src="/api/articles/cover/${article.id}" alt="封面" onclick="openImageRegenerateModal('cover', 0, '${escapeHtml(article.cover_prompt || '')}')" style="cursor:pointer;" title="点击重新生成">`;
        } else {
            document.getElementById('modalArticleCover').innerHTML =
                `<div onclick="openImageRegenerateModal('cover', 0, '')" style="cursor:pointer; padding: 40px; background: #f5f5f5; text-align: center; border-radius: 8px;">
                    <p style="color: #888;">📷 点击生成封面图</p>
                </div>`;
        }

        // 为文章内容中的图片添加点击事件
        setTimeout(() => {
            const contentDiv = document.getElementById('modalArticleContent');
            const images = contentDiv.querySelectorAll('img');
            images.forEach((img, index) => {
                const src = img.getAttribute('src');
                if (src && src.includes('/api/articles/figure/')) {
                    const match = src.match(/\/figure\/[^/]+\/(\d+)/);
                    if (match) {
                        const figureIndex = parseInt(match[1]);
                        const prompt = article.figure_prompt_list?.[figureIndex - 1] || '';
                        img.style.cursor = 'pointer';
                        img.title = '点击重新生成';
                        img.onclick = (e) => {
                            e.stopPropagation();
                            openImageRegenerateModal('figure', figureIndex, prompt);
                        };
                    }
                }
            });
        }, 100);

        // 更新草稿按钮文字
        const draftBtn = document.getElementById('draftActionBtn');
        if (article.wechat_media_id) {
            draftBtn.textContent = '修改草稿';
        } else {
            draftBtn.textContent = '上传草稿';
        }
        draftBtn.disabled = !article.cover_url;

        openModal('articleModal');
    } catch (error) {
        showToast('加载文章失败: ' + error.message, 'error');
    }
}

async function saveArticleEdit() {
    if (!currentArticle) return;

    showLoading('正在保存...');
    try {
        const data = {
            title: document.getElementById('modalArticleTitle').value,
            digest: document.getElementById('modalArticleDigest').value,
            content: document.getElementById('modalArticleContent').innerHTML
        };

        const response = await fetch(`/api/articles/${currentArticle.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();

        if (result.success) {
            showToast('保存成功！', 'success');
            currentArticle = result.article;
            loadArticles();
        } else {
            showToast('保存失败: ' + (result.detail || '未知错误'), 'error');
        }
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function regenerateArticle() {
    if (!currentArticle) return;
    if (!confirm('重新生成将覆盖当前内容，确定继续吗？')) return;

    showLoading('AI正在重新生成文章...');
    try {
        const response = await fetch(`/api/articles/${currentArticle.id}/regenerate`, {
            method: 'POST'
        });
        const result = await response.json();

        if (result.success) {
            showToast('重新生成成功！', 'success');
            await previewArticle(currentArticle.id);
            loadArticles();
        } else {
            showToast('重新生成失败: ' + (result.detail || '未知错误'), 'error');
        }
    } catch (error) {
        showToast('重新生成失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function handleDraftAction() {
    if (!currentArticle) return;

    if (currentArticle.wechat_media_id) {
        // 修改草稿
        await updateDraft();
    } else {
        // 上传草稿
        await uploadDraft();
    }
}

async function updateDraft() {
    if (!currentArticle) return;

    showLoading('正在更新草稿...');
    try {
        const response = await fetch('/api/wechat/draft/update', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ article_id: currentArticle.id })
        });
        const data = await response.json();

        if (data.success) {
            showToast('草稿更新成功！', 'success');
            await previewArticle(currentArticle.id);
            loadArticles();
        } else {
            showToast('更新失败: ' + (data.detail || '未知错误'), 'error');
        }
    } catch (error) {
        showToast('更新失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function generateImagesFor(articleId) {
    showLoading('正在生成封面图和插图...');
    try {
        const response = await fetch('/api/articles/generate-images', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ article_id: articleId })
        });
        const data = await response.json();

        if (data.success) {
            showToast(data.message || '图片生成成功！', 'success');
            loadArticles();
        } else {
            showToast('生成失败: ' + (data.detail || '未知错误'), 'error');
        }
    } catch (error) {
        showToast('生成失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function generateImages() {
    if (currentArticle) {
        await generateImagesFor(currentArticle.id);
        await previewArticle(currentArticle.id);
    }
}

// ===== 图片重新生成 =====
function openImageRegenerateModal(imageType, figureIndex, currentPrompt) {
    currentImageRegenerate = {
        type: imageType,
        figureIndex: figureIndex
    };
    document.getElementById('imagePromptInput').value = currentPrompt || '';
    openModal('imageRegenerateModal');
}

async function confirmRegenerateImage() {
    if (!currentArticle || !currentImageRegenerate) return;

    const prompt = document.getElementById('imagePromptInput').value.trim();
    if (!prompt) {
        showToast('请输入图片提示词', 'error');
        return;
    }

    closeModal('imageRegenerateModal');
    showLoading('正在重新生成图片...');

    try {
        const response = await fetch('/api/articles/regenerate-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                article_id: currentArticle.id,
                image_type: currentImageRegenerate.type,
                figure_index: currentImageRegenerate.figureIndex || null,
                prompt: prompt
            })
        });
        const data = await response.json();

        if (data.success) {
            showToast(data.message, 'success');
            // 刷新预览
            await previewArticle(currentArticle.id);
            loadArticles();
        } else {
            showToast('生成失败: ' + (data.detail || '未知错误'), 'error');
        }
    } catch (error) {
        showToast('生成失败: ' + error.message, 'error');
    } finally {
        hideLoading();
        currentImageRegenerate = null;
    }
}

async function handleDraftForArticle(articleId, hasMediaId) {
    if (hasMediaId) {
        // 修改草稿 - 调用更新接口
        showLoading('正在更新草稿...');
        try {
            const response = await fetch('/api/wechat/draft/update', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ article_id: articleId })
            });
            const data = await response.json();
            if (data.success) {
                showToast('草稿更新成功！', 'success');
                loadArticles();
            } else {
                showToast('更新失败: ' + (data.detail || '未知错误'), 'error');
            }
        } catch (error) {
            showToast('更新失败: ' + error.message, 'error');
        } finally {
            hideLoading();
        }
    } else {
        // 上传草稿 - 调用新增接口
        await uploadDraftFor(articleId);
    }
}

async function uploadDraftFor(articleId) {
    showLoading('正在上传草稿...');
    try {
        const response = await fetch('/api/wechat/draft/upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ article_id: articleId })
        });
        const data = await response.json();
        if (data.success) {
            showToast('草稿上传成功！', 'success');
            loadArticles();
        } else {
            showToast('上传失败: ' + (data.detail || '未知错误'), 'error');
        }
    } catch (error) {
        showToast('上传失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function uploadDraft() {
    if (currentArticle) {
        await uploadDraftFor(currentArticle.id);
        closeModal('articleModal');
    }
}

// ===== 草稿相关 =====
async function loadDrafts() {
    try {
        const response = await fetch('/api/wechat/draft/list');
        const data = await response.json();

        if (data.success) {
            renderDraftList(data.item || []);
        } else {
            document.getElementById('draftList').innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📋</span>
                    <p>请先绑定公众号后查看草稿</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('加载草稿失败:', error);
    }
}

function renderDraftList(drafts) {
    const container = document.getElementById('draftList');

    if (drafts.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📋</span>
                <p>暂无草稿</p>
            </div>
        `;
        return;
    }

    container.innerHTML = drafts.map(draft => {
        const article = draft.content?.news_item?.[0] || {};
        return `
            <div class="draft-item">
                <div class="draft-info">
                    <div class="draft-title">${escapeHtml(article.title || '无标题')}</div>
                    <div class="draft-time">${formatTimestamp(draft.update_time)}</div>
                </div>
                <div class="draft-actions">
                    <button class="btn btn-sm btn-primary" onclick="publishDraft('${draft.media_id}')">
                        发布
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteDraft('${draft.media_id}')">
                        删除
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

async function publishDraft(mediaId) {
    if (!confirm('确定要发布这篇草稿吗？发布后将无法撤回。')) return;

    showLoading('正在发布...');
    try {
        const response = await fetch(`/api/wechat/draft/${mediaId}/publish`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            showToast('发布任务已提交！', 'success');
            loadDrafts();
        } else {
            showToast('发布失败: ' + (data.detail || '未知错误'), 'error');
        }
    } catch (error) {
        showToast('发布失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function deleteDraft(mediaId) {
    if (!confirm('确定要删除这篇草稿吗？')) return;

    try {
        const response = await fetch(`/api/wechat/draft/${mediaId}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        if (data.success) {
            showToast('删除成功！', 'success');
            loadDrafts();
        } else {
            showToast('删除失败: ' + (data.detail || '未知错误'), 'error');
        }
    } catch (error) {
        showToast('删除失败: ' + error.message, 'error');
    }
}

// ===== 配置相关 =====
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();

        // LLM配置
        document.getElementById('configLlmBase').value = config.llm?.api_base || '';
        document.getElementById('configLlmModel').value = config.llm?.model || '';
        document.getElementById('configLlmTemp').value = config.llm?.temperature || 0.7;
        document.getElementById('configLlmTokens').value = config.llm?.max_tokens || 4096;

        // 图片配置
        document.getElementById('configImageUrl').value = config.image?.api_url || '';
        document.getElementById('configImagePrefix').value = config.image?.default_prompt_prefix || '';

        // 定时任务配置
        document.getElementById('configAutoCron').value = config.scheduler?.auto_cron || '';
        document.getElementById('configSchedulerEnabled').checked = config.scheduler?.enabled || false;

    } catch (error) {
        console.error('加载配置失败:', error);
    }
}

async function saveConfig() {
    const configData = {
        llm: {
            api_base: document.getElementById('configLlmBase').value || null,
            api_key: document.getElementById('configLlmKey').value || null,
            model: document.getElementById('configLlmModel').value || null,
            temperature: parseFloat(document.getElementById('configLlmTemp').value) || null,
            max_tokens: parseInt(document.getElementById('configLlmTokens').value) || null
        },
        image: {
            api_url: document.getElementById('configImageUrl').value || null,
            default_prompt_prefix: document.getElementById('configImagePrefix').value || null
        },
        scheduler: {
            auto_cron: document.getElementById('configAutoCron').value || null,
            enabled: document.getElementById('configSchedulerEnabled').checked
        }
    };

    try {
        const response = await fetch('/api/config', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configData)
        });
        const data = await response.json();

        if (data.success) {
            showToast('配置保存成功！', 'success');
        } else {
            showToast('保存失败: ' + (data.detail || '未知错误'), 'error');
        }
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    }
}

async function bindWechat() {
    const accountName = document.getElementById('configAccountName').value.trim();
    const appId = document.getElementById('configAppId').value.trim();
    const appSecret = document.getElementById('configAppSecret').value.trim();

    if (!accountName) {
        showToast('请填写公众号名称', 'error');
        return;
    }
    if (!appId || !appSecret) {
        showToast('请填写AppID和AppSecret', 'error');
        return;
    }

    showLoading('正在绑定公众号...');
    try {
        const response = await fetch('/api/wechat/bind', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ app_id: appId, app_secret: appSecret, account_name: accountName })
        });
        const data = await response.json();

        if (data.success) {
            showToast('公众号绑定成功！', 'success');
            checkWeChatStatus();
        } else {
            showToast('绑定失败: ' + (data.detail || '未知错误'), 'error');
        }
    } catch (error) {
        showToast('绑定失败: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function checkWeChatStatus() {
    try {
        const response = await fetch('/api/wechat/status');
        const data = await response.json();

        const statusEl = document.getElementById('wechatStatus');
        const boundInfoEl = document.getElementById('wechatBoundInfo');
        const boundNameEl = document.getElementById('boundAccountName');

        if (data.bound && data.valid) {
            statusEl.innerHTML = `
                <span class="status-dot online"></span>
                <span>已绑定: ${data.account_name || data.app_id}</span>
            `;
            // 显示绑定信息
            if (boundInfoEl && data.account_name) {
                boundInfoEl.style.display = 'block';
                boundNameEl.textContent = data.account_name;
            }
            // 回显已保存的公众号名称
            if (data.account_name) {
                document.getElementById('configAccountName').value = data.account_name;
            }
        } else if (data.bound) {
            statusEl.innerHTML = `
                <span class="status-dot"></span>
                <span>Token失效</span>
            `;
            if (boundInfoEl) boundInfoEl.style.display = 'none';
        } else {
            statusEl.innerHTML = `
                <span class="status-dot offline"></span>
                <span>未绑定公众号</span>
            `;
        }
    } catch (error) {
        console.error('检查微信状态失败:', error);
    }
}

// ===== 弹窗 =====
function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// ===== Loading =====
function showLoading(text = '加载中...') {
    document.getElementById('loadingText').textContent = text;
    document.getElementById('loadingOverlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
}

// ===== Toast =====
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span>${type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ'}</span>
        <span>${escapeHtml(message)}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ===== 工具函数 =====
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatNumber(num) {
    if (num >= 10000) return (num / 10000).toFixed(1) + '万';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN');
}

function formatTimestamp(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('zh-CN');
}

function getStatusText(status) {
    const statusMap = {
        'draft': '草稿',
        'generated': '已生成',
        'uploaded': '已上传',
        'published': '已发布'
    };
    return statusMap[status] || status;
}
