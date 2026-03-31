# AstrBot 新闻联播查询插件

基于 [xin-wen-lian-bo](https://github.com/DuckBurnIncense/xin-wen-lian-bo) 数据源的 AstrBot 插件。

功能：查询新闻联播内容，并使用AI进行智能总结和分析。

## 功能特性

- **日期查询**: 查询指定日期的新闻联播内容
- **AI智能总结**: 使用AI对新闻进行简要总结、详细分析或分类统计
- **关键词搜索**: 搜索包含特定关键词的新闻
- **近期概览**: 快速查看最近几天的新闻概要
- **自动分类**: 自动识别新闻类别（时政、经济、科技、社会、国际等）
- **本地缓存**: 智能缓存机制，减少网络请求

## 安装方法

1. 确保 AstrBot 已安装 `aiohttp` 和 `aiofiles`:
   ```bash
   pip install aiohttp aiofiles
   ```

2. 将本插件文件夹复制到 AstrBot 的 `plugins` 目录

3. 重启 AstrBot 或重新加载插件

4. 插件将自动注册相关命令

## 使用方法

### 查询指定日期的新闻

```
/xinwen                    # 查询今天的新闻
/xinwen yesterday          # 查询昨天的新闻
/xinwen 20260330          # 查询指定日期
/xinwen 2026-03-30        # 支持多种日期格式
```

### AI智能总结

```
/xinwen-summary                    # 简要总结今天的新闻
/xinwen-summary today brief       # 简要总结（默认）
/xinwen-summary today detailed    # 详细分析
/xinwen-summary today category    # 分类统计
/xinwen-summary 20260330 detailed # 总结指定日期
```

**总结风格说明：**
- `brief` - 简要总结：提炼3-5条主要要点
- `detailed` - 详细分析：分领域深度分析（时政、经济、社会、国际等）
- `category` - 分类统计：按类别分组统计新闻数量

### 搜索新闻

```
/xinwen-search 经济        # 搜索包含"经济"的新闻
/xinwen-search 习近平      # 搜索包含"习近平"的新闻
/xinwen-search 科技        # 搜索包含"科技"的新闻
```

### 查看近期新闻

```
/xinwen-latest             # 查看最近3天的新闻
/xinwen-latest 5           # 查看最近5天的新闻
/xinwen-latest 7           # 查看最近7天的新闻
```

### 帮助信息

```
/xinwen-help               # 显示帮助信息
```

## 命令列表

| 命令 | 说明 | 示例 |
|------|------|------|
| `/xinwen [日期]` | 查询指定日期的新闻 | `/xinwen`, `/xinwen 20260330` |
| `/xinwen-summary [日期] [style]` | AI总结新闻 | `/xinwen-summary today detailed` |
| `/xinwen-search <关键词>` | 搜索新闻内容 | `/xinwen-search 经济` |
| `/xinwen-latest [天数]` | 查看最近几天新闻 | `/xinwen-latest 5` |
| `/xinwen-help` | 显示帮助信息 | `/xinwen-help` |

## 日期格式支持

- `today` - 今天（默认）
- `yesterday` - 昨天
- `YYYYMMDD` - 如 20260330
- `YYYY-MM-DD` - 如 2026-03-30
- `YYYY/MM/DD` - 如 2026/03/30

## 新闻分类

插件会自动识别以下类别：

| 类别 | 关键词 |
|------|--------|
| 时政 | 习近平、总书记、主席、总理、人大、政协 |
| 经济 | 经济、发展、增长、GDP、产业、市场、金融 |
| 科技 | 科技、创新、技术、研发、人工智能、航天 |
| 社会 | 民生、就业、教育、医疗、社保、住房 |
| 国际 | 国际、外交、访问、合作、联合国 |
| 军事 | 军队、国防、军事、演习、装备 |
| 农业 | 农业、农村、粮食、丰收、乡村振兴 |
| 生态 | 生态、环保、绿色、气候、碳中和 |
| 法律 | 法治、法律、司法、法院、立法 |
| 综合 | 其他新闻 |

## 文件结构

```
xinwen_lianbo/
├── __init__.py            # 插件入口
├── main.py                # 主插件代码
├── README.md              # 本文件
├── data/                  # 数据目录
└── cache/                 # 缓存目录
    ├── available_dates.json
    └── 20260330.md
```

## 技术实现

### 数据来源
- 原始数据: https://github.com/DuckBurnIncense/xin-wen-lian-bo
- 数据格式: Markdown
- 更新频率: 每日更新

### 缓存机制
- 本地文件缓存，减少网络请求
- 缓存有效期：1小时
- 日期列表缓存：24小时

### AI总结
- 调用 AstrBot 配置的 LLM 提供商
- 支持多种总结风格
- 自动构建结构化提示词

## 注意事项

1. **网络依赖**: 首次查询需要从 GitHub 下载数据
2. **数据范围**: 数据从2023年开始，部分早期日期可能没有数据
3. **AI总结**: 需要配置 LLM 提供商才能使用总结功能
4. **搜索范围**: 搜索功能默认搜索最近30天的新闻

## 数据来源

- 项目: https://github.com/DuckBurnIncense/xin-wen-lian-bo
- 原始来源: https://tv.cctv.com/ (央视网)

## 许可证

MIT License
