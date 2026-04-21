---
name: sentiment-monitor
description: >
  基于LLM的品牌负面信息早期发现与隐匿风险深挖系统。
  核心能力：早期发现 + 隐匿发现 + 风险深挖 + 框架升级检测。
  方法论驱动：Agent自主思考搜什么、何时停，不依赖硬编码规则。
---

# 品牌舆情监控 Skill

## 核心定位

**目标**：尽可能早地发现负面信息，挖掘常规搜索找不到的隐匿风险信号。
**不是做一份漂亮的报告，而是找到别人找不到的负面。**

## 架构

```
Agent（分析师）                      脚本（工具）
+-------------------+            +------------------+
| 读结果 → 思考     | --query--> | 搜索 → 存raw/    |
| 发现 → 设计新query| <--结果-- | 零业务逻辑       |
| 判断何时停        |            +------------------+
+-------------------+
```

**Agent = 大脑（决定搜什么、分析什么、何时停）。脚本 = 手（搜索+存文件）。**
Agent 不直接调用 web_search / web_fetch / 百度工具。所有数据收集通过脚本完成。

---

## 执行流程

### Phase 0: 初始化

```bash
# 百科查询（建立品牌基础画像）
python3 scripts/sentiment-collect.py "品牌名" --baike

# 初始泛化搜索
python3 scripts/sentiment-collect.py "品牌名" --round 0 \
  --query "品牌名" "品牌名 新闻" "品牌名 评价"
```

读结果 → 提取初始种子实体 → 创建 `status.json`

### 主循环：搜索→分析→思考→扩散

反复执行以下循环，直到判断收敛：

```
① 基于当前种子池和上轮发现，思考本轮应该搜什么方向
   （参考 references/methodology.md 的迭代思维模型）

② 设计Query并执行搜索：
   python3 scripts/sentiment-collect.py "品牌" --round N --query "q1" "q2" "q3"

③ 读搜索结果，逐条分析：
   - 提取新实体 → 加入种子池
   - 识别情感信号和风险事件
   - 对高相关结果抓全文：--fetch-url "URL"
   - **特别注意**：同一事件是否以新的更危险的叙事框架出现？

④ 如果发现了L2+风险事件或隐匿信号，围绕它展开深挖：
   - 风险深挖：references/risk-tracking.md（五步法）
   - 隐匿发现：references/hidden-risk-discovery.md（七大思考透镜）
   - 二阶传播：用事件指纹（不含品牌名）搜索脱品牌名的二次传播

⑤ 更新 status.json

⑥ 判断是否收敛（参考 methodology.md §一.1.3 收敛原则）
```

**关键**：这不是"完成N个步骤就进入下一轮"的打钩流程。
这是一个连续的思考过程。每轮的搜索方向、深度、侧重点都应该基于上一轮的分析结果自主决定。

### 写报告 & 转PDF

- 按 `templates/report-template.md` 的8章结构写报告
- 信源带URL，技术支持固定写"赛迪网"，不出现搜索工具名
- 第六章6.4隐匿信源数据来自 `hidden_risks.json`
- 报告写完后立即转PDF：
  ```bash
  # 方法A（推荐）：内置脚本
  python3 scripts/md2pdf.py report_v1.3.md report.pdf
  # 方法B（备用）：见 scripts/md2pdf.py 内的Chrome方案
  ```

---

## 核心参考文件（按需阅读）

| 文件 | 什么时候读 | 核心内容 |
|------|-----------|---------|
| `references/methodology.md` | **主循环开始前必读** | 迭代思维模型、种子池演化、Query设计哲学、收敛原则 |
| `references/hidden-risk-discovery.md` | 发现L2+事件后 | 七大隐匿性思考透镜（R1-R7），启发式而非清单式 |
| `references/risk-tracking.md` | 需要深挖L2+事件时 | 五步法纵深挖掘 |
| `references/early-detection.md` | 每轮常规搜索时 | 早期发现四层漏斗 |
| `references/report-writing-guide.md` | 写报告时 | 8章写作规范+自检清单 |
| `templates/report-template.md` | 写报告时 | 唯一的格式基准 |
| `references/examples/saidi-leakage-case.md` | 遇到类似场景时 | 真实漏报案例，从错误中学习 |

---

## 硬性禁令

| # | ❌ 禁止 | ✅ 正确做法 |
|---|--------|-----------|
| 1 | 自己调web_search/web_fetch/百度工具收集数据 | 全部通过 sentiment-collect.py 脚本 |
| 2 | 出现任何搜索工具名称 | 只写媒体/网站名称 |
| 3 | 技术支持写其他内容 | 固定写：赛迪网 |
| 4 | 自创模板外章节 | 只写template中的8章 |
| 5 | 不生成status.json / hidden_risks.json | 三个沉淀文件缺一不可 |
| 6 | 编造URL | 找不到就写"URL缺失: 原因说明" |
| 7 | 将"同一事件+新框架"误判为重复信息 | 识别为框架升级信号，独立分析 |
| 8 | 只看snippet就对高相关结果下结论 | 必须抓全文再判断 |
| 9 | 机械式执行固定Query清单而不思考 | 基于分析结果自主设计每轮搜索方向 |

---

## 数据沉淀

| 文件 | 内容 | 创建时机 |
|------|------|---------|
| `raw/*.txt` | 每次搜索原始结果 | 脚本自动写入 |
| `status.json` | 迭代状态中枢（种子池、风险事件、轮次等） | Phase 0创建，每轮更新 |
| `hidden_risks.json` | 隐匿性风险信号表 | 首次隐匿发现时创建，之后追加 |

---

## 文件导航

```
sentiment-monitor/
├── SKILL.md                          ← 本文件（执行入口）
├── scripts/
│   ├── sentiment-collect.py          ← 数据采集脚本（唯一搜索入口）
│   └── md2pdf.py                     ← MD转PDF
├── templates/
│   ├── report-template.md            ← 8章报告模板
│   └── status-template.json          ← status.json填空模板
└── references/
    ├── methodology.md                ← ★ 核心方法论（必读）
    ├── hidden-risk-discovery.md      ← 隐匿发现思考透镜
    ├── risk-tracking.md              ← 风险深挖五步法
    ├── early-detection.md            ← 早期发现四层漏斗
    ├── report-writing-guide.md       ← 写作规范+自检
    ├── analyst-identity.md           ← 分析师身份设定
    ├── output-specs.md               ← 输出格式规范
    └── examples/
        └── saidi-leakage-case.md     ← 漏报案例研究（从错误中学习）
```

---

## 版本记录

| 版本 | 变化 |
|------|------|
| v1.0-v2.2 | 初版 → 引入采集脚本 → 防覆盖机制 |
| v2.3-v2.5 | 加入Step 3E二阶追踪/R6扩展到9组/PDF稳定化（打补丁式改进） |
| **v3.0** | **彻底重构为方法论驱动。删除所有硬编码Query模板/强制执行清单/内联CSS。SKILL.md从336行精简至~120行。新增methodology.md核心思维模型和examples/案例库。Agent从操作工变为分析师。** |
