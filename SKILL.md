---
name: pdf-parse
description: |
  读取任何 PDF 的内容：先秒级预检文本层，判定加密/转曲/乱码/扫描件，再决定直接取文本还是渲染图片视觉识别。
  触发词：解析 PDF、提取 PDF 内容、PDF 转文字/Markdown、读取 PDF、看 PDF、PDF 乱码、PDF 打不开、parse PDF、extract PDF、convert PDF to text。
  确定性触发（直接执行）：**任何需要读取 PDF 内容的任务**——包括看简历、读合同、读报告、抽表格——第一步都跑 pdf_triage.py，不要自己写 PyMuPDF 代码。
  非确定性触发（先问）：只提到 PDF 文件名未说用途——询问："需要把这个 PDF 解析成 Markdown 吗？"
tags:
  - pdf-parse
type: skill
---

## 目录文件说明

| 文件 | 作用 |
|------|------|
| [[pdf-parse/SKILL]] | Skill 主文件，定义触发条件、工作流程、注意事项 |
| [[pdf-parse/meta]] | 关联声明：topics/product_scope/data 字段，供 `_discover.py` 自动计算与其他 skill 的关联关系 |
| [[pdf-parse/wiki]] | 跨执行索引：判定阈值的标定依据（改阈值前必读）+ 已知问题 PDF 来源清单 |
| [[pdf-parse/pdf_triage.py\|pdf_triage.py]] | **默认入口**：文本层预检 + 按需渲染 PNG（毫秒级，零模型，处理加密/转曲/乱码/扫描件） |
| [[pdf-parse/parse_pdf.py\|parse_pdf.py]] | 重型兜底：marker-pdf 转结构化 Markdown（表格/公式/OCR，自动装依赖） |
| [[pdf-parse/README]] | 快速使用说明 |
| [[pdf-parse/progress]] | 开发进度记录 |
| [[pdf-parse/task_plan]] | 历史任务规划文件 |
| `.gitignore` | Git 忽略规则 |
| `raw/` | 执行归档（本 skill 为工具型，通常不产物；仅在遇到新型加密混淆 PDF 时归档到 `raw/YYYY-MM-DD_<症状>/` 留样本，并把阈值标定结论写进 [[pdf-parse/wiki]]） |
| [[pdf-parse/wiki]] | (待补充用途说明) |

# PDF 读取 Skill

## 铁律：读 PDF 永远从 triage 开始，不要手写 PyMuPDF

```bash
python3 ~/.claude/skills/pdf-parse/pdf_triage.py <pdf_path>
```

一次调用（约 0.2–0.6 秒，不加载任何模型）同时完成：判定文本层能不能用、剔除水印行、给出可用文本、文本判死时自动渲染 PNG 并打印路径。**禁止再写 `fitz.open(...).get_text()` 的临时脚本去试** —— 那条路必然是「拿到乱码 → 再手写渲染 → 再撞沙箱写权限」三轮返工，本 skill 存在的意义就是消灭这三轮。

## 按 VERDICT 行动

| VERDICT | 含义 | 你该做什么 |
|---------|------|-----------|
| `TEXT_OK` | 文本层完好 | 直接用输出的文本，**不要 Read 图片** |
| `TEXT_PARTIAL` | 部分字体 cmap 坏（正文可读、标题/公司名成乱码） | 文本+图片都给了；用 `[?]` 标记的行必须对照图片校对 |
| `TEXT_SUSPECT` | 文本量偏少 | 先看文本，明显不全再 Read 图片 |
| `VECTOR_OUTLINED` | 文字已转曲成矢量路径，文本层只剩水印 | 只能 Read 图片做视觉识别 |
| `BROKEN_CMAP` | 字体映射被混淆，取出的全是乱码 | 只能 Read 图片做视觉识别 |
| `SCANNED` | 扫描件/纯图片 | Read 图片；要结构化表格/公式才升级 `parse_pdf.py` |
| `ENCRYPTED` | 加密且空密码打不开 | 停下来找用户要密码 |

图片路径直接用 Read 工具读（视觉识别），**不要再调 OCR**。渲染默认 150 dpi、限宽 1600px，简历/合同类文档足够看清；模糊时加 `--dpi 200`。

## 关于「加密混淆」这类 PDF（招聘系统导出简历最常见）

BOSS 直聘、猎聘、内部招聘系统导出的简历常做防复制处理，表现为三类，triage 已全部覆盖：

1. **文字转曲**（`VECTOR_OUTLINED`）：整页文字变成上千条矢量路径，`get_text()` 只剩重复的水印哈希串。判据是 CJK 极少 + drawings > 300。
2. **字体子集混淆**（`BROKEN_CMAP` / `TEXT_PARTIAL`）：cmap 被打乱，取出来是 `·š` `BLˆAI` 这种拉丁扩展字符。判据是乱码字符数 / CJK 数 > 4%（实测 23 份中文简历语料：正常文档 ≤1.7%，坏字体 ≥10%）。**危险的是 `TEXT_PARTIAL`——正文读得通、只有标题和公司名是乱码，最容易把错的公司名写进结论**，所以这类一律强制配图校对。
3. **满页重复水印**：每页嵌几十行相同哈希串干扰判断。triage 把页内重复 ≥3 次的整行剔除后再评估，水印不再污染字数统计。

## 参数

| 参数 | 默认 | 用途 |
|------|------|------|
| `--dpi` | 150 | 渲染精度，看不清时提到 200 |
| `--max-width` | 1600 | 像素限宽，避免图过大拖慢视觉读取 |
| `--max-pages` | 20 | 只分析/渲染前 N 页 |
| `--force-render` | — | 无论判定如何都渲染图片 |
| `--outdir` | 自动 | 输出目录；默认落 `$TMPDIR/pdf-triage/<文件名>/`（沙箱下 `/tmp` 直写会 Operation not permitted，脚本已自动规避并逐级探测可写目录） |

## 什么时候升级到 parse_pdf.py（marker-pdf）

**只在需要「结构化 Markdown」时**——多页扫描件要保留标题层级、复杂表格要转 Markdown table、含 LaTeX 公式的论文。代价是首次运行要下载数百 MB 模型、单次转换几十秒到几分钟。

```bash
python3 ~/.claude/skills/pdf-parse/parse_pdf.py <pdf_path>
```

只是「看懂内容」（简历、合同、报告）**不要用它**——triage 出图 + 视觉识别快一到两个数量级，且不吃 GPU。

## 注意事项

- triage 无外部依赖，只需 pymupdf；`parse_pdf.py` 首次运行需联网装依赖和模型
- triage 全部输出走 stdout，可直接管道 grep `^VERDICT`
- 视觉识别读图时，人名/公司名/数字要逐字核对，别凭印象补全

## 遇到判错时：归档到 raw/ 并更新标定

triage 判错（把坏文本判成 `TEXT_OK`，或把正常文档误判为需渲染）时，不要就地改阈值了事：

1. 把样本 PDF 归档到 `raw/YYYY-MM-DD_<症状>/`，同目录写 `input.md` 记录判错表现。
2. 调阈值后**必须重跑全语料回归**（命令与期望结果见 [[pdf-parse/wiki]]），确认没有引入新的误判。
3. 把新的标定依据写进 [[pdf-parse/wiki]] 的阈值表——阈值的价值全在标定语料上，不记录等于下次重新试错。

---

## 目录结构

```
pdf-parse/
├── SKILL.md         # 本文件，skill 主逻辑
├── meta.md          # 关联声明，供 _discover.py 计算关联 skill
├── pdf_triage.py    # 默认入口：预检 + 按需渲染 PNG（毫秒级）
└── parse_pdf.py     # 重型兜底：marker-pdf 转结构化 Markdown
```
