# AI公众号自动托管系统

一个基于Python的AI驱动微信公众号自动化托管系统。

## 功能特性

- 🔍 **AI热点新闻抓取**: 使用Playwright自动抓取AIBase和AI-Bot的热点新闻
- 📝 **AI文章生成**: 基于热点新闻自动创作公众号文章
- 🖼️ **AI封面图生成**: 自动生成文章封面图片
- 📱 **微信公众号集成**: 通过API管理草稿
- ⏰ **定时任务**: 支持定时自动抓取和生成
- 🌐 **Web管理界面**: 可视化配置和管理
- 🔐 **登录认证**: 支持环境变量配置用户名密码

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chrome
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

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `AUTH_USERNAME` | 登录用户名 | 空 (不启用认证) |
| `AUTH_PASSWORD` | 登录密码 | 空 (不启用认证) |

> **注意**: 如果未设置 `AUTH_USERNAME` 和 `AUTH_PASSWORD`，系统将跳过登录认证，便于本地开发。

## HuggingFace Spaces 部署

本项目支持在 HuggingFace Spaces 上部署。

### 部署步骤

1. 在 HuggingFace 创建新的 Space，选择 **Docker** 作为 SDK
2. 将本项目代码上传到 Space（或连接 Git 仓库）
3. 在 Space 的 **Settings > Secrets** 中配置环境变量：
   - `AUTH_USERNAME`: 登录用户名
   - `AUTH_PASSWORD`: 登录密码
   - 其他配置（如微信AppID等）可在登录后通过Web界面配置

### Dockerfile 说明

项目包含预配置的 `Dockerfile`，使用 Playwright 官方镜像，已包含 Chrome 浏览器依赖。

## 项目结构

```
├── app/
│   ├── main.py           # FastAPI入口
│   ├── config.py         # 配置管理
│   ├── auth.py           # 认证模块
│   ├── models/           # 数据模型
│   ├── scrapers/         # 新闻抓取模块
│   ├── ai/               # AI模块(LLM/图片)
│   ├── wechat/           # 微信公众号模块
│   ├── scheduler/        # 定时任务
│   ├── api/              # API路由
│   └── static/           # 前端文件
├── data/                 # 数据存储
├── config.yaml           # 配置文件
├── Dockerfile            # Docker配置
└── requirements.txt      # 依赖
```

## API文档

启动服务后访问 http://localhost:8000/docs 查看API文档
