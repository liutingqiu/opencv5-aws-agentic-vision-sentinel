"""Render the technical report to a print-ready HTML for CDP printToPDF."""

from __future__ import annotations

import pathlib
import sys

import markdown

md_path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "docs/technical-report.md")
out_path = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "docs/technical-report.html")
body = markdown.markdown(md_path.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])

CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: "Segoe UI", system-ui, sans-serif; font-size: 10.5pt; line-height: 1.55; color: #14181d; }
h1 { font-size: 22pt; margin: 0 0 6pt; letter-spacing: -.02em; }
h2 { font-size: 13pt; margin: 20pt 0 6pt; border-bottom: 1.5px solid #12b0e8; padding-bottom: 3pt; }
h3 { font-size: 11pt; margin: 14pt 0 4pt; }
p { margin: 6pt 0; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #eef3f7; padding: 1px 3px; border-radius: 3px; }
pre { background: #0d1724; color: #dbe7f2; padding: 9pt 11pt; border-radius: 5px; font-size: 8.6pt; overflow: visible; white-space: pre-wrap; }
pre code { background: none; color: inherit; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; font-size: 9.5pt; }
th, td { border: 1px solid #c9d4de; padding: 4pt 7pt; text-align: left; }
th { background: #eef3f7; }
blockquote { border-left: 3px solid #12b0e8; margin: 8pt 0; padding: 2pt 10pt; color: #45596b; }
strong { color: #0b1622; }
li { margin: 3pt 0; }
"""

html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>"""
out_path.write_text(html, encoding="utf-8")
print("wrote", out_path, len(html))
