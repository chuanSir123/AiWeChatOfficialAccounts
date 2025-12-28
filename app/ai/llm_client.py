"""
LLM客户端 (OpenAI格式)
"""
import json
import uuid
from typing import List, Optional
import httpx
from ..config import get_config, LLMConfig
from ..models.news import NewsItem
from ..models.article import Article, ArticleStatus


class LLMClient:
    """OpenAI格式LLM客户端"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or get_config().llm
    
    async def _call_api(self, messages: List[dict], max_tokens: Optional[int] = None) -> str:
        """调用LLM API"""
        url = f"{self.config.api_base}/chat/completions"
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            return data["choices"][0]["message"]["content"]
    
    async def generate_article(
        self, 
        news_items: List[NewsItem], 
        custom_prompt: Optional[str] = None,
        news_details: Optional[List['NewsDetail']] = None
    ) -> Article:
        """根据新闻生成公众号文章
        
        Args:
            news_items: 新闻列表
            custom_prompt: 自定义提示词
            news_details: 新闻详情列表（包含正文），如果提供则使用正文内容
        """
        
        # 构建新闻内容
        news_content = ""
        for i, news in enumerate(news_items, 1):
            # 优先使用详情中的正文内容
            detail = news_details[i-1] if news_details and i <= len(news_details) else None
            if detail and detail.content:
                # 清理HTML标签，提取纯文本
                import re
                clean_content = re.sub(r'<[^>]+>', '', detail.content)
                clean_content = clean_content[:2000]  # 限制长度
                news_content += f"\n【新闻{i}】\n标题：{news.title}\n正文：{clean_content}\n"
            else:
                news_content += f"\n【新闻{i}】\n标题：{news.title}\n摘要：{news.summary}\n"
        
        system_prompt = """
        你是一位顶级科技自媒体主笔（‘机器之心’风格），拥有敏锐的行业洞察力和极强的文字感染力。你的任务是根据提供的AI热点新闻，撰写一篇适合微信公众号发布的深度早报。
        【核心写作心法】
        1. **拒绝流水账**：不要机械地罗列新闻（新闻1、新闻2...）。你需要找到这些新闻背后的共同逻辑（如“门槛降低”、“成本内卷”、“应用爆发”），用一条主线串联全文。
        2. **说人话，有温度**：把“低延迟高并发”翻译成“眨眼间搞定”。多用“我们”、“你”来拉近距离。技术是冰冷的，但你的文字要有情绪（兴奋、焦虑、期待）。
        3. **结构流线型**：
            - **标题**：必须“标题党”但不过分，利用好奇心、紧迫感或反差萌（15-30字）。
            - **开头**：从现象、痛点或一个具体的场景切入，3秒内抓住读者注意力。\n
            - **正文**：小标题不要用“某某产品发布”，要用观点句（如“编程门槛彻底消失”）。
            - **结尾**：**严禁使用“总结与展望”作为标题**。结尾应当是情绪的升华、犀利的预判，或者一个引人深思的提问，引导读者去评论区互动。
        【硬性要求】
        1. 文章长度：1500-2500字。
        2. 配图逻辑：根据内容情感节奏，插入0-5张图片占位符 `<figureX>`。图片提示词必须是纯视觉描述，**严禁**生成包含文字、图表、UI界面的图片。
        【HTML输出规范（必须严格执行）】
        所有输出必须封装在JSON的 content 字段中，且必须使用以下内联样式HTML：
        - **文章容器**：内容不需要外层div，直接输出p标签序列。
        - **主标题**（仅用于第一行）：<p style=\"font-size:18px;font-weight:bold;color:#333;margin:20px 0 10px 0;\"><strong>标题文字</strong></p>
        - **小标题**（观点句）：<p style=\"font-size:16px;font-weight:bold;color:#333;margin:24px 0 10px 0;\"><strong>小标题文字</strong></p>
        - **正文段落**（短句为主，多换行）：<p style=\"font-size:15px;line-height:1.8;color:#333;margin-bottom:16px;text-align:justify;\">正文内容</p>
        - **重点强调**：<strong>加粗文字</strong>
        - **技术术语/补充**：<em>斜体文字</em>
        - **金句/引用**：<blockquote style=\"border-left:4px solid #d0d0d0;padding:10px 15px;margin:20px 0;background:#f8f8f8;color:#555;font-size:14px;line-height:1.6;\">引用或金句内容</blockquote>
        - **列表**（仅用于参数对比）：<p style=\"font-size:15px;line-height:1.8;color:#333;padding-left:20px;margin-bottom:8px;\">• 列表内容</p>
        - **插图占位**：<figure1> <figure2> ...
        - **禁止使用**：h1-h6, ul, ol, li, div, span（除非必要）。
        请以JSON格式返回，包含以下字段：
        - title: 文章标题
        - digest: 文章摘要(50-100字，禁止超过100字)
        - content: 文章HTML内容（必须使用内联样式，可包含<figure1>到<figure5>占位符）
        - cover_prompt: 封面图生成提示词（30字以内，描述视觉场景，不含文字和图表）
        - figure_prompt_list: 插图提示词数组（每个元素30字以内，描述视觉场景，不含文字和图表，数量与content中的占位符数量一致，可为空数组）
"""
        
        user_prompt = f"请根据以下AI热点新闻撰写公众号文章：\n{news_content}"
        
        if custom_prompt:
            user_prompt += f"\n\n额外要求：{custom_prompt}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self._call_api(messages)
        print(response)
        
        # 解析JSON响应
        data = await self._parse_json_response(response)
        
        # 获取figure_prompt_list，确保是列表
        figure_prompts = data.get("figure_prompt_list", [])
        if isinstance(figure_prompts, str):
            figure_prompts = [figure_prompts] if figure_prompts else []
        
        # 获取配置的公众号名称作为作者
        from ..config import get_config
        config = get_config()
        author_name = config.wechat.account_name or "AI资讯"
        
        article = Article(
            id=str(uuid.uuid4())[:8],
            title=data.get("title", "AI热点资讯"),
            digest=data.get("digest", ""),
            content=data.get("content", response),
            author=author_name,
            cover_prompt=data.get("cover_prompt", ""),
            figure_prompt_list=figure_prompts,
            source_news=[n.id for n in news_items],
            status=ArticleStatus.GENERATED
        )
        
        return article
    
    async def _parse_json_response(self, response: str) -> dict:
        """解析LLM的JSON响应，如果失败则调用LLM修复"""
        try:
            # 尝试提取JSON
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            return json.loads(json_str.strip())
        except json.JSONDecodeError:
            print("JSON解析失败，尝试使用LLM修复...")
            # 调用LLM修复JSON
            repair_messages = [
                {
                    "role": "system", 
                    "content": "你是一个JSON修复专家。用户会提供一段可能格式不正确的文本，请提取其中的信息并返回正确格式的JSON。只返回JSON，不要其他内容。"
                },
                {
                    "role": "user", 
                    "content": f"请将以下内容转换为正确的JSON格式（包含title, digest, content, cover_prompt, figure_prompt_list字段，其中figure_prompt_list是数组）：\n\n{response}"
                }
            ]
            
            repaired_response = await self._call_api(repair_messages)
            
            try:
                # 再次尝试解析
                json_str = repaired_response
                if "```json" in repaired_response:
                    json_str = repaired_response.split("```json")[1].split("```")[0]
                elif "```" in repaired_response:
                    json_str = repaired_response.split("```")[1].split("```")[0]
                
                return json.loads(json_str.strip())
            except json.JSONDecodeError:
                # 仍然失败，返回默认值
                print("JSON修复失败，使用默认值")
                return {
                    "title": "AI热点资讯",
                    "digest": "",
                    "content": f"<p>{response}</p>",
                    "cover_prompt": "科技感AI主题封面图",
                    "figure_prompt_list": []
                }
    
    async def generate_cover_prompt(self, title: str, digest: str) -> str:
        """生成封面图提示词"""
        messages = [
            {
                "role": "system",
                "content": "你是一位专业的AI图片提示词专家。请根据文章标题和摘要，生成一个适合作为公众号封面图的图片描述。要求：简洁、富有科技感、与AI主题相关。只返回提示词，不要其他内容。"
            },
            {
                "role": "user",
                "content": f"文章标题：{title}\n文章摘要：{digest}\n\n请生成封面图提示词（30字以内）："
            }
        ]
        
        return await self._call_api(messages, max_tokens=100)
