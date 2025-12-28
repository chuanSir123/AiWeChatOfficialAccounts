# AI公众号自动托管系统

一个基于Python的AI驱动微信公众号自动化托管系统。

## 功能特性

- 🔍 **AI热点新闻抓取**: 使用Playwright自动抓取AIBase和AI-Bot的热点新闻
- 📝 **AI文章生成**: 基于热点新闻自动创作公众号文章
- 🖼️ **AI封面图生成**: 自动生成文章封面图片
- 📱 **微信公众号集成**: 通过API管理草稿
- ⏰ **定时任务**: 支持定时自动抓取和生成
- 🌐 **Web管理界面**: 可视化配置和管理

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置

启动服务后，在Web管理界面中进行配置（无需手动编辑配置文件）：

- **微信公众号**: `app_id` 和 `app_secret`
- **LLM配置**: API地址、密钥、模型
- **图片生成**: API地址
- **定时任务**: 自动发布的Cron表达式

### 3. 启动服务

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问管理界面

打开浏览器访问: http://localhost:8000

## 项目结构

```
├── app/
│   ├── main.py           # FastAPI入口
│   ├── config.py         # 配置管理
│   ├── models/           # 数据模型
│   ├── scrapers/         # 新闻抓取模块
│   ├── ai/               # AI模块(LLM/图片)
│   ├── wechat/           # 微信公众号模块
│   ├── scheduler/        # 定时任务
│   ├── api/              # API路由
│   └── static/           # 前端文件
├── data/                 # 数据存储
├── config.yaml           # 配置文件
└── requirements.txt      # 依赖
```

## API文档

启动服务后访问 http://localhost:8000/docs 查看API文档
