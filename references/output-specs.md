# 过程辅助文件参考

> **这些文件都是Agent思考过程中的辅助工具，不是最终产出。**
> **唯一产出是 report_v1.3.md + report.pdf。**
> **你可以用这些文件来整理思路，也可以不用——按你的工作习惯决定。**

---

## data/{品牌名}/ 目录结构

```
data/{品牌名}/
├── raw/                           # 原始搜索数据（脚本自动写入）
│   └── *.txt                      # 每次搜索一个文件
├── status.json                    # [可选] 你的思考笔记本
├── hidden_risks.json             # [可选] 隐匿发现草稿
├── report_v1.3.md                # ★ 最终报告
└── report_v1.3.pdf               # ★ 最终报告PDF
```

---

## status.json — 思考笔记本 [可选]

用途：帮你记住搜索到哪了、发现了什么、下一步想搜什么。

**不需要严格遵循任何schema**。如果你觉得有用，可以用 `assets/status-template.json` 作为起点自由增删字段。

如果你更习惯在写报告前直接回顾raw/文件和自己的分析记忆，那完全可以不创建这个文件。

### 参考结构（不是强制的）

```json
{
  "brand": "品牌名",
  "current_round": 3,
  "seed_pool": {
    "seeds": [
      {"type": "event", "value": "某事件", "note": "..."},
      {"type": "person", "value": "某人名", "note": "..."}
    ]
  },
  "risk_events": [
    {"id": "RE-1", "title": "事件标题", "level": "L2/L3", "status": "tracking/resolved"}
  ],
  "notes": "自由记录任何你觉得有用的思考..."
}
```

---

## hidden_risks.json — 隐匿发现草稿 [可选]

用途：写报告时，帮你回忆分析过程中发现的隐匿信号，方便填入第六章6.4节。

**同样不是强制的**。如果你在分析过程中已经对隐匿发现有了清晰印象，可以直接写报告。

### 参考格式

```json
[
  {
    "id": "HR-1",
    "signal": "一句话概括",
    "source": "来源平台",
    "url": "真实URL 或 URL缺失: 原因",
    "strategy": "用了哪个思考透镜(R1-R7)",
    "related_event": "关联的风险事件",
    "strength": "强/中强/中/弱",
    "concealment_level": "L1-L5",
    "explanation": "为什么相关"
  }
]
```

---

## raw/ 文件说明

raw/ 中的文件由 `sentiment-collect.py` 脚本自动创建和管理。
你只需要知道怎么读它们（搜索结果都在里面），不需要关心命名规则。

*重写说明：v3.0将"产出物规范"改为"过程辅助文件参考"。status.json和hidden_risks.json从强制产出降级为可选工具。*
