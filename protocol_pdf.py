#!/usr/bin/env python3
from __future__ import annotations

import pathlib
from typing import List

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def _pick_font_candidates() -> List[pathlib.Path]:
    return [
        pathlib.Path("C:/Windows/Fonts/arial.ttf"),
        pathlib.Path("C:/Windows/Fonts/calibri.ttf"),
        pathlib.Path("C:/Windows/Fonts/tahoma.ttf"),
        pathlib.Path("C:/Windows/Fonts/segoeui.ttf"),
    ]


def _register_font() -> str:
    for font_path in _pick_font_candidates():
        if font_path.exists():
            font_name = f"custom_{font_path.stem.lower()}"
            try:
                pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
                return font_name
            except Exception:
                continue
    return "Helvetica"


def save_protocol_pdf(protocol_text: str, out_file: pathlib.Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    font_name = _register_font()

    page_width, page_height = A4
    left = 40
    right = 40
    top = 42
    bottom = 42
    line_height = 15
    usable_width = page_width - left - right
    max_chars = max(40, int(usable_width / 7.0))

    c = canvas.Canvas(str(out_file), pagesize=A4)
    c.setTitle("Protocol")
    c.setFont(font_name, 11)
    y = page_height - top

    def new_page() -> None:
        nonlocal y
        c.showPage()
        c.setFont(font_name, 11)
        y = page_height - top

    for raw_line in protocol_text.splitlines():
        line = raw_line.rstrip()
        if not line:
            y -= line_height
            if y < bottom:
                new_page()
            continue

        chunks = [line[i : i + max_chars] for i in range(0, len(line), max_chars)]
        for chunk in chunks:
            c.drawString(left, y, chunk)
            y -= line_height
            if y < bottom:
                new_page()

    c.save()
