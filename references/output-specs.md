# 产出物格式规范 v2.1

> **只保留实际需要的产出物定义。**

---

## 目录结构

```
data/{品牌名}/
├── raw/                           # 原始搜索数据（每次搜索存一个文件）
│   ├── q_01_{关键词}.txt
│   ├── q_02_{关键词}.txt
│   ├── q03_L0_{关键词}.txt       # Layer 0 嗅探的搜索结果
│   └── ...
├── status.json                    # 迭代状态中枢（必须创建）
├── hidden_risks.json             # 隐匿性风险信号表（发现隐匿信号时才创建）
├── report_v1.3.md                # 最终报告（按模板8章结构）
└── report_v1.3.pdf               # 最终报告PDF
```

## status.json 最小Schema（复制 templates/status-template.json 后填空）

必须包含的字段：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| brand | string | 品牌名 | "赛迪顾问" |
| phase | string | 阶段 | "completed" |
| current_round | integer | 当前轮次（必须>=6才能收敛） | 7 |
| total_searches | integer | 总搜索次数 | 15 |
| seeds | array | 种子列表，每项含type/value/sentiment_hint | 见下方示例 |
| sentiment_snapshot | object | 含positive_ratio/neutral_ratio/negative_ratio/data_points | 见下方示例 |
| risk_events | array | 风险事件列表，每项含id/title/level/status | 见下方示例 |
| convergence_reason | string | 收敛原因说明 | "round=7, 连续2轮无新信号" |
| timestamps | object | 含started_at/completed_at/duration_minutes | 见下方示例 |

**seeds数组元素格式**：
```json
{"type": "event", "value": "百强县买榜事件", "sentiment_hint": "negative"}
```
type可选值: event / person / company / keyword / platform
sentiment_hint可选值: positive / negative / neutral / mixed

**sentiment_snapshot格式**：
```json
{
  "positive_ratio": 0.25,
  "neutral_ratio": 0.35,
  "negative_ratio": 0.40,
  "data_points": 38,
  "last_updated": "2026-04-20T23:00:00+08:00"
}
```

三个ratio之和应接近1.0。

## hidden_risks.json Schema（发现隐匿信号时才创建）

```json
[
  {
    "id": "HR-1",
    "signal": "信号摘要（一句话）",
    "source": "来源媒体或平台名称",
    "url": "真实URL或者写 URL缺失: [原因]",
    "strategy": "R1到R7中的一个",
    "related_event": "关联的风险事件ID或名称，如RE001",
    "strength": "强 或 中强 或 中 或 弱",
    "concealment_level": "L1 或 L2 或 L3 或 L4 或 L5",
    "explanation": "为什么这个信号与目标品牌相关（1-2句话）"
  }
]
```

## raw/ 文件命名规则

| 前缀含义 | 格式 | 示例 |
|---------|------|------|
| 第N轮常规搜索 | `q{N}_{关键词}.txt` | `q_03_赛迪顾问.txt` |
| Layer 0 嗅探 | `q{N}_L0_{关键词}.txt` | `q05_L0_负面定向.txt` |
| Layer 2 验证放大 | `q{N}_L2_{关键词}.txt` | `q06_L2_南京同构.txt` |
| 隐匿策略搜索 | `q{N}_R{策略号}_{关键词}.txt` | `q07_R2_关联实体.txt` |

每个raw文件的内容就是该次搜索返回的原始文本结果，不做加工。

*v2.1: 去除emoji；字段说明改为表格形式；URL处理规则明确化。*
