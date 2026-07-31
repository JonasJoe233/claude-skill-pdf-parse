# pdf-parse — 跨执行索引

本 skill 是纯工具型（不产出交付物），`raw/` 只存偶发的调试样本；真正需要跨执行沉淀的是**判定阈值的标定依据**和**已知的问题 PDF 来源**，记在下面。

## 默认入口

```bash
python3 ~/.claude/skills/pdf-parse/pdf_triage.py <pdf>
```

见 [[pdf-parse/SKILL]] 的「按 VERDICT 行动」表。任何读 PDF 的任务第一步都是它，不要手写 PyMuPDF。

## 阈值标定依据（改判据前先看这里）

标定语料：`~/Downloads/*简历*.pdf`，23 份中文简历（招聘系统导出为主），2026-07-31。

| 判据 | 阈值 | 标定结果 |
|------|------|---------|
| 乱码比 `moji / cjk` | > 4% → `TEXT_PARTIAL` | 正常文档 0–1.7%（最高：简历9.pdf 1.64%）；坏字体文档 10.05%（张芷依）。4% 卡在两簇中间，留足余量 |
| 矢量路径数 `drawings` | > 300 且 CJK 稀少 → `VECTOR_OUTLINED` | 转曲文档 845–1254；注意**正常文档也可能上千**（王明金 2080、吴尚坤 1309），所以 drawings 必须与「CJK 稀少」联合判断，单独用会误杀 |
| 水印行 | 页内重复 ≥3 次的整行剔除 | 招聘系统水印每页嵌 3–20 行相同哈希串，不剔除会把字数统计撑到"看起来正常" |

**改阈值必须重跑全语料回归**：`for f in ~/Downloads/*简历*.pdf; do python3 pdf_triage.py "$f" | grep ^VERDICT; done`，期望只有张芷依=TEXT_PARTIAL、季宣儒=VECTOR_OUTLINED，其余全 TEXT_OK。

## 已知问题 PDF 来源

| 来源 | 症状 | VERDICT |
|------|------|---------|
| 百度内部招聘系统导出（`C0xxxxxxx-姓名-原始简历.pdf`） | 多数正常；少量整页转曲或字体子集混淆，每页嵌重复哈希水印 | 多为 `TEXT_OK`，偶发 `VECTOR_OUTLINED` / `TEXT_PARTIAL` |
| 季宣儒简历（C05081597） | 整页文字转曲，文本层仅剩水印串 | `VECTOR_OUTLINED` |
| 张芷依简历（C04767587） | 正文中文可读，标题/公司名/技能行 cmap 坏成拉丁扩展字符 | `TEXT_PARTIAL`（最危险的一类：不校对就会把错的公司名写进结论） |

## 关联

- [[hiring/SKILL]] — 主要消费方：筛简历/出面试题前先用本 skill 读简历
