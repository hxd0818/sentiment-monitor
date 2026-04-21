# 隐匿性风险发现 — 迭代深挖体系 v3.1

> **核心：隐匿发现不是一次性扫描，而是一个持续演化的子迭代体系。**
> **它有自己的状态、自己的积累、自己的收敛判断——并与主循环双向交互。**

---

## 一、体系定位

```
┌─────────────────────────────────────────────────────┐
│                  主循环（搜索→分析→写状态）            │
│                                                     │
│  ┌───────────────────────────────────────────┐      │
│  │       隐匿发现子体系（平行迭代）              │      │
│  │                                           │      │
│  │  隐匿状态(hs_) ──→ 透镜选择 ──→ 搜/验证 ──┘      │
│  │       ↑                    │                   │
│  │       └────────────────────┘                   │
│  │         发现写入hs_ + 反哺种子池               │      │
│  └───────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────┘

关键理解：
- 隐匿发现不是主循环里的"一步"，而是一个嵌套在主循环内的子迭代
- 每一轮主循环都可能触发0次或多次隐匿发现子迭代
- 隐匿发现有自己的状态（记录在status.json中），跨轮积累
- 隐匿发现的成果反哺主循环的种子池（新实体、新事件、新方向）
```

---

## 二、隐匿状态的物理载体

隐匿发现的状态**不单独存文件**，而是作为 status.json 中的一个段。
这样隐匿状态和主循环状态在同一文件中，保证一致性。

### status.json 中的隐匿状态段

```json
{
  "hidden_state": {
    "_meta": "隐匿发现子体系的迭代状态。每轮主循环结束时同步更新。",

    "lens_log": [
      {
        "round": 2,
        "lens": "R6",
        "trigger": "RE-001事件的叙事框架可能从'商业争议'向'形式主义'转移",
        "queries_used": ["q1", "q2"],
        "results_summary": "发现1篇框架升级文章",
        "new_findings": ["HR-3"],
        "next_lens_suggested": ["R1(用新框架关键词再搜)"]
      }
    ],

    "coverage_map": {
      "R1": {"status": "pending|active|matured|exhausted", "last_round": 0, "findings_count": 0, "notes": ""},
      "R2": {"status": "pending", "last_round": 0, "findings_count": 0, "notes": ""},
      "R3": {"status": "pending", "last_round": 0, "findings_count": 0, "notes": ""},
      "R4": {"status": "pending", "last_round": 0, "findings_count": 0, "notes": ""},
      "R5": {"status": "pending", "last_round": 0, "findings_count": 0, "notes": ""},
      "R6": {"status": "pending", "last_round": 0, "findings_count": 0, "notes": ""},
      "R7": {"status": "pending", "last_round": 0, "findings_count": 0, "notes": ""}
    },

    "evolution_chain": [
      {
        "step": 1,
        "round": 2,
        "from_lens": "R6",
        "discovery": "发现'新型腐败'框架下的文章",
        "original_event": "RE-001",
        "new_framework": "商业争议 → 形式主义典型 → 新型腐败",
        "child_findings": ["HR-3"],
        "triggered_next": "R1(用'新型腐败'+金额特征搜)"
      }
    ],

    "convergence": {
      "is_converged": false,
      "reason": "",
      "evidence": {
        "rounds_since_last_finding": 0,
        "inactive_lenses": [],
        "all_exhausted": false
      }
    }
  }
}
```

### 各字段的设计意图

| 字段 | 为什么需要 |
|------|-----------|
| **lens_log** | 记录每个透镜每次执行的细节。跨轮知道"R6上次用的是什么思路搜的，发现了什么" |
| **coverage_map** | 7个透镜各自的覆盖状态。知道哪些透镜还没用过、哪些用过但没发现、哪些有发现值得再用 |
| **evolution_chain** | **这是隐匿发现迭代的核心**。记录"A发现→触发B→B又触发C"的链式反应 |
| **convergence** | 隐匿子体系的独立收敛判断。与主循环收敛分开 |

---

## 三、隐匿发现的迭代机制

### 3.1 什么时候启动隐匿发现

**不是固定时机。以下任一条件触发：**

| 触发条件 | 启动方式 |
|---------|---------|
| 主循环发现L2+风险事件 | 围绕该事件启动相关透镜 |
| 主循环连续2轮gain=low | 用coverage_map检查哪个透镜还没试过 |
| 某个透镜上轮有发现且suggest了next_lens | 执行建议的下一个透镜 |
| 收敛前最后检查 | 对所有active/matured透镜做最后一轮深化 |
| Agent直觉觉得"不对劲" | 自由选择透镜 |

### 3.2 单次隐匿发现的执行流程

```
① 选择透镜（选哪个？为什么选这个？）
   基于当前状态：
   - coverage_map中哪个透镜是pending/exhausted但有新素材？
   - 上次lens_log里有没有suggest了next_lens？
   - 当前风险事件的性质最匹配哪个透镜？

② 设计隐匿Query（去品牌名！）
   基于所选透镜的思考方向 + 当前已知的事件特征
   关键：用事件指纹、金额数字、行为动词、委婉语——就是不用品牌名

③ 执行搜索 + 读结果

④ 分析结果：
   - 发现隐匿信号？→ 记入 hidden_risks_found + evolution_chain
   - 没发现？→ 更新 coverage_map 标记该透镜本轮无收获
   - 发现但不确定？→ --fetch-url 抓全文确认

⑤ 【关键】反哺主循环状态：
   - 隐匿信号涉及的新实体 → 加入 seed_pool
   - 隐匿信号关联的新事件 → 加入/更新 risk_events
   - 触发的新搜索方向 → 写入相关种子的 next_directions

⑥ 更新 hidden_state（lens_log + coverage_map + evolution_chain）
```

### 3.3 链式演化（隐匿发现的核心价值）

**隐匿发现最大的价值不是单次扫描，而是透镜之间的链式反应。**

```
实际案例（赛迪顾问）：

第2轮 主循环: 发现"百强县买榜事件"(RE-001)
           ↓
第2轮 隐匿启动(R6): "这件事会不会被框架升级？"
           → 搜: "百强县 买榜 形式主义"
           → 发现: 确实有文章开始用"形式主义"框架
           → evolution_chain记录: step1, R6, 商业争议→形式主义
           → suggest next: R1(用"形式主义"+特征词再搜)
           ↓
第3轮 隐匿启动(R1): "用新框架词搜，有没有更隐蔽的文章？"
           → 搜: "形式主义 百强县 咨询费"
           → 发现: 一篇"某咨询公司"文章(L1语义伪装)
           → evolution_chain记录: step2, R1, 发现L1信号
           → suggest next: R5(看看小平台怎么讨论这事)
           ↓
第3轮 隐匿启动(R5): "渠道下沉看看"
           → 搜: 公众号/知乎相关讨论
           → 发现: 有文章把此事归入"新型腐败"类别
           → evolution_chain记录: step3, R5, 框架再次升级!
           → suggest next: R6 again(用"新型腐败"框架再验证)
           ↓
第4轮 隐匿启动(R6): "新型腐败框架下有多少二次传播？"
           → 搜: "新型腐败 百强县 榜单 咨询"
           → 发现: 多篇纪法教育文章，完全不用品牌名
           → L5框架转移确认！
           → evolution_chain记录: step4, R5→R6最终确认
```

**这就是迭代积累。每一轮的输出是下一轮的输入。**

### 3.4 evolution_chain 的设计意图

```json
{
  "evolution_chain": [
    {"step": 1, "from_lens": "R6", "discovery": "...", "triggered_next": "R1"},
    {"step": 2, "from_lens": "R1", "discovery": "...", "triggered_next": "R5"},
    {"step": 3, "from_lens": "R5", "discovery": "...", "triggered_next": "R6"},
    {"step": 4, "from_lens": "R6", "discovery": "...", "triggered_next": null}
  ]
}
```

- `step` 序号 = 迭代深度（越深说明挖得越透）
- `from_lens` = 这一步用了哪个透镜
- `triggered_next` = 这一步的发现触发了下一步用什么透镜
- 如果 `triggered_next` = null → 链条到头了，这个方向收敛

**Agent可以通过回顾evolution_chain回答：**
- "我在隐匿发现上走了多远？"（看step数）
- "我是怎么从最初的事件找到这篇完全脱品牌名文章的？"（追溯链路）
- "还有没有没探索过的分支？"（看哪些透镜没在链中出现）

---

## 四、隐匿发现的收敛判断

### 4.1 何时隐匿子体系收敛

**独立于主循环的收敛。** 条件：

1. **coverage_map** 中所有透镜都是 exhausted 或 matured（至少用过一次且无新发现）
2. **evolution_chain** 最后一步的 `triggered_next` = null（链式反应自然终止）
3. **rounds_since_last_finding** >= 2（连续2轮主循环没有新的隐匿发现）

### 4.2 不收敛的情况（继续挖）

| 情况 | 做法 |
|------|------|
| evolution_chain还有活跃分支 | 沿着分支继续 |
| 某个透镜之前用了但现在有了新素材（如新事件） | 重新激活该透镜 |
| 主循环发现了新的L2+事件 | 围绕新事件启动新一轮隐匿扫描 |
| R6检测到框架升级迹象 | 框架升级本身就是不收敛信号 |

---

## 五、七个透镜速查（思考方向，非执行清单）

| 透镜 | 核心问题 | 什么时候用 |
|------|---------|-----------|
| **R1 语义伪装** | 不点名品牌的话，会用什么词？ | 想找代称/委婉语文章时 |
| **R2 实体辐射** | 关联方有没有出事？ | 种子池积累了关联实体后 |
| **R3 时间共振** | 前后有没有异常聚集？ | 已知事件的时间点附近 |
| **R4 跨域融合** | 其他领域也出问题了吗？ | 想交叉验证时 |
| **R5 渠道下沉** | 小平台有人在议论吗？ | 主流信源已充分覆盖后 |
| **R6 框架转移** | 叙事角度在向危险方向变吗？ | **最重要**，有L2+事件就应考虑 |
| **R7 反事实推演** | 如果恶化会怎样？有先兆吗？ | 其他透镜都有发现后 |

---

*v3.1: 从v3.0的'7个思考透镜'升级为'带状态的迭代深挖体系'。核心变化：(1)新增hidden_state段(status.json内)，含lens_log/coverage_map/evolution_chain/convergence四个状态结构；(2)定义隐匿发现的触发条件、单次执行流程、链式演化机制；(3)隐匿状态与主循环状态双向交互——隐匿发现反哺种子池，主循环发现触发隐匿扫描。*
