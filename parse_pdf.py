#!/usr/bin/env python3
import subprocess
import sys
import os

def check_python_version():
    major, minor = sys.version_info.major, sys.version_info.minor
    if (major, minor) < (3, 10):
        print(
            f"错误：当前 Python 版本为 {major}.{minor}，marker-pdf 要求 Python 3.10+\n"
            f"请升级 Python：https://www.python.org/downloads/\n"
            f"macOS 推荐：brew install python@3.12",
            file=sys.stderr
        )
        sys.exit(1)

def ensure_marker():
    try:
        from marker.converters.pdf import PdfConverter
        return True
    except ImportError:
        print("正在安装 marker-pdf（首次安装包含 PyTorch，体积较大，请耐心等待）...", file=sys.stderr)
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "marker-pdf", "-q"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"安装失败:\n{result.stderr}", file=sys.stderr)
            return False
        print("marker-pdf 安装完成", file=sys.stderr)
        return True

def parse_pdf(pdf_path):
    pdf_path = os.path.expanduser(pdf_path)

    if not os.path.exists(pdf_path):
        print(f"错误：文件不存在: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    if not ensure_marker():
        print("请手动运行: pip install marker-pdf", file=sys.stderr)
        sys.exit(1)

    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered

    print("正在加载模型（首次运行需下载模型文件，约数百 MB，请耐心等待）...", file=sys.stderr)
    converter = PdfConverter(artifact_dict=create_model_dict())

    print(f"正在解析: {pdf_path}", file=sys.stderr)
    rendered = converter(pdf_path)
    markdown, _, _ = text_from_rendered(rendered)

    print(markdown)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: parse_pdf.py <pdf_path>", file=sys.stderr)
        sys.exit(1)
    check_python_version()
    parse_pdf(sys.argv[1])
