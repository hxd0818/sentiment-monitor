# 过程文件参考

> **status.json = 迭代中枢（必须维护）。hidden_risks.json = 可选草稿。raw/ = 脚本自动产出。**
> **唯一用户可见产出：report_v1.3.md + report.pdf。**

---

## data/{品牌名}/ 目录

```
data/{品牌名}/
├── raw/                           # 原始搜索数据（脚本自动写入）
│   └── *.txt                      # 每次搜索一个文件
├── status.json                    # ★ 迭代中枢（必须创建，每轮更新）
├── hidden_risks.json             # [可选] 隐匿发现详细记录
├── report_v1.3.md                # ★ 最终报告
└── report_v1.3.pdf               # ★ 最终报告PDF
```

---

## status.json — 迭代中枢（必须）

**这不是可选的。是整个迭代机制的物理基础。**

每轮循环的 ①读 和 ⑤写 都围绕这个文件。
没有它 → Agent失忆 → 不是迭代，是重复。

完整schema见 `references/methodology.md` §二.1。
初始化时从 `assets/status-template.json` 复制后填空。

### 核心字段速查

| 字段段 | 为什么重要 |
|--------|-----------|
| `seed_pool.seeds[].next_directions` | 扩散的物理载体：记录"还想搜什么方向" |
| `risk_events[].unknowns` | 深挖的物理载体：记录"还不知道什么" |
| `search_log[].information_gain` | 收敛的数据基础：信息增益趋势 |
| `search_log[].next_thinking` | 跨轮记忆：下轮从这里接着想 |
| `seed_pool.seeds[].depth` + `parent` | 种子分裂树：追溯挖掘路径 |

---

## hidden_risks.json — 可选

用途：写报告6.4节时回顾隐匿发现的细节。
如果 status.json 的 `hidden_risks_found` 已经够用，可以不创建此文件。

---

## raw/ 文件

由脚本自动创建和管理。Agent只需要知道怎么读它们。

*重写说明：v3.1确认status.json为必须维护的迭代中枢，不再是可选工具。*
