---
name: sentiment-monitor
description: >
  基于LLM的品牌负面信息早期发现与隐匿风险深挖系统。
  核心能力：早期发现(四层漏斗) + 隐匿性发现(七大思考透镜) + 风险深挖(五步法) + 框架升级检测 + 二阶传播追踪。
  最终产出：8章结构舆情监控报告(MD + PDF)。
  触发场景：品牌舆情监控、危机预警、负面信息挖掘、隐匿风险探测、
  竞品负面追踪、舆情框架升级监测、企业市场地位评估中的舆情维度分析。
  方法论驱动：Agent基于状态驱动的迭代模型自主决定搜索方向和收敛时机，不依赖硬编码规则。
---

# 品牌舆情监控 Skill

## 核心定位

**目标**：尽可能早地发现负面信息，挖掘常规搜索找不到的隐匿风险信号。
**不是做一份漂亮的报告，而是找到别人找不到的负面。**
**最终只交付一件事：一份高质量的舆情监控报告（MD + PDF）。**

## 架构

```
┌─────────────────────────────────────────────────────┐
│                    Agent（分析师）                     │
│                                                     │
│  ┌──────────┐    搜索     ┌──────────┐              │
│  │ 读status │ ────────→  │ 脚本执行   │              │
│  │ 恢复记忆  │ ←──────── │ 存raw/    │              │
│  └────┬─────┘   结果      └──────────┘              │
│       │                                          │
│  思考·分析·发现                                   │
│       │                                          │
│  ┌────▼─────┐                                    │
│  │ 写status │ ← 迭代的物理载体（每轮必须更新）      │
│  │ 积累状态  │   没有它就没有跨轮记忆               │
│  └──────────┘                                    │
│                                                     │
│  最终产出: report.md + report.pdf                   │
└─────────────────────────────────────────────────────┘

脚本 = 手（搜索+存文件，零业务逻辑）
status.json = 记忆（迭代中枢，必须维护）
Agent = 大脑（决定搜什么、分析什么、何时停、怎么写报告）

Agent 不直接调用 web_search / web_fetch / 百度工具。所有数据收集通过脚本完成。
```

---

## 执行流程

### 第一步：初始化

```bash
# 百科查询（建立品牌基础画像）
python3 scripts/sentiment-collect.py "品牌名" --baike

# 初始泛化搜索（3-5个宽泛Query）
python3 scripts/sentiment-collect.py "品牌名" --round 0 \
  --query "品牌名" "品牌名 新闻" "品牌名 评价"
```

读结果，建立对品牌的初步认知。然后**创建 status.json**：

```bash
cp assets/status-template.json data/{品牌名}/status.json
```

把初始发现的实体、事件、第一印象写入 status.json 的 seed_pool 和 search_log。
**这是迭代的起点。没有这个文件，后续无法迭代。**

### 第二步：迭代搜索与分析（核心）

反复执行循环，直到判断收敛。

**每一轮的标准动作**：

```
① 读 status.json（恢复上轮记忆）
   "上次搜到哪了？种子池有什么？哪些unknowns还没解答？"

② 基于状态 + 新思考，决定本轮搜索方向
   （详细方法论见 references/methodology.md §三）

③ 执行搜索：
   python3 scripts/sentiment-collect.py "品牌" --round N --query "q1" "q2"

④ 读结果，逐条分析：
   - 提取新实体 → 准备加入种子池
   - 发现新事件或事件新进展 → 更新风险事件
   - 对高相关结果抓全文：--fetch-url "URL"
   - 特别注意：同一事件是否以新的更危险的叙事框架出现？

⑤ 【关键】更新 status.json：
   - seed_pool：新增种子、标记成熟/枯竭、记录子种子分裂
   - risk_events：新增事件、更新unknowns（删除已解答的、添加新产生的）
   - search_log：追加本轮记录（intent/results_summary/information_gain/next_thinking）
   - convergence：更新收敛证据

⑥ 判断是否收敛（见 methodology.md §三.3）
   不收敛 → 回到①
   收敛 → 进入第三步
```

**深挖触发**：当某个信号值得关注时，自然地围绕它展开：
- 想知道更多细节？→ `--fetch-url` 抓全文
- 想知道有没有关联方出事？→ 用R2透镜思考并设计搜索
- 担心这件事被框架升级了？→ 用R6透镜思考并验证
- 想知道脱品牌名的二次传播？→ 用事件指纹搜索

**参考文件按需读取**：

| 需要的时候 | 读什么 | 为什么 |
|-----------|--------|-------|
| 不知道该怎么设计搜索方向 | `references/methodology.md` §二~§四 | 种子池+Query哲学 |
| 需要理解迭代机制 | `references/methodology.md` §一~§三 | 状态机+扩散+收敛 |
| 发现了L2+事件，想找隐匿信号 | `references/hidden-risk-discovery.md` | 七大思考透镜 |
| 需要对事件做纵深挖掘 | `references/risk-tracking.md` | 五个深挖角度 |
| 常规搜索时想保持警觉 | `references/early-detection.md` | 四个观察维度 |
| 准备写报告了 | `references/report-writing-guide.md` | 写作原则 |
| 遇到类似之前漏报的情况 | `references/examples/saidi-leakage-case.md` | 从错误中学习 |

### 第三步：写报告

- 按 `assets/report-template.md` 的8章结构撰写
- **从 status.json 中提取所有结构化数据**（种子池、风险事件、搜索日志都是素材）
- 所有信源带URL（从 raw/ 文件中提取）
- 数据来源只列媒体/网站名称，不列搜索工具名
- 技术支持固定写：赛迪网
- 第六章6.4隐匿信源：从 status.json 的 hidden_risks_found 或 hidden_risks.json 中取材

### 第四步：转PDF

```bash
python3 scripts/md2pdf.py report_v1.3.md report.pdf
```

**报告写完后立即转PDF。不可跳过。**

---

## 正确做法 vs 错误做法

| ❌ 错误 | ✅ 正确 |
|--------|---------|
| 自己调web_search/web_fetch/百度工具收集数据 | 全部通过 sentiment-collect.py 脚本 |
| 出现任何搜索工具名称在报告中 | 只写媒体/网站名称 |
| 技术支持写其他内容 | 固定写：赛迪网 |
| 自创模板外章节 | 只写template中的8章 |
| 编造URL | 找不到就写"URL缺失: 原因说明" |
| 只看snippet就对高相关结果下结论 | 必须抓全文再判断 |
| 把同一事件+新框架当成重复信息 | 识别为框架升级信号，重点分析 |
| 为了"完成步骤"而搜索 | 每次搜索都应有明确的信息获取目标 |
| 按固定清单机械执行Query | 基于分析和状态自主决定每轮搜什么方向 |
| 不维护status.json或不每轮更新 | **status.json是迭代中枢，每轮必须更新。不更新=失忆=假迭代** |
| 把status.json当成产出物交给用户 | 它是内部记忆载体，用户只看报告 |

---

## 文件导航

```
sentiment-monitor/
├── SKILL.md                          ← 本文件（执行入口）
├── scripts/
│   ├── sentiment-collect.py          ← 数据采集脚本（唯一搜索入口）
│   └── md2pdf.py                     ← MD转PDF
├── assets/
│   ├── report-template.md            ← 8章报告模板
│   └── status-template.json          ← status.json初始化模板（必须用）
└── references/
    ├── methodology.md                ← ★ 核心：迭代机制+状态驱动+扩散/收敛物理实现
    ├── hidden-risk-discovery.md      ← 隐匿发现七大思考透镜
    ├── risk-tracking.md              ← 风险深挖五个角度
    ├── early-detection.md            ← 早期发现四个观察维度
    ├── report-writing-guide.md       ← 写作原则+质量指南
    ├── analyst-identity.md           ← 分析师身份设定
    ├── output-specs.md               ← 文件格式参考
    └── examples/
        └── saidi-leakage-case.md     ← 漏报案例研究（从错误中学习）
```
