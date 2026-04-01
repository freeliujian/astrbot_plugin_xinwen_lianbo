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

import aiohttp
import aiofiles
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
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


@register("xinwen_lianbo", "Your Name", "新闻联播查询插件 - 查询并 AI 总结新闻联播内容", "1.0.0")
class XinwenLianboPlugin(Star):
    """新闻联播查询插件主类"""

    DATA_SOURCE_URL = "https://raw.githubusercontent.com/DuckBurnIncense/xin-wen-lian-bo/master/news/{date}.md"

    def __init__(self, context: Context):
        super().__init__(context)

        self.plugin_dir = os.path.dirname(__file__)
        self.data_dir = os.path.join(self.plugin_dir, "data")
        self.cache_dir = os.path.join(self.plugin_dir, "cache")
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

        self.cache_duration = 3600
        self.available_dates = self._load_available_dates()

    def _load_available_dates(self) -> List[str]:
        """加载可用日期列表"""
        cache_file = os.path.join(self.cache_dir, "available_dates.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cached_time = datetime.fromisoformat(data.get('cached_at', '2000-01-01'))
                    if datetime.now() - cached_time < timedelta(hours=24):
                        return data.get('dates', [])
            except Exception as e:
                logger.warning(f"加载可用日期缓存失败：{e}")
        return []

    def _save_available_dates(self, dates: List[str]):
        """保存可用日期列表"""
        cache_file = os.path.join(self.cache_dir, "available_dates.json")
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'dates': dates,
                    'cached_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存可用日期缓存失败：{e}")

    async def _fetch_from_github(self, date: str) -> Optional[str]:
        """从 GitHub 获取指定日期的新闻"""
        url = self.DATA_SOURCE_URL.format(date=date)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        content = await response.text()
                        await self._save_to_cache(date, content)
                        return content
                    else:
                        logger.warning(f"获取 {date} 新闻失败，状态码：{response.status}")
                        return None
        except Exception as e:
            logger.error(f"获取 {date} 新闻时出错：{e}")
            return None

    async def _save_to_cache(self, date: str, content: str):
        """保存内容到本地缓存"""
        cache_file = os.path.join(self.cache_dir, f"{date}.md")
        try:
            async with aiofiles.open(cache_file, 'w', encoding='utf-8') as f:
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
            async with aiofiles.open(cache_file, 'r', encoding='utf-8') as f:
                return await f.read()
        except Exception as e:
            logger.warning(f"读取缓存失败：{e}")
            return None

    async def _get_news(self, date: str) -> Optional[DailyNews]:
        """获取指定日期的新闻"""
        content = await self._load_from_cache(date)

        if content is None:
            content = await self._fetch_from_github(date)

        if content is None:
            return None

        return self._parse_news(date, content)

    def _parse_news(self, date: str, content: str) -> DailyNews:
        """解析 Markdown 格式的新闻内容"""
        items = []

        year = date[:4]
        month = date[4:6]
        day = date[6:8]
        date_display = f"{year}年{month}月{day}日"

        pattern = r'##+\s*(.+?)\n\n?([\s\S]*?)(?=##+|\Z)'
        matches = re.findall(pattern, content)

        for title, item_content in matches:
            title = title.strip()
            item_content = item_content.strip()

            if title and item_content:
                category = self._detect_category(title, item_content)
                items.append(NewsItem(
                    title=title,
                    content=item_content,
                    category=category
                ))

        if not items:
            items.append(NewsItem(
                title="新闻联播",
                content=content,
                category="综合"
            ))

        return DailyNews(
            date=date,
            date_display=date_display,
            items=items,
            raw_content=content
        )

    def _detect_category(self, title: str, content: str) -> str:
        """检测新闻分类"""
        title_lower = title.lower()
        content_lower = content.lower()

        category_keywords = {
            "时政": ["习近平", "总书记", "主席", "总理", "人大", "政协", "政治局", "会议"],
            "经济": ["经济", "发展", "增长", "GDP", "产业", "企业", "市场", "金融", "贸易"],
            "科技": ["科技", "创新", "技术", "研发", "人工智能", "芯片", "航天", "卫星"],
            "社会": ["民生", "就业", "教育", "医疗", "社保", "住房", "养老"],
            "文化": ["文化", "艺术", "文物", "非遗", "旅游", "体育", "奥运"],
            "国际": ["国际", "外交", "访问", "会谈", "合作", "联合国", "美国", "俄罗斯", "欧洲"],
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
        result = f"## 新闻联播 {news.date_display}\n\n"

        for idx, item in enumerate(news.items, 1):
            result += f"{idx}. **{item.title}**"
            if item.category:
                result += f" `[{item.category}]`"
            result += "\n"

            if show_content:
                content_preview = item.content[:200].replace('\n', ' ')
                if len(item.content) > 200:
                    content_preview += "..."
                result += f"   {content_preview}\n"

            result += "\n"

        return result.strip()

    def _truncate_content(self, news: DailyNews, max_length: int = 4000) -> str:
        """截断新闻内容以适应 LLM 上下文限制"""
        full_content = f"新闻联播 {news.date_display}\n\n"
        current_length = len(full_content)

        for item in news.items:
            item_text = f"## {item.title}\n{item.content}\n\n"
            if current_length + len(item_text) > max_length:
                remaining = max_length - current_length - 100
                if remaining > 50:
                    truncated_content = item.content[:remaining] + "..."
                    full_content += f"## {item.title}\n{truncated_content}\n\n"
                else:
                    full_content += f"## {item.title}\n[内容省略]\n\n"
                break
            full_content += item_text
            current_length += len(item_text)

        return full_content

    async def _summarize_with_ai(self, event: AstrMessageEvent, news: DailyNews, summary_type: str = "brief") -> str:
        
        # 准备提示词模板
        if summary_type == "brief":
            prompt_template = """请对以下新闻联播内容进行简要总结：

{content}

要求：
1. 总结主要新闻要点（3-5 条）
2. 每条要点简洁明了，不超过 50 字
3. 突出重要政策、事件和数据
4. 使用中文输出

请按以下格式输出：
## 今日要闻总结

1. [要点 1]
2. [要点 2]
3. [要点 3]
..."""
        elif summary_type == "detailed":
            prompt_template = """请对以下新闻联播内容进行详细分析和总结：

{content}

要求：
1. 分领域总结（时政、经济、社会、国际等）
2. 每个领域列出重要新闻并简要分析
3. 提炼今日政策重点和趋势
4. 使用中文输出

请按以下格式输出：
## 新闻联播深度分析

### 一、时政要闻
...

### 二、经济动态
...

### 三、社会民生
...

### 四、国际视野
...

### 五、今日要点
总结今日最重要的 1-3 个要点"""
        else:
            prompt_template = """请对以下新闻联播内容按类别进行分类总结：

{content}

要求：
1. 将新闻按类别分组（时政、经济、科技、社会、国际等）
2. 每类列出相关新闻标题
3. 统计各类别新闻数量
4. 使用中文输出

请按以下格式输出：
## 新闻分类统计

### 时政（X 条）
- [新闻标题 1]
- [新闻标题 2]
...

### 经济（X 条）
..."""

        full_content = self._truncate_content(news, max_length=4000)
        prompt = prompt_template.format(content=full_content)

        try:
            
            event.should_call_llm(True)

            umo = event.unified_msg_origin
            provider_id = await self.context.get_current_chat_provider_id(umo=umo)

            logger.info(f"使用 LLM 提供商 ID: {provider_id}")

            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=prompt
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
            yield event.plain_result("日期格式错误。支持的格式：today, yesterday, YYYYMMDD, YYYY-MM-DD")
            return

        yield event.plain_result(f"正在获取 {parsed_date} 的新闻联播...")

        news = await self._get_news(parsed_date)

        if not news:
            yield event.plain_result(f"未找到 {parsed_date} 的新闻联播内容。\n可能原因：\n1. 该日期没有新闻联播\n2. 数据尚未更新\n3. 网络连接问题")
            return

        result = self._format_news(news, show_content=True)
        yield event.plain_result(result)

    @filter.command("xinwen-summary")
    async def summarize_news(self, event: AstrMessageEvent, date: str = "today", style: str = "brief"):
        """AI 总结新闻联播"""
        parsed_date = self._parse_date(date)
        if not parsed_date:
            yield event.plain_result("日期格式错误。支持的格式：today, yesterday, YYYYMMDD, YYYY-MM-DD")
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
            news_stats += "（" + ", ".join([f"{k}:{v}" for k, v in category_counts.items()]) + "）"

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

        results = []
        today = datetime.now()

        for i in range(30):
            date = (today - timedelta(days=i)).strftime('%Y%m%d')
            news = await self._get_news(date)

            if news:
                matched_items = []
                for item in news.items:
                    if keyword.lower() in item.title.lower() or keyword.lower() in item.content.lower():
                        matched_items.append(item)

                if matched_items:
                    results.append({
                        'date': news.date_display,
                        'items': matched_items
                    })

            if len(results) >= 5:
                break

        if not results:
            yield event.plain_result(f"未找到包含「{keyword}」的新闻")
            return

        result_text = f"## 搜索「{keyword}」的结果\n\n"
        for r in results:
            result_text += f"### {r['date']}\n"
            for item in r['items']:
                result_text += f"- **{item.title}**\n"
                content_preview = self._extract_context(item.content, keyword)
                result_text += f"  {content_preview}\n\n"

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
            date = (today - timedelta(days=i)).strftime('%Y%m%d')
            news = await self._get_news(date)
            if news:
                results.append(news)

        if not results:
            yield event.plain_result("获取新闻失败，请稍后重试")
            return

        result_text = f"## 最近 {len(results)} 天新闻联播\n\n"
        for news in results:
            result_text += f"### {news.date_display}\n"
            for idx, item in enumerate(news.items[:5], 1):
                result_text += f"{idx}. {item.title}"
                if item.category:
                    result_text += f" `[{item.category}]`"
                result_text += "\n"
            if len(news.items) > 5:
                result_text += f"... 还有 {len(news.items) - 5} 条新闻\n"
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
            return datetime.now().strftime('%Y%m%d')
        elif date_str == "yesterday":
            return (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

        if re.match(r'^\d{8}$', date_str):
            return date_str

        match = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', date_str)
        if match:
            return f"{match.group(1)}{match.group(2)}{match.group(3)}"

        match = re.match(r'^(\d{4})/(\d{2})/(\d{2})$', date_str)
        if match:
            return f"{match.group(1)}{match.group(2)}{match.group(3)}"

        return None

    def _extract_context(self, content: str, keyword: str, context_length: int = 50) -> str:
        """提取关键词所在的上下文"""
        content_lower = content.lower()
        keyword_lower = keyword.lower()

        pos = content_lower.find(keyword_lower)
        if pos == -1:
            return content[:100] + "..." if len(content) > 100 else content

        start = max(0, pos - context_length)
        end = min(len(content), pos + len(keyword) + context_length)

        context = content[start:end]

        if start > 0:
            context = "..." + context
        if end < len(content):
            context = context + "..."

        return context
