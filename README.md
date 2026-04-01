# AstrBot 新闻联播查询插件

基于 [xin-wen-lian-bo](https://github.com/DuckBurnIncense/xin-wen-lian-bo) 数据源的 AstrBot 插件。

功能：查询新闻联播内容，并使用 AI 进行智能总结和分析。

## 功能特性

- **日期查询**: 查询指定日期的新闻联播内容
- **AI 智能总结**: 使用 AI 对新闻进行简要总结、详细分析或分类统计
- **关键词搜索**: 搜索包含特定关键词的新闻
- **近期概览**: 快速查看最近几天的新闻概要
- **自动分类**: 自动识别新闻类别（时政、经济、科技、社会、国际等）
- **本地缓存**: 智能缓存机制，减少网络请求

## 安装方法

1. 确保 AstrBot 版本 >= v4.5.7

2. 确保已安装依赖:
   ```bash
   pip install aiohttp aiofiles
   ```

3. 将本插件文件夹复制到 AstrBot 的 `plugins` 目录

4. 重启 AstrBot 或重新加载插件

5. 测试命令：`/xinwen-help`

## 使用方法

### 查询指定日期的新闻

```
/xinwen                    # 查询今天的新闻
/xinwen yesterday          # 查询昨天的新闻
/xinwen 20260330          # 查询指定日期
/xinwen 2026-03-30        # 支持多种日期格式
```

### AI 智能总结

```
/xinwen-summary                    # 简要总结今天的新闻
/xinwen-summary today brief       # 简要总结（默认）
/xinwen-summary today detailed    # 详细分析
/xinwen-summary today category    # 分类统计
```

**总结风格说明：**
- `brief` - 简要总结：提炼 3-5 条主要要点
- `detailed` - 详细分析：分领域深度分析（时政、经济、社会、国际等）
- `category` - 分类统计：按类别分组统计新闻数量

### 搜索新闻

```
/xinwen-search 经济        # 搜索包含"经济"的新闻
/xinwen-search 科技        # 搜索包含"科技"的新闻
```

### 查看近期新闻

```
/xinwen-latest             # 查看最近 3 天的新闻
/xinwen-latest 5           # 查看最近 5 天的新闻
```

## 命令列表

| 命令 | 说明 | 示例 |
|------|------|------|
| `/xinwen [日期]` | 查询指定日期的新闻 | `/xinwen`, `/xinwen 20260330` |
| `/xinwen-summary [日期] [style]` | AI 总结新闻 | `/xinwen-summary today detailed` |
| `/xinwen-search <关键词>` | 搜索新闻内容 | `/xinwen-search 经济` |
| `/xinwen-latest [天数]` | 查看最近几天新闻 | `/xinwen-latest 5` |
| `/xinwen-help` | 显示帮助信息 | `/xinwen-help` |

## 技术实现

### 数据来源
- 原始数据: https://github.com/DuckBurnIncense/xin-wen-lian-bo
- 数据格式: Markdown
- 更新频率: 每日更新

### 缓存机制
- 本地文件缓存，减少网络请求
- 缓存有效期：1 小时
- 日期列表缓存：24 小时

## 调试方法

### 测试 LLM 调用

```bash
cd xinwen_lianbo
python test_llm.py
```

### 查看日志

```bash
tail -f logs/astrbot.log
```

### 启用调试模式

在 `main.py` 中添加:
```python
logger.debug(f"Provider ID: {provider_id}")
logger.debug(f"Prompt: {prompt[:100]}...")
```

## 注意事项

1. **版本要求**: AstrBot >= v4.5.7
2. **网络依赖**: 首次查询需要从 GitHub 下载数据
3. **数据范围**: 数据从 2023 年开始
4. **LLM 配置**: 需要配置 LLM 才能使用总结功能(Dp 等国内模型不能总结)

## 许可证

MIT License
