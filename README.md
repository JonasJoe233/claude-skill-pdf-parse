# pdf-parse

**A Claude Code skill that converts PDFs to Markdown — zero manual setup, works on any machine.**

> 一个 Claude Code skill，把 PDF 转成 Markdown。`git clone` 即完成跨设备配置。

---

## 解决什么问题

### 第一个问题：大型图像 PDF 在 Claude Code 里解析失败

Claude Code 内置的 `Read` 工具能处理简单 PDF，但碰到大型图像型 PDF（扫描件、设计稿、多页合同）时经常报错：

```
Error: PDF too large to read at once. Use the pages parameter.
```

即使分页读取，遇到复杂布局、多栏排版、表格、公式，识别质量也不稳定。[marker](https://github.com/datalab-to/marker) 是专为 PDF → Markdown 转换设计的开源工具，能正确处理这些场景，输出带层级结构的干净 Markdown。

### 第二个问题：跨设备环境配置无法平迁

找到好工具只是开始。真正的麻烦是：

> 我有多台设备（工作机、家用机、新买的电脑），每台都要手动 `pip install`、配环境、装模型。这些配置分散在本地，没有版本管理，换台电脑就要重来一遍。

### 这个 Skill 的解法

**把"工具 + 安装逻辑"打包成一个 git 仓库。**

```bash
git clone https://github.com/your-username/pdf-parse ~/.claude/skills/pdf-parse
```

一条命令，新设备上的 Claude Code 立即拥有和其他设备完全相同的 PDF 解析能力。脚本首次运行时自动安装 marker-pdf 及所需模型，无需任何手动配置。

---

## 工作原理

```
PDF 文件
  │
  └─ marker-pdf
       ├─ 文本型 PDF → 直接提取文本层
       └─ 图像型 PDF → OCR（surya 模型）
                              │
                         Markdown 输出
                    （标题 / 表格 / LaTeX 公式）
```

marker 会自动判断是否需要 OCR，文本型 PDF 快速提取，图像型 PDF 走模型推理，无需人工干预。

---

## 前置要求

- [Claude Code](https://claude.ai/code) 已安装
- Python 3.10+
- 首次运行需要网络（自动安装 marker-pdf + 下载 OCR 模型，**总计约数百 MB，请预留时间**）

---

## 安装

```bash
git clone https://github.com/your-username/pdf-parse ~/.claude/skills/pdf-parse
```

无需重启 Claude Code，技能立即生效。

```
~/.claude/skills/
└── pdf-parse/
    ├── SKILL.md        ← Claude Code 读取的技能定义
    ├── parse_pdf.py    ← 核心脚本（含自动安装逻辑）
    └── README.md
```

---

## 使用方式

在 Claude Code 对话中直接说：

```
解析这个 PDF：/Users/yourname/Desktop/report.pdf
```

```
把 ~/Downloads/合同.pdf 转成 Markdown
```

**首次运行**输出示例：

```
正在安装 marker-pdf（首次安装包含 PyTorch，体积较大，请耐心等待）...
marker-pdf 安装完成
正在加载模型（首次运行需下载模型文件，约数百 MB，请耐心等待）...
正在解析: /Users/yourname/Desktop/report.pdf
```

之后直接运行，无重复安装和下载。

---

## 输出示例

```markdown
# 季度财务报告

## 概览

| 指标 | Q3 | Q4 |
|------|----|----|
| 营收 | 120M | 145M |
| 利润率 | 18% | 21% |

## 技术指标

损失函数定义为：

$$L = -\sum_{i} y_i \log(\hat{y}_i)$$
```

标题层级、表格结构、LaTeX 公式均完整保留。

---

## 设计决策

**为什么用 marker 而不是 PyMuPDF + Claude 视觉？**

PyMuPDF 渲染图片后让模型逐页识别，大型 PDF 会触发 Claude Code 内置 `Read` 工具的页数限制和渲染错误。marker 在本地完成所有解析，不依赖模型的视觉通道，输出更稳定，且直接产出结构化 Markdown。

**为什么不用 MCP Server？**

MCP Server 需要独立配置文件和进程管理，在多设备场景下同样面临配置同步问题。

**首次安装慢是设计缺陷吗？**

不是。模型只下载一次，之后缓存在本地，后续每台机器 clone 后首次运行下载，之后永久可用。这个成本远低于每台设备手动配置环境的重复劳动。

---

## 局限性

- 首次运行需下载 OCR 模型（约数百 MB），网络受限环境需提前手动安装
- 受网络代理限制的环境手动安装：`pip install marker-pdf`
- Python 3.10+ 要求（marker-pdf 官方限制）

---

## License

MIT
