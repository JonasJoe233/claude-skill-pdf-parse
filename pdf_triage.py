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
    # 转曲文档的残留文本常是无 CJK 的水印串（长度可能过百），先判矢量再看字数
    thin = a["cjk"] < MIN_CJK and a["chars"] < 400
    if thin and a["drawings"] > 300:
        return "VECTOR_OUTLINED"
    if thin and a["images"] and a["chars"] < MIN_CHARS:
        return "SCANNED"
    if a["chars"] >= MIN_CHARS:
        return "TEXT_OK" if not thin else "TEXT_SUSPECT"
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


def render(doc, outdir, dpi, max_width, pages):
    out = []
    for i in pages:
        page = doc[i]
        d = dpi
        # 控制像素宽度，避免图过大拖慢视觉读取
        if max_width:
            w = page.rect.width * d / 72
            if w > max_width:
                d = max(72, int(d * max_width / w))
        f = outdir / f"p{i + 1}.png"
        page.get_pixmap(dpi=d).save(f)
        out.append(f)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--max-width", type=int, default=1600)
    ap.add_argument("--outdir")
    ap.add_argument("--force-render", action="store_true")
    ap.add_argument("--max-pages", type=int, default=20)
    a = ap.parse_args()

    path = Path(a.pdf).expanduser()
    if not path.exists():
        sys.exit(f"文件不存在：{path}")

    try:
        doc = fitz.open(path)
    except Exception as e:
        sys.exit(f"打不开 PDF：{e}")

    if doc.needs_pass and not doc.authenticate(""):
        print("VERDICT: ENCRYPTED")
        print("HINT:", VERDICT_HINT["ENCRYPTED"])
        return

    n = min(doc.page_count, a.max_pages)
    stats = [analyze(doc[i]) for i in range(n)]
    verdicts = [verdict_of(s) for s in stats]
    # 全篇结论取最常见页级结论；只要有一页文本可用就不轻易判死
    overall = "TEXT_OK" if verdicts.count("TEXT_OK") * 2 >= n else Counter(verdicts).most_common(1)[0][0]
    if a.force_render:
        overall = "TEXT_BAD"

    print(f"FILE: {path}")
    print(f"PAGES: {doc.page_count} (analyzed {n})")
    print(f"VERDICT: {overall}")
    print(f"HINT: {VERDICT_HINT[overall]}")
    print(f"STATS: " + " | ".join(
        f"p{i+1} chars={s['chars']} cjk={s['cjk']} junk={s['junk']} draw={s['drawings']} img={s['images']} wm={s['wm']}"
        for i, s in enumerate(stats)))

    if overall in ("TEXT_OK", "TEXT_SUSPECT"):
        print("\n--- TEXT (水印行已剔除) ---")
        for i, s in enumerate(stats):
            print(f"\n===== PAGE {i + 1} =====\n{s['body']}")

    if overall != "TEXT_OK":
        outdir = writable_outdir(a.outdir, path.stem[:40])
        files = render(doc, outdir, a.dpi, a.max_width, range(n))
        print("\n--- IMAGES (用 Read 工具读取这些路径) ---")
        for f in files:
            print(f)
        if doc.page_count > n:
            print(f"NOTE: 仅渲染前 {n} 页，其余用 --max-pages 调整")


if __name__ == "__main__":
    main()
