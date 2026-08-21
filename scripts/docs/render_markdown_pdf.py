#!/usr/bin/env python3
"""Render a Markdown guide to self-contained, print-oriented HTML."""

from __future__ import annotations

import argparse
import html
import pathlib
import re
import unicodedata

from markdown_it import MarkdownIt


def slugify(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", "", value))
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value or "section"


def add_heading_ids_and_toc(document: str) -> tuple[str, str]:
    headings: list[tuple[int, str, str]] = []
    used: dict[str, int] = {}

    def replace(match: re.Match[str]) -> str:
        level = int(match.group(1))
        body = match.group(2)
        label = html.unescape(re.sub(r"<[^>]+>", "", body)).strip()
        base = slugify(label)
        used[base] = used.get(base, 0) + 1
        anchor = base if used[base] == 1 else f"{base}-{used[base]}"
        if level in (2, 3):
            headings.append((level, label, anchor))
        return f'<h{level} id="{anchor}">{body}</h{level}>'

    document = re.sub(r"<h([1-6])>(.*?)</h\1>", replace, document, flags=re.S)
    items = []
    for level, label, anchor in headings:
        class_name = "toc-section" if level == 2 else "toc-subsection"
        items.append(
            f'<li class="{class_name}"><a href="#{anchor}">{html.escape(label)}</a></li>'
        )
    return document, "\n".join(items)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args()

    markdown_text = args.source.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", markdown_text, flags=re.M)
    title = title_match.group(1).strip() if title_match else args.source.stem
    markdown_text = re.sub(r"^#\s+.+\n", "", markdown_text, count=1, flags=re.M)

    renderer = MarkdownIt("commonmark", {"html": True, "typographer": True})
    renderer.enable("table")
    content, toc = add_heading_ids_and_toc(renderer.render(markdown_text))

    template = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  @page { size: A4; margin: 17mm 15mm 18mm 18mm; }
  * { box-sizing: border-box; }
  body {
    color: #172033;
    font-family: "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 9.4pt;
    line-height: 1.45;
    margin: 0;
  }
  .cover {
    min-height: 247mm;
    display: flex;
    flex-direction: column;
    justify-content: center;
    page-break-after: always;
    border-left: 9px solid #2457d6;
    padding: 0 16mm;
  }
  .cover .eyebrow {
    color: #2457d6;
    font-size: 11pt;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
  }
  .cover h1 {
    color: #111827;
    font-size: 28pt;
    line-height: 1.15;
    margin: 7mm 0 5mm;
  }
  .cover .subtitle { color: #475569; font-size: 13pt; max-width: 145mm; }
  .cover .meta { color: #64748b; margin-top: 20mm; }
  .toc { page-break-after: always; }
  .toc h1 { color: #173b91; font-size: 22pt; }
  .toc ol { list-style: none; padding-left: 0; columns: 2; column-gap: 10mm; }
  .toc li { break-inside: avoid; margin: 0 0 2.2mm; }
  .toc .toc-subsection { padding-left: 4mm; font-size: 8.5pt; }
  .toc a { color: #1e3a8a; text-decoration: none; }
  h2, h3, h4 { break-after: avoid; page-break-after: avoid; }
  h2 {
    color: #173b91;
    font-size: 16pt;
    border-bottom: 1px solid #b9c8ec;
    padding-bottom: 2mm;
    margin: 8mm 0 3mm;
  }
  h3 { color: #244b9b; font-size: 12.5pt; margin: 6mm 0 2mm; }
  h4 { color: #334155; font-size: 10.5pt; }
  p { margin: 0 0 3mm; }
  ul, ol { margin: 1.5mm 0 3.5mm; padding-left: 6mm; }
  li { margin-bottom: .9mm; }
  blockquote {
    background: #eef4ff;
    border-left: 4px solid #4d72d8;
    margin: 3mm 0 5mm;
    padding: 3mm 4mm;
  }
  blockquote p { margin: 0; }
  table {
    border-collapse: collapse;
    font-size: 8.1pt;
    margin: 3mm 0 5mm;
    width: 100%;
  }
  tr { break-inside: avoid; page-break-inside: avoid; }
  th, td { border: 1px solid #cbd5e1; padding: 1.8mm 2mm; vertical-align: top; }
  th { background: #e8eefc; color: #173b91; text-align: left; }
  tr:nth-child(even) td { background: #f8fafc; }
  code {
    background: #eef2f7;
    border-radius: 2px;
    font-family: "Noto Mono", "DejaVu Sans Mono", monospace;
    font-size: 8.2pt;
    padding: .2mm .7mm;
  }
  pre {
    background: #111827;
    border-radius: 4px;
    color: #f8fafc;
    font-size: 7.7pt;
    line-height: 1.35;
    overflow-wrap: anywhere;
    padding: 3mm;
    white-space: pre-wrap;
    break-inside: avoid;
  }
  pre code { background: transparent; color: inherit; padding: 0; }
  a { color: #2457d6; overflow-wrap: anywhere; }
  strong { color: #111827; }
  .footer-note {
    border-top: 1px solid #cbd5e1;
    color: #64748b;
    font-size: 7.5pt;
    margin-top: 10mm;
    padding-top: 2mm;
  }
</style>
</head>
<body>
  <section class="cover">
    <div class="eyebrow">Cruzr S2 · VLA · Teleoperación</div>
    <h1>__TITLE__</h1>
    <div class="subtitle">Compatibilidad v0.2.0, PICO 4 Ultra Enterprise, captura de demostraciones, diseño de datasets y estrategia de entrenamiento.</div>
    <div class="meta">Versión documental 1.1<br>21 de agosto de 2026</div>
  </section>
  <nav class="toc">
    <h1>Contenido</h1>
    <ol>__TOC__</ol>
  </nav>
  <main>__CONTENT__</main>
  <div class="footer-note">Documento técnico del proyecto. Los elementos marcados como Pendiente DSA requieren confirmación del proveedor.</div>
</body>
</html>
"""
    output = (
        template.replace("__TITLE__", html.escape(title))
        .replace("__TOC__", toc)
        .replace("__CONTENT__", content)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
