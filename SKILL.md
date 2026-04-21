---
name: sentiment-monitor
description: >
  基于LLM的品牌负面信息早期发现与隐匿风险深挖系统。
  核心能力：早期发现(四层漏斗) + 隐匿发现(七大策略) + 风险深挖。
  触发场景：品牌舆情监控、危机预警、负面信息挖掘、隐匿风险探测。
---

# 品牌舆情监控 Skill -- 负面早期发现 + 隐匿风险深挖

## 核心定位

本Skill的核心目标是：尽可能早地发现负面信息、挖掘常规搜索找不到的隐匿风险信号。
不是做一份漂亮的报告，而是找到别人找不到的负面。

## 架构（与OpenProbe相同模式）

```
Agent（你）                          脚本（dumb tool）
+-------------------+            +------------------+
| 决定策略 -> 设计query | --传入-->  | 搜索 -> 存raw/    |
| 读结果 -> 分析判断   | <--返回-- | 零业务逻辑       |
| 更新种子 -> 下一轮   |            +------------------+
|  ^__循环直到收敛___|
+-------------------+
```

**关键原则：Agent = 大脑（决定搜什么、何时停），脚本 = 手（搜索+存文件）**
Agent 不直接调用 web_search / web_fetch / 百度工具。所有数据收集通过脚本完成。

## 执行流程（必须严格遵守）

### Step 1: 读规范文件

按顺序读取以下文件：
1. `templates/report-template.md` -- 唯一格式基准（8章结构）
2. `references/report-writing-guide.md` -- 写作规范+自检清单
3. 记住以下固定值：技术支持=赛迪网 / 不出现搜索工具名 / 8章结构不变

### Step 2: Phase 0 -- 初始化采集

通过脚本执行初始搜索：

```bash
# 百科查询（建立品牌基础画像，只需一次）
python3 scripts/sentiment-collect.py "品牌名" --baike

# 泛化搜索（3-5个初始Query，round=0表示初始轮）
python3 scripts/sentiment-collect.py "品牌名" --round 0 --query "品牌名" "品牌名 新闻" "品牌名 评价"
```

脚本会自动将结果存入 `data/{品牌}/raw/` 目录。
文件名格式：`r0_q01.txt`, `r0_q02.txt`（轮次_序号.txt），不同轮次不会覆盖。

读 raw/ 中的结果后：
- 提取初始种子实体（人名/公司名/事件/关键词）
- 创建 status.json（复制 templates/status-template.json 后填空）

### Step 3: 主循环（>=3轮，每轮执行5个步骤）

**每轮必须依次执行以下5个步骤，不可跳过任何一个。**

#### Step 3A: 常规搜索（每轮必做）

```
(1) 读 status.json
(2) 设计本轮常规Query（基于种子池 + 上轮新发现 + 早期发现Layer0五行扫描）
(3) 通过脚本搜索：
    python3 scripts/sentiment-collect.py "品牌名" --round N --query "q1" "q2" "q3"
(4) 读 rN_*.txt 结果，提取新实体、识别情感信号、标记L2+事件
```

**早期发现 Layer0 五行Query（混入上述搜索中）**：
1. 品牌名精确："赛迪顾问"
2. 产品/服务关键词：（从种子池获取）
3. 高管名：（从种子池获取）
4. 行业/客户关键词：（从种子池获取）
5. 负面定向："赛迪顾问 造假/问题/通报/争议"

#### Step 3B: 风险深挖（每轮必做，有L2+事件时执行）

如果 Step 3A 发现了 L2+ 风险事件（或之前轮次发现的L2+事件尚未完成深挖）：

1. 读 `references/risk-tracking.md`（五步法：边界确认->时间线重建->传播链路->影响评估->关联方扫描）
2. 对需要深挖的关键URL，用脚本抓取全文：
   ```bash
   python3 scripts/sentiment-collect.py "品牌" --round N --fetch-url "URL1" "URL2"
   ```
3. 将分析结果写入报告素材（第二章2.3节和第四章4.1节的数据来源）

**如果没有新的L2+事件，仍需检查已有事件是否有未完成的深挖维度。**

#### Step 3C: 隐匿性发现（每轮必做，无条件执行）

**这是本Skill的核心差异化能力。每轮都必须执行，不可跳过。**

1. 读 `references/hidden-risk-discovery.md`（七大策略：R1语义去伪装 / R2关联实体辐射 / R3时间窗口异常 / R4跨域融合 / R5渠道下沉 / R6叙事框架转移 / R7反事实推演）
2. **基于当前已知的L2+事件和种子实体，为每个策略设计至少1个专项Query**
3. ⚠️ **R6策略必须执行完整Query清单（见下方【R6强制执行清单】），不可省略任何一组**
4. **⚠️ R6-G/H/I结果必须全文抓取分析（v2.5新增，解决snippet漏判问题）**：
   - R6-G/H/I的搜索结果**不能只看snippet（摘要）就下结论**
   - 对每条结果先用URL/标题做相关性初筛
   - **对高相关结果（标题或摘要含事件指纹关键词的），必须用 `--fetch-url` 抓取全文**
   - 原因：关键框架升级信息往往在文章正文深处，snippet看不到
   ```bash
   # 例：R6-G搜到相关文章后，抓全文确认是否包含本事件的框架升级内容
   python3 scripts/sentiment-collect.py "品牌" --round N_R6G_fetch --fetch-url "高相关URL1" "高相关URL2"
   ```
5. 通过脚本执行隐匿策略专项搜索：
   ```bash
   python3 scripts/sentiment-collect.py "品牌" --round N_R{策略号} --query "R策略Query1" "R策略Query2"
   # 例如：
   # --round 3_R1 --query '"买榜" 咨询公司' '"付费排名" 县域'
   # --round 3_R2 --query "海城市 其他项目" "辽宁 评比"
   # --round 3_R6 --query '"百强县" 典型案例' '"形式主义" 教育'
   ```
5. **读搜索结果，逐条判断是否为隐匿性负面信号**
6. **将确认的隐匿信号写入 `hidden_risks.json`**（必须创建此文件，格式见 output-specs.md）
7. 如果某条隐匿信号置信度高，围绕它再追加1-2轮验证搜索

**隐匿搜索的文件命名规则**：用 `--round N_RX` 前缀区分，如 `3_R1_q01.txt`, `3_R2_q01.txt`

#### 【R6强制执行清单】⚠️ 每轮Step 3C必须完整执行

当存在L2+事件时，R6策略的以下Query组**必须全部搜索，不可跳过任何一组**：

| 组别 | Query模板（用实际事件指纹替换{}） | 目标 |
|------|-----------------------------------|------|
| R6-A | `"{金额}" "{榜单/排名}" 通报` | 纳入反腐话语检测 |
| R6-B | `"新型腐败" "{行业关键词}"` 或 `"隐形腐败" "{行业关键词}"` | 新型腐败归类检测 |
| R6-C | `"{事件特征}" 典型案例` 或 `"{事件特征}" 警示教育` | 案例库入库检测 |
| R6-D | `"形式主义" "{地名}" 榜单` | 形式主义典型检测 |
| R6-E | `"某{机构类型}" {事件行为}` | 代称文章匹配 |
| R6-F | `{事件特征} 本质 是` 或 `{事件特征} 暴露` | 深度评论框架检测 |
| **R6-G（新增）** | **`"不收钱不收礼" {行业/事件关键词}`** | **新型腐败科普文检测** |
| **R6-H（新增）** | **`"第X种" {事件行为}` 或 `"{数字}种" 腐败 类型`** | **分类拆解文检测（如"6种腐败类型"）** |
| **R6-I（新增）** | **`"悄悄蔓延\|正在体制内\|值得警惕" {行业关键词}`** | **泛社会传播预警文检测** |

> **执行方法**：将以上9组Query分摊到不同轮次（每轮至少3组），但**收敛前必须全部执行完毕**。

#### Step 3D: 状态更新（每轮必做）

```python
# 必须更新 status.json:
# - current_round += 1
# - seeds[] 追加本轮新实体
# - risk_events[] 追加/更新
# - r6_query_groups_completed: 追加本轮已完成的R6组别编号
# - timestamps.last_updated = 当前时间
```

#### Step 3E: 二阶传播追踪（每轮必做，新增）

**原理**：当一个风险事件被中央/国家级信源通报后，它就不再只是"品牌的危机"，而变成了"公共议题"。公共议题会在各种框架下被二次、三次传播——反腐教育、普法文章、自媒体深度分析、高校案例等。这些传播**几乎不会出现品牌原名**。

**这是本次v2.4优化的核心新增步骤，专门解决"匿名引用盲区"问题。**

**操作步骤**：

1. **从每个L2+事件中提取「事件指纹」**（不含品牌名的唯一特征组合）：

   ```python
   # 以赛迪顾问买榜事件为例：
   event_fingerprint = {
       "behavior": "买榜/付费上榜/主观指标调分",
       "amount": "498万",
       "location": "海城市/鞍山/辽宁",
       "product": "百强县/榜单评价",
       "result": "从第118名到第91名",
       "nature": "形式主义/咨询费/虚假合作",
       "time": "2024年6月签约/2025年7月出榜"
   }
   ```

2. **用事件指纹 + 泛化叙事词组合搜索**（**完全不含品牌名**）：

   ```bash
   # 二阶传播追踪专用Query（每轮至少选3个方向搜索）
   python3 scripts/sentiment-collect.py "品牌" --round N_2nd --query \
     '"498万" "百强县"' \
     '"百强县" "主观指标"' \
     '"县域经济和新质生产力研究综合服务"' \
     '"买榜" "典型案例"' \
     '"咨询费" "榜单" "通报"' \
     '"第.*种" "腐败" "榜单"' \
     '"不收钱不收礼" "咨询"'
   ```

3. **对结果做「框架升级检测」**——判断每篇文章是否将事件置于比之前更危险的框架中：

   | 当前已知最危险框架 | 更危险框架（需要立即标记） |
   |-------------------|-------------------------|
   | 商业争议 | 形式主义典型 |
   | 形式主义典型 | **新型腐败/隐性腐败案例** |
   | 新型腐败案例 | **具体腐败罪名定性（如贪污/受贿/滥用职权）** |
   | 个案讨论 | **纳入全国性教育素材/教材/培训课程** |

4. **如果发现框架升级**：立即回到 Step 3C 补充对应方向的深挖搜索，并将发现作为**独立新条目**写入 hidden_risks.json 和报告（不要合并到原有事件中，它是独立的更高层级发现）。

5. **在 status.json 中记录二阶追踪状态**：
   ```json
   "second_order_tracking": {
     "event_fingerprints": ["指纹1", "指纹2"],
     "last_framework_detected": "形式主义典型",
     "framework_upgrade_found": true,
     "highest_risk_framework": "新型腐败第4类-虚假合作"
   }
   ```

#### 收敛判断（v2.4强化版）

五个条件**全部满足**才可收敛：
1. round >= 3
2. 连续2轮无新的 L1+ 信号
3. **hidden_risks.json 已创建且包含至少3条记录**
4. **R6强制执行清单的9组Query已全部执行完毕（检查status.json中的r6_query_groups_completed）**
5. **Step 3E二阶传播追踪已完成至少2轮，且最后一轮未发现框架升级**

任一不满足则继续下一轮。

### Step 4: 写报告

- 严格按 report-template.md 的8章结构填写
- 所有信源带URL（从 raw/ 文件中的搜索结果提取URL）
- 数据来源只列媒体/网站名称，不列搜索工具
- 技术支持固定写：赛迪网
- **第六章6.4隐匿信源表的数据来自 hidden_risks.json，必须填写**
- 执行自检清单（report-writing-guide.md 第8节）

### Step 5: 转PDF（⚠️ 必须执行，不可跳过）

**这是最后一步，报告写完后必须立即执行，不可因时间不够而跳过。**

**方法A：使用内置脚本（推荐）**
```bash
cd data/{品牌}/
python3 scripts/md2pdf.py report_v1.3.md report.pdf
```

**方法B：如果脚本失败，用备用方案（已验证可用）**
```bash
# B-1: MD → HTML
python3 -c "
import markdown
with open('data/{品牌}/report_v1.3.md','r') as f: md=f.read()
html=markdown.markdown(md,extensions=['tables','fenced_code'])
full_html='<!DOCTYPE html><html><head><meta charset=utf-8><style>@page{margin:0}body{font-family:\"Noto Sans SC\",SimHei,sans-serif;font-size:9.5pt;line-height:1.75;color:#1a1a1a;padding:15mm 16mm 18mm 16px;margin:0}h1{font-size:17pt;color:#1a5276;border-bottom:2.5px solid #1a5276;padding-bottom:8px;text-align:center;page-break-before:always;margin-top:20px}h1:first-of-type{page-break-before:avoid;margin-top:5px}h2{font-size:13pt;color:#2874a6;margin-top:20px;border-left:4px solid #2874a6;padding-left:10px}h3{font-size:11pt;color:#34495e;margin-top:14px}table{border-collapse:collapse;width:100%;margin:8px 0;font-size:8pt;table-layout:fixed;word-wrap:break-word;overflow-wrap:break-word}th,td{border:1px solid #bbb;padding:5px 6px;text-align:left;vertical-align:top;word-wrap:break-word;overflow-wrap:break-word;word-break:break-all}th{background:#eaf2f8;font-weight:bold;font-size:7.5pt}code{background:#f0f0f0;padding:1px 4px;border-radius:2pt;font-size:7.5pt;word-break:break-all}pre{background:#f5f5f5;padding:10px;border-radius:5px;overflow-x:auto;font-size:7.5pt;white-space:pre-wrap;word-wrap:break-word}p{margin:4px 0;text-align:justify}ul,ol{margin:4px 0;padding-left:18px}li{margin:2px 0}strong{color:#c0392b}blockquote{border-left:3px solid #2874a6;padding-left:10px;color:#555;margin:8px 0;font-size:9pt}</style></head><body>'+html+'</body></html>'
with open('/tmp/saidi_report.html','w') as f: f.write(full_html)
print('HTML OK')
"
# B-2: HTML → PDF (Chrome headless)
google-chrome --headless --disable-gpu --no-sandbox \
  --print-to-pdf="data/{品牌}/report.pdf" "file:///tmp/saidi_report.html"
```

**验证**: `ls -la data/{品牌}/report.pdf` 确认文件存在且 > 100KB

> **⚠️ 本机环境限制**：weasyprint有FFI bug、fpdf不支持中文TTC字体，均不可用。只用Chrome-based方案。

## 三大核心方法

| # | 方法 | 文件 | 执行方式 | 核心动作 |
|---|------|------|---------|---------|
| **1** | **常规搜索+早期发现** | `references/early-detection.md` | **每轮Step 3A必做** | Layer0五行嗅探 + Query设计 |
| **2** | **隐匿性发现** | `references/hidden-risk-discovery.md` | **每轮Step 3C必做** | R1-R7七大策略，每策略至少1个专项Query |
| **3** | **风险深挖** | `references/risk-tracking.md` | **每轮Step 3B必做** | 五步法纵深挖掘 |

## 脚本用法速查

```bash
# 常规搜索（每轮Step 3A）
python3 scripts/sentiment-collect.py "品牌" --round 1 --query "关键词1" "关键词2"

# 隐匿策略搜索（每轮Step 3C，用 _RX 后缀区分）
python3 scripts/sentiment-collect.py "品牌" --round 2_R1 --query "语义去伪装query"
python3 scripts/sentiment-collect.py "品牌" --round 2_R2 --query "关联实体query"
python3 scripts/sentiment-collect.py "品牌" --round 2_R6 --query "框架转移query"

# URL深挖（Step 3B）
python3 scripts/sentiment-collect.py "品牌" --round 3 --fetch-url "https://..."

# 百科查询（Phase 0，只查一次）
python3 scripts/sentiment-collect.py "品牌" --baike
```

**重要：每轮搜索必须加 `--round N`（N=当前轮次号），否则会覆盖之前的数据文件。**

## 硬性禁令与正确做法

| # | 禁止 | 正确做法 |
|---|------|---------|
| 1 | 自己调用web_search/web_fetch/百度工具来收集数据 | 所有数据收集通过 `python3 scripts/sentiment-collect.py` 完成 |
| 2 | 出现"百度AI搜索""web_fetch""Brave搜索"等任何搜索工具名称 | 信息来源只写媒体或网站名称 |
| 3 | 技术支持写其他内容 | 固定只写四个字：**赛迪网** |
| 4 | 自创模板外章节 | 只写template中的8个章节 |
| 5 | 跳过数据沉淀（不生成status.json） | Phase 0结束后必须创建status.json并每轮更新 |
| 6 | **跳过隐匿性发现（Step 3C）或不执行R1-R7策略搜索** | 每轮必须为每个R策略设计至少1个Query并通过脚本搜索，结果写入hidden_risks.json |
| 7 | **不生成hidden_risks.json文件** | 必须创建此文件，即使无发现也要写明"经七策略全扫描，未发现额外隐匿信号"及每个策略的扫描结论 |
| 8 | 编造URL | 找不到真实URL就写"URL缺失: 原因说明" |
| 9 | **将"同一事件+新框架"误判为重复信息** | **当已抓取的事件在新的搜索结果中以更危险的叙事框架出现时，必须识别为「框架升级」而非「信息重复」。这是v2.4新增的核心分析能力要求。** |

## 数据沉淀（必产出的三个文件）

| 文件 | 内容 | 创建时机 |
|------|------|---------|
| `raw/*.txt` | 每次搜索原始结果 | **脚本自动写入**（每轮搜索后） |
| `status.json` | 迭代状态中枢（含r6_query_groups_completed + second_order_tracking） | **Phase 0创建，每轮Step 3D更新** |
| `hidden_risks.json` | 隐匿性风险信号表（含框架升级记录） | **Step 3C首次执行时创建，之后每轮追加** |

**三个文件缺一不可。缺少任何一个都视为任务未完成。**

## 文件导航

| 类型 | 文件 | 用途 |
|------|------|------|
| 主文件 | SKILL.md（本文件） | 执行入口 |
| 数据采集脚本 | scripts/sentiment-collect.py | **所有搜索/抓取都通过此脚本** |
| 格式基准 | templates/report-template.md | 8章报告模板 |
| 状态模板 | templates/status-template.json | status.json填空模板 |
| 核心1 | references/early-detection.md | 早期发现四层漏斗 |
| 核心2 | references/hidden-risk-discovery.md | 隐匿性发现七大策略 |
| 核心3 | references/risk-tracking.md | 风险事件深挖 |
| 写作规范 | references/report-writing-guide.md | 8章写作指南+自检清单 |
| 身份设定 | references/analyst-identity.md | 分析师身份+语气 |
| PDF转换 | scripts/md2pdf.py | MD转PDF |

## 能力版本记录

| 版本 | 变更 |
|------|------|
| v2.0 | 大精简：聚焦三大核心，总代码量-82% |
| v2.1 | 去除emoji；禁止项改为对照格式 |
| v2.2 | 引入sentiment-collect.py数据采集脚本 |
| v2.2.1 | 新增--round参数防数据覆盖 |
| **v2.4** | **新增Step 3E二阶传播追踪（解决匿名引用盲区）；R6强制执行清单从6组扩展到9组（+G/H/I）；收敛条件从3项增加到5项；新增框架升级检测表** |
| **v2.5** | **R6-G/H/I搜索结果必须全文抓取分析（不可只看snippet）；Step 5转PDF增加备用方案和失败排查指南；修复子任务报告生成阶段卡住问题** |
