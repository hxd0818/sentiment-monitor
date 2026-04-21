# Sentiment Monitor — 品牌舆情监控 Skill

> 基于 OpenProbe（company-chain-investigate v9.5）架构和方法论构建的**品牌舆情监控与情感分析系统**。

## 能力概述

Sentiment Monitor 是一个 Agent 驱动的 OSINT 舆情分析工具，通过螺旋迭代式搜索和 LLM 情感分析，对品牌/企业进行全面舆情画像：

| 维度 | 核心输出 |
|------|---------|
| D1 情感主题分布 | 用户讨论的话题分类 + 各话题情感倾向 + 热度排序 |
| D2 情绪驱动因子 | 触发正/负面情绪的关键因素归因分析 |
| D3 风险事件追踪 | 负面事件清单 + 影响评估 + 危机等级判定 |
| D4 影响力图谱 | KOL/媒体/意见领袖识别 + 态度图谱 + 传播路径 |
| D5 渠道热度映射 | 各平台讨论热度 + 情感特征 + 渠道策略建议 |
| D6 竞品情感对比 | vs竞品的情感差异 + 竞争优劣势洞察 |

## 与 OpenProbe 的关系

```
OpenProbe (v9.5)                    Sentiment Monitor (v1.0)
┌─────────────────┐                ┌──────────────────────┐
│ 企业调查         │   方法论复用    │ 舆情监控              │
│ ·竞争对手       │ ────────→      │ ·情感主题分布 (D1)    │
│ ·产业链         │  螺旋迭代       │ ·情绪驱动因子 (D2)    │
│ ·资本关系       │  PIR驱动收敛    │ ·风险事件追踪 (D3)    │
│ ·关键人物       │  种子扩散       │ ·影响力图谱 (D4)      │
│                 │  质量门禁       │ ·渠道热度映射 (D5)    │
│                 │  实体分层       │ ·竞品情感对比 (D6)    │
└─────────────────┘                └──────────────────────┘
```

**完全复用**：
- ✅ 螺旋迭代状态机（Phase 0 → Phase N 十步法）
- ✅ status.json 唯一状态真相源
- ✅ PIR 四层结构（Layer 0-3）
- ✅ 数据质量门禁（时效分级+推算规范）
- ✅ Query 设计铁律（≤5词/单问题/时间锚定）
- ✅ 实体分层策略（Tier 1/2/3）
- ✅ 收敛判断机制
- ✅ 报告撰写标准与自检清单

**领域适配**：
- 🔄 维度从"企业调查四维"重构为"舆情监控六维"
- 🔄 PIR 模板从"企业情报需求"重构为"舆情情报需求"
- 🔄 分析师身份从"产业研究员"切换为"舆情分析师"
- 🔄 新增 `--social` 社交媒体专项搜索模式
- 🔄 新增信源分级体系（权威媒体/一般媒体/社交平台/用户生成内容）
- 🔄 输出报告从"竞争格局报告"重构为"舆情分析报告"

## 快速开始

```bash
# 对品牌"名创优品"进行舆情监控
python3 scripts/collect-v1.py "名创优品" --baike
python3 scripts/collect-v1.py "名创优品" --query "口碑 评价" "差评 投诉" "最新 动态"
python3 scripts/collect-v1.py "名创优品" --social "小红书 评价" "微博 吐槽"
python3 scripts/collect-v1.py "名创优品" --pdf
```

## 输出物

```
data/{品牌名}/
├── status.json              # 迭代状态中枢
├── raw/                     # 原始搜索数据
│   ├── s01.txt ~ sNN.txt    # 搜索结果
│   ├── baike.txt            # 百科结果
│   └── social_01.txt        # 社交媒体搜索结果
├── sentiment_profile.json   # 品牌情感画像
├── topic_model.json         # 主题模型结果
├── risk_events.json         # 风险事件清单
├── influence_graph.json     # 影响力图谱
├── channel_heatmap.json     # 渠道热度数据
├── competitor_sentiment.json# 竞品对比数据
├── report_v1.md             # Markdown 舆情报告
└── report.pdf               # PDF 报告
```

## 版本

- **v1.0** (2026-04-20) — 初始版本，基于 OpenProbe v9.5 架构
