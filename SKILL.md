---
name: sentiment-monitor
description: >
  基于LLM的品牌负面信息早期发现与隐匿风险深挖系统。
  核心能力：早期发现(四层漏斗) + 隐匿性发现(七大思考透镜) + 风险深挖(五步法) + 框架升级检测 + 二阶传播追踪。
  最终产出：8章结构舆情监控报告(MD + PDF)。
  触发场景：品牌舆情监控、危机预警、负面信息挖掘、隐匿风险探测、
  竞品负面追踪、舆情框架升级监测、企业市场地位评估中的舆情维度分析。
  方法论驱动：Agent基于迭代思维模型自主决定搜索方向和收敛时机，不依赖硬编码规则。
---

# 品牌舆情监控 Skill

## 核心定位

**目标**：尽可能早地发现负面信息，挖掘常规搜索找不到的隐匿风险信号。
**不是做一份漂亮的报告，而是找到别人找不到的负面。**
**最终只交付一件事：一份高质量的舆情监控报告（MD + PDF）。**

## 架构

```
Agent（分析师）                      脚本（工具）
+-------------------+            +------------------+
| 读结果 → 思考     | --query--> | 搜索 → 存raw/    |
| 发现 → 设计新query| <--结果-- | 零业务逻辑       |
| 判断何时停        |            +------------------+
+-------------------+

唯一产出：report_v1.3.md + report.pdf
其余文件(raw/status/json)均为思考过程的中间产物，随用随弃
```

**Agent = 大脑（决定搜什么、分析什么、何时停、怎么写报告）。**
**脚本 = 手（搜索+存文件，零业务逻辑）。**
Agent 不直接调用 web_search / web_fetch / 百度工具。所有数据收集通过脚本完成。

---

## 执行流程

### 第一步：初始化了解品牌

```bash
# 百科查询（建立品牌基础画像）
python3 scripts/sentiment-collect.py "品牌名" --baike

# 初始泛化搜索（3-5个宽泛Query）
python3 scripts/sentiment-collect.py "品牌名" --round 0 \
  --query "品牌名" "品牌名 新闻" "品牌名 评价"
```

读结果，建立对品牌的初步认知：
- 这个品牌是谁？做什么的？谁在管？
- 目前能看到什么？（正面/中性/负面）
- 有没有一眼就能识别的风险信号？

可以用 `assets/status-template.json` 作为初始记录模板（也可以不用——这只是帮你整理思路的工具）。

### 第二步：迭代搜索与分析（核心）

反复执行「搜索→阅读→思考→再搜索」循环，直到判断没有更多值得挖掘的内容。

**每次循环的思考方式**（详细方法论见 `references/methodology.md`）：

1. **我目前知道什么？** — 回顾已发现的实体、事件、信号
2. **这意味着什么？** — 判断严重程度、叙事框架、潜在关联
3. **我还不知道什么？** — 识别盲区：哪些角度没覆盖？哪些信源没触达？
4. **我怎么去发现？** — 设计能回答③的问题的搜索词
5. **执行搜索，读结果，回到①**

**深挖触发**：当某个信号值得关注时，自然地围绕它展开：
- 想知道更多细节？→ `--fetch-url` 抓全文
- 想知道有没有关联方出事？→ 用R2透镜思考并设计搜索
- 担心这件事被框架升级了？→ 用R6透镜思考并验证
- 想知道脱品牌名的二次传播？→ 用事件指纹搜索

**参考文件按需读取**（不要预先全部读完）：

| 需要的时候 | 读什么 | 为什么 |
|-----------|--------|-------|
| 不知道该怎么设计搜索方向 | `references/methodology.md` §一~§二 | 迭代模型+种子池演化 |
| 发现了L2+事件，想找隐匿信号 | `references/hidden-risk-discovery.md` | 七大思考透镜 |
| 需要对事件做纵深挖掘 | `references/risk-tracking.md` | 五步法 |
| 常规搜索时想系统覆盖 | `references/early-detection.md` | 四层漏斗 |
| 准备写报告了 | `references/report-writing-guide.md` | 8章写作规范 |
| 遇到类似之前漏报的情况 | `references/examples/saidi-leakage-case.md` | 从错误中学习 |

### 第三步：写报告

- 按 `assets/report-template.md` 的8章结构撰写
- 所有信源带URL（从 raw/ 文件中提取）
- 数据来源只列媒体/网站名称，不列搜索工具名
- 技术支持固定写：赛迪网
- 第六章6.4隐匿信源：基于你在分析过程中发现的隐匿信号整理填写（如果你用了hidden_risks.json做笔记，可以从中取材；如果没用，直接根据记忆和分析写）

### 第四步：转PDF

```bash
# 方法A（推荐）
python3 scripts/md2pdf.py report_v1.3.md report.pdf

# 方法B（备用）：Chrome headless方案，见 md2pdf.py 内注释
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
| 把status.json/hidden_risks.json当成产出物 | 它们是思考用的草稿纸，唯一产出是报告 |
| 按固定清单机械执行Query | 基于分析自主决定每轮搜什么方向 |

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
│   └── status-template.json          ← 可选的状态记录模板（非强制）
└── references/
    ├── methodology.md                ← ★ 核心方法论（迭代思维模型）
    ├── hidden-risk-discovery.md      ← 隐匿发现七大思考透镜
    ├── risk-tracking.md              ← 风险深挖五步法
    ├── early-detection.md            ← 早期发现四层漏斗
    ├── report-writing-guide.md       ← 写作规范+自检清单
    ├── analyst-identity.md           ← 分析师身份设定
    ├── output-specs.md               ← 输出格式规范
    └── examples/
        └── saidi-leakage-case.md     ← 漏报案例研究（从错误中学习）
```
