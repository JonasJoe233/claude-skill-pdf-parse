---
name: pdf-parse
description: 将 PDF 转换为 Markdown，基于 marker-pdf，支持文本 PDF、图像 PDF、扫描件、表格、公式。自动安装依赖，任何机器开箱即用。
type: skill
---

# PDF → Markdown 转换 Skill

## 功能

- 文本型 PDF、图像型 PDF（扫描件）、含表格/公式的 PDF 全部支持
- 输出结构化 Markdown，保留标题层级、表格、LaTeX 公式
- 基于 [marker-pdf](https://github.com/datalab-to/marker)，自动判断是否需要 OCR
- **首次运行自动安装依赖（含模型文件），无需手动配置**

## 使用方式

用户提供 PDF 路径即可触发：

- `解析这个 PDF：/path/to/file.pdf`
- `把 ~/Desktop/report.pdf 转成 Markdown`
- `/pdf-parse ~/Downloads/合同.pdf`

## 工作流程

1. 将用户提供的路径展开为绝对路径
2. 运行 `python3 {SKILL_DIR}/parse_pdf.py <pdf_path>`
3. 脚本自动安装依赖（如未安装），加载模型，转换 PDF
4. 将输出的 Markdown 内容直接返回给用户

## 注意事项

- **首次运行较慢**：需下载 marker 模型文件（约数百 MB），完成后后续运行正常
- 转换进度和状态信息输出到 stderr，Markdown 正文输出到 stdout
- 需要网络连接（首次安装依赖和下载模型）
- Python 3.10+ 推荐（marker-pdf 官方要求）
