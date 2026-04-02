"""
AstrBot 新闻联播查询插件
功能：查询新闻联播内容，并使用 AI 进行智能总结
数据来源：https://github.com/DuckBurnIncense/xin-wen-lian-bo

"""

import os
import re
import json
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass
from xml.etree import ElementTree as ET

import markdown

import asyncio
import aiohttp
import aiofiles
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger


@dataclass
class NewsItem:
    """单条新闻数据结构"""

    title: str
    content: str
    category: str = ""


@dataclass
class DailyNews:
    """单日新闻联播数据结构"""

    date: str
    date_display: str
    items: List[NewsItem]
    raw_content: str


@register(
    "xinwen_lianbo",
    "freeliujian",
    "新闻联播查询插件 - 查询并 AI 总结新闻联播内容",
    "1.0.0",
)
class XinwenLianboPlugin(Star):
    DATA_SOURCE_URL = "https://raw.githubusercontent.com/DuckBurnIncense/xin-wen-lian-bo/master/news/{date}.md"

    CONCURRENCY_LIMIT = 10

    def __init__(self, context: Context):
        super().__init__(context)

        base_dir = StarTools.get_data_dir()
        self.cache_dir = base_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_duration = 86400
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> dict:
        """从 JSON 文件加载提示词模板"""
        prompts_file = os.path.join(os.path.dirname(__file__), "prompts.json")
        try:
            with open(prompts_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载提示词文件失败：{e}")
            return {}

    async def _fetch_from_github(
        self, date: str, session: Optional[aiohttp.ClientSession] = None
    ) -> Optional[str]:
        """从 GitHub 获取指定日期的新闻，支持传入共享 session"""
        url = self.DATA_SOURCE_URL.format(date=date)

        async def _do_fetch(s: aiohttp.ClientSession) -> Optional[str]:
            try:
                async with s.get(
                    url, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        await self._save_to_cache(date, content)
                        return content
                    else:
                        logger.warning(
                            f"获取 {date} 新闻失败，状态码：{response.status}"
                        )
                        return None
            except Exception as e:
                logger.error(f"获取 {date} 新闻时出错：{e}")
                return None

        if session is not None:
            return await _do_fetch(session)

        async with aiohttp.ClientSession() as new_session:
            return await _do_fetch(new_session)

    async def _save_to_cache(self, date: str, content: str):
        """保存内容到本地缓存"""
        cache_file = os.path.join(self.cache_dir, f"{date}.md")
        try:
            async with aiofiles.open(cache_file, "w", encoding="utf-8") as f:
                await f.write(content)
        except Exception as e:
            logger.warning(f"保存缓存失败：{e}")

    async def _load_from_cache(self, date: str) -> Optional[str]:
        """从本地缓存加载内容"""
        cache_file = os.path.join(self.cache_dir, f"{date}.md")

        if not os.path.exists(cache_file):
            return None

        mtime = os.path.getmtime(cache_file)
        if datetime.now().timestamp() - mtime > self.cache_duration:
            return None

        try:
            async with aiofiles.open(cache_file, "r", encoding="utf-8") as f:
                return await f.read()
        except Exception as e:
            logger.warning(f"读取缓存失败：{e}")
            return None

    async def _get_news(
        self, date: str, session: Optional[aiohttp.ClientSession] = None
    ) -> Optional[DailyNews]:
        """获取指定日期的新闻"""
        content = await self._load_from_cache(date)

        if content is None:
            content = await self._fetch_from_github(date, session=session)

        if content is None:
            return None

        return self._parse_news(date, content)

    def _parse_news(self, date: str, content: str) -> DailyNews:
        """使用 markdown 库解析新闻内容"""
        year = date[:4]
        month = date[4:6]
        day = date[6:8]
        date_display = f"{year}年{month}月{day}日"

        items = []
        html = markdown.markdown(content)
        try:
            root = ET.fromstring(f"<root>{html}</root>")
        except ET.ParseError:
            return DailyNews(
                date=date,
                date_display=date_display,
                items=[NewsItem(title="新闻联播", content=content, category="综合")],
                raw_content=content,
            )
        current_title = None
        current_parts: List[str] = []
        in_detail_section = False

        def _element_text(el: ET.Element) -> str:
            """递归提取元素内所有文本（包括子标签中的文本）"""
            return "".join(el.itertext()).strip()

        def _save_current():
            nonlocal current_title, current_parts
            if current_title and current_parts:
                body = "\n".join(current_parts).strip()
                if body:
                    items.append(
                        NewsItem(
                            title=current_title,
                            content=body,
                            category=self._detect_category(current_title, body),
                        )
                    )
            current_title = None
            current_parts = []

        for el in root:
            tag = el.tag.lower()

            if tag == "h2":
                heading = _element_text(el)
                if heading == "详细新闻":
                    in_detail_section = True
                continue

            if tag == "h3" and in_detail_section:
                _save_current()
                current_title = _element_text(el)
                continue

            if tag in ("h1", "hr"):
                continue

            # 正文段落、列表等
            if current_title:
                text = _element_text(el)
                if text:
                    current_parts.append(text)

        _save_current()

        if not items:
            items.append(
                NewsItem(
                    title="新闻联播",
                    content=content,
                    category="综合",
                )
            )

        return DailyNews(
            date=date,
            date_display=date_display,
            items=items,
            raw_content=content,
        )

    def _detect_category(self, title: str, content: str) -> str:
        """检测新闻分类"""
        title_lower = title.lower()
        content_lower = content.lower()

        category_keywords = {
            "时政": [
                "总书记",
                "主席",
                "总理",
                "人大",
                "政协",
                "政治局",
                "会议",
            ],
            "经济": [
                "经济",
                "发展",
                "增长",
                "GDP",
                "产业",
                "企业",
                "市场",
                "金融",
                "贸易",
            ],
            "科技": [
                "科技",
                "创新",
                "技术",
                "研发",
                "人工智能",
                "芯片",
                "航天",
                "卫星",
            ],
            "社会": ["民生", "就业", "教育", "医疗", "社保", "住房", "养老"],
            "文化": ["文化", "艺术", "文物", "非遗", "旅游", "体育", "奥运"],
            "国际": [
                "国际",
                "外交",
                "访问",
                "会谈",
                "合作",
                "联合国",
                "美国",
                "俄罗斯",
                "欧洲",
            ],
            "军事": ["军队", "国防", "军事", "演习", "装备", "官兵"],
            "农业": ["农业", "农村", "农民", "粮食", "丰收", "乡村振兴"],
            "生态": ["生态", "环保", "绿色", "气候", "碳达峰", "碳中和", "环境"],
            "法律": ["法治", "法律", "司法", "法院", "检察", "立法"],
        }

        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in title_lower or keyword in content_lower:
                    return category

        return "综合"

    def _format_news(self, news: DailyNews, show_content: bool = True) -> str:
        """格式化新闻输出"""
        result = f"**日期 {news.date_display}** \n\n"

        for idx, item in enumerate(news.items, 1):
            result += f"{idx}. **{item.title}** "
            if item.category:
                result += f" `[{item.category}]`"
            result += "\n"

            if show_content:
                result += f"   {item.content}\n\n"

        return result.strip()

    def _truncate_content(self, news: DailyNews, max_length: int = 6000) -> str:
        """截断新闻内容以适应 LLM 上下文限制，保留完整标题，只截断正文"""
        full_content = f"新闻联播 {news.date_display}\n\n"
        current_length = len(full_content)

        for item in news.items:
            title_line = f"## {item.title}\n"
            current_length += len(title_line)

            remaining = max_length - current_length - 10  # 留余量给换行符
            if remaining <= 0:
                full_content += title_line + "[内容省略]\n\n"
                break

            if len(item.content) <= remaining:
                full_content += title_line + item.content + "\n\n"
                current_length += len(item.content) + 2
            else:
                truncated = item.content[:remaining] + "..."
                full_content += title_line + truncated + "\n\n"
                break

        return full_content

    async def _summarize_with_ai(
        self, event: AstrMessageEvent, news: DailyNews, summary_type: str = "brief"
    ) -> str:

        prompt_template = self.prompts.get(summary_type)
        if not prompt_template:
            prompt_template = self.prompts.get(
                "brief", "请总结以下新闻内容：\n\n{content}"
            )

        full_content = self._truncate_content(news, max_length=6000)
        prompt = prompt_template.format(content=full_content)

        try:
            event.should_call_llm(True)

            umo = event.unified_msg_origin
            provider_id = await self.context.get_current_chat_provider_id(umo=umo)

            logger.info(f"使用 LLM 提供商 ID: {provider_id}")

            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id, prompt=prompt
            )

            # 步骤 3: 获取返回文本
            if not llm_resp or not llm_resp.completion_text:
                raise ValueError("LLM 返回空响应")

            return llm_resp.completion_text

        except Exception as e:
            logger.error(f"AI 总结失败：{e}")
            error_str = str(e)

            # 友好的错误提示
            if "502" in error_str:
                return "❌ AI 总结失败：LLM 服务商暂时不可用（502 错误），请稍后重试。"
            elif "429" in error_str or "rate limit" in error_str.lower():
                return "❌ AI 总结失败：请求过于频繁，触发速率限制。"
            elif "401" in error_str or "unauthorized" in error_str.lower():
                return "❌ AI 总结失败：API 密钥无效或权限不足，请检查 LLM 配置。"
            else:
                return f"❌ AI 总结失败：{error_str}"

    @filter.command("xinwen")
    async def query_news(self, event: AstrMessageEvent, date: str = "today"):
        """查询新闻联播"""
        parsed_date = self._parse_date(date)
        if not parsed_date:
            yield event.plain_result(
                "日期格式错误。支持的格式：today, yesterday, YYYYMMDD, YYYY-MM-DD"
            )
            return

        yield event.plain_result(f"正在获取 {parsed_date} 的新闻联播...")

        news = await self._get_news(parsed_date)

        if not news:
            yield event.plain_result(
                f"未找到 {parsed_date} 的新闻联播内容。\n可能原因：\n1. 该日期没有新闻联播\n2. 数据尚未更新\n3. 网络连接问题"
            )
            return

        result = self._format_news(news, show_content=True, show_preview=True)
        yield event.plain_result(result)

    @filter.command("xinwen-summary")
    async def summarize_news(
        self, event: AstrMessageEvent, date: str = "today", style: str = "brief"
    ):
        """AI 总结新闻联播"""
        parsed_date = self._parse_date(date)
        if not parsed_date:
            yield event.plain_result(
                "日期格式错误。支持的格式：today, yesterday, YYYYMMDD, YYYY-MM-DD"
            )
            return

        if style not in ["brief", "detailed", "category"]:
            style = "brief"

        # 获取新闻
        yield event.plain_result(f"正在获取 {parsed_date} 的新闻联播...")

        news = await self._get_news(parsed_date)

        if not news:
            yield event.plain_result(f"未找到 {parsed_date} 的新闻联播内容。")
            return

        # 显示统计信息
        news_stats = f"新闻统计：共 {len(news.items)} 条新闻"
        category_counts = {}
        for item in news.items:
            cat = item.category or "综合"
            category_counts[cat] = category_counts.get(cat, 0) + 1
        if category_counts:
            news_stats += (
                "（"
                + ", ".join([f"{k}:{v}" for k, v in category_counts.items()])
                + "）"
            )

        yield event.plain_result(news_stats)
        yield event.plain_result("正在进行 AI 分析，请稍候（可能需要 10-30 秒）...")

        # AI 总结
        summary = await self._summarize_with_ai(event, news, summary_type=style)
        yield event.plain_result(summary)

    @filter.command("xinwen-search")
    async def search_news(self, event: AstrMessageEvent, *, keyword: str):
        """搜索新闻联播内容"""
        if not keyword or len(keyword) < 2:
            yield event.plain_result("搜索关键词至少需要 2 个字符")
            return

        yield event.plain_result(f"正在搜索包含「{keyword}」的新闻...")

        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(30)]

        semaphore = asyncio.Semaphore(self.CONCURRENCY_LIMIT)

        async def _limited_get_news(date: str, session: aiohttp.ClientSession):
            async with semaphore:
                return await self._get_news(date, session=session)

        async with aiohttp.ClientSession() as session:
            news_list: List[Optional[DailyNews]] = await asyncio.gather(
                *[_limited_get_news(date, session) for date in dates],
            )

        results = []
        for news in news_list:
            if news is None:
                continue
            matched_items = [
                item
                for item in news.items
                if keyword.lower() in item.title.lower()
                or keyword.lower() in item.content.lower()
            ]
            if matched_items:
                results.append({"date": news.date_display, "items": matched_items})
            if len(results) >= 5:
                break

        if not results:
            yield event.plain_result(f"未找到包含「{keyword}」的新闻")
            return

        result_text = f"## 搜索「{keyword}」的结果\n\n"
        for r in results:
            result_text += f"### {r['date']}\n"
            for item in r["items"]:
                result_text += f"- **{item.title}**\n"
                result_text += f"  {item.content}\n\n"

        yield event.plain_result(result_text)

    @filter.command("xinwen-latest")
    async def latest_news(self, event: AstrMessageEvent, days: int = 3):
        """查看最近几天的新闻联播"""
        if days < 1 or days > 7:
            days = 3

        yield event.plain_result(f"正在获取最近 {days} 天的新闻联播...")

        results = []
        today = datetime.now()

        for i in range(days):
            date = (today - timedelta(days=i)).strftime("%Y%m%d")
            news = await self._get_news(date)
            if news:
                results.append(news)

        if not results:
            yield event.plain_result("获取新闻失败，请稍后重试")
            return

        result_text = f"## 最近 {len(results)} 天新闻联播\n\n"
        for news in results:
            result_text += f"### {news.date_display}\n"
            for idx, item in enumerate(news.items, 1):
                result_text += f"{idx}. {item.title}"
                if item.category:
                    result_text += f" `[{item.category}]`"
                result_text += "\n"
            if len(news.items) >= 8:
                result_text += f"\n> 共 {len(news.items)} 条新闻\n"
            result_text += "\n"

        yield event.plain_result(result_text)

    @filter.command("xinwen-help")
    async def help_command(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = """## 新闻联播查询插件

### 命令列表

| 命令 | 说明 | 示例 |
|------|------|------|
| `/xinwen [日期]` | 查询指定日期的新闻 | `/xinwen`, `/xinwen 20260330` |
| `/xinwen-summary [日期] [style]` | AI 总结新闻 | `/xinwen-summary`, `/xinwen-summary today detailed` |
| `/xinwen-search <关键词>` | 搜索新闻内容 | `/xinwen-search 经济` |
| `/xinwen-latest [天数]` | 查看最近几天新闻 | `/xinwen-latest`, `/xinwen-latest 5` |
| `/xinwen-help` | 显示帮助信息 | `/xinwen-help` |

### 日期格式
- `today` - 今天（默认）
- `yesterday` - 昨天
- `YYYYMMDD` - 如 20260330
- `YYYY-MM-DD` - 如 2026-03-30

### 总结风格
- `brief` - 简要总结（默认）
- `detailed` - 详细分析
- `category` - 分类统计

### 数据来源
数据来自 GitHub: https://github.com/DuckBurnIncense/xin-wen-lian-bo
"""
        yield event.plain_result(help_text)

    def _parse_date(self, date_str: str) -> Optional[str]:
        """解析日期字符串为 YYYYMMDD 格式"""
        date_str = date_str.lower().strip()

        if date_str == "today":
            return datetime.now().strftime("%Y%m%d")
        elif date_str == "yesterday":
            return (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

        if re.match(r"^\d{8}$", date_str):
            return date_str

        match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", date_str)
        if match:
            return f"{match.group(1)}{match.group(2)}{match.group(3)}"

        match = re.match(r"^(\d{4})/(\d{2})/(\d{2})$", date_str)
        if match:
            return f"{match.group(1)}{match.group(2)}{match.group(3)}"

        return None
