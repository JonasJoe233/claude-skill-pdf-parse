#!/usr/bin/env python3
"""PDF 预检（triage）：一次调用判定文本层能不能用，不能用就直接渲染 PNG 供视觉读取。

设计目标：消灭「先试 get_text 拿到乱码 → 再手写渲染 → 再撞沙箱权限」的三轮试错。
毫秒级完成，不加载任何模型；只有文本层判死时才渲染图片。

用法：
    python3 pdf_triage.py <pdf> [--dpi 150] [--max-width 1600] [--outdir DIR] [--force-render]

stdout 输出 VERDICT + 可用文本，或需要用 Read 工具读的 PNG 路径。
"""
import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    sys.exit("缺少 pymupdf：pip3 install --user pymupdf")

CJK = re.compile(r"[㐀-䶿一-鿿぀-ヿ가-힯]")
JUNK = re.compile(r"[-�]")  # 私有区/替换符 → cmap 坏了，取出来是乱码
MIN_CJK = 15       # 中文文档正常一页远超此值
MIN_CHARS = 80

VERDICT_HINT = {
    "TEXT_OK": "文本层完好，直接用下方文本，不要渲染图片",
    "TEXT_SUSPECT": "文本量偏少，文本与图片都给了；先看文本，明显不全再 Read 图片",
    "VECTOR_OUTLINED": "文字已转曲为矢量路径（文本层只剩水印）→ 必须走图片视觉识别",
    "BROKEN_CMAP": "字体 cmap 损坏/被混淆，取出的是乱码 → 必须走图片视觉识别",
    "SCANNED": "扫描件/纯图片 PDF → 必须走图片视觉识别",
    "TEXT_BAD": "文本层不可用（原因未归类）→ 走图片视觉识别",
    "ENCRYPTED": "PDF 加密且空密码打不开 → 需用户提供密码",
}


def analyze(page):
    text = page.get_text()
    lines = [l for l in text.splitlines() if l.strip()]
    counts = Counter(lines)
    # 同一页内重复 ≥3 次的整行判为水印，剔除后再评估正文含量
    body = "\n".join(l for l in lines if counts[l] < 3)
    return {
        "body": body,
        "chars": len(body.strip()),
        "cjk": len(CJK.findall(body)),
        "junk": len(JUNK.findall(body)),
        "drawings": len(page.get_drawings()),
        "images": len(page.get_images(full=True)),
        "wm": sum(v for v in counts.values() if v >= 3),
    }


def verdict_of(a):
    if a["junk"] * 5 >= max(a["chars"], 1):
        return "BROKEN_CMAP"
    if a["chars"] >= MIN_CHARS:
        return "TEXT_OK" if (a["cjk"] >= MIN_CJK or a["chars"] >= 400) else "TEXT_SUSPECT"
    if a["drawings"] > 300:
        return "VECTOR_OUTLINED"
    if a["images"]:
        return "SCANNED"
    return "TEXT_BAD"


def writable_outdir(explicit, stem):
    # 沙箱下 /tmp 直写会 Operation not permitted；TMPDIR 一定可写
    cands = [explicit] if explicit else []
    cands += [os.environ.get("TMPDIR"), Path.home() / ".cache", "."]
    for c in cands:
        if not c:
            continue
        d = Path(c).expanduser() / "pdf-triage" / stem
        try:
            d.mkdir(parents=True, exist_ok=True)
            probe = d / ".w"
            probe.write_text("1")
            probe.unlink()
            return d
        except OSError:
            continue
    sys.exit("找不到可写目录用于渲染 PNG")
