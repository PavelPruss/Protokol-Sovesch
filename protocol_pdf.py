#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
import pathlib
import re
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


def _derive_meeting_title(out_file: pathlib.Path) -> str:
    stem = out_file.stem
    if stem.endswith(".protocol"):
        stem = stem[: -len(".protocol")]
    stem = stem.replace("_", " ").replace("-", " ").strip()
    return stem or "Без названия"


def save_protocol_pdf(protocol_text: str, out_file: pathlib.Path, meeting_title: str | None = None) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    font_name = _register_font()

    page_width, page_height = A4
    left = 40
    right = 40
    top = 42
    bottom = 42
    line_height = 15
    usable_width = page_width - left - right
    heading_color = (0.14, 0.23, 0.52)
    text_color = (0.1, 0.13, 0.2)

    c = canvas.Canvas(str(out_file), pagesize=A4)
    c.setTitle("Protocol")
    c.setFont(font_name, 11)
    c.setFillColorRGB(*text_color)
    y = page_height - top

    def new_page() -> None:
        nonlocal y
        c.showPage()
        c.setFont(font_name, 11)
        c.setFillColorRGB(*text_color)
        y = page_height - top

    def ensure_space(required_height: float) -> None:
        nonlocal y
        if y - required_height < bottom:
            new_page()

    def wrap_line(text: str, font_size: int) -> List[str]:
        words = text.split()
        if not words:
            return [""]
        lines: List[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if pdfmetrics.stringWidth(candidate, font_name, font_size) <= usable_width:
                current = candidate
                continue
            lines.append(current)
            current = word
        lines.append(current)
        return lines

    heading_pattern = re.compile(r"^#{1,6}\s+")
    numbered_list_pattern = re.compile(r"^\d+\.\s+")
    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    final_meeting_title = (meeting_title or "").strip() or _derive_meeting_title(out_file)

    # First-page title block for faster visual orientation.
    c.setFont(font_name, 19)
    c.setFillColorRGB(*heading_color)
    c.drawString(left, y, "Протокол совещания")
    y -= 23
    c.setFont(font_name, 12)
    c.setFillColorRGB(0.22, 0.28, 0.4)
    c.drawString(left, y, f"Встреча: {final_meeting_title}")
    y -= 16
    c.setFont(font_name, 10)
    c.setFillColorRGB(0.38, 0.44, 0.58)
    c.drawString(left, y, f"Сформировано: {generated_at}")
    y -= 12
    c.setLineWidth(1.1)
    c.setStrokeColorRGB(0.75, 0.82, 0.95)
    c.line(left, y, page_width - right, y)
    y -= 16
    c.setFont(font_name, 11)
    c.setFillColorRGB(*text_color)

    for raw_line in protocol_text.splitlines():
        line = raw_line.rstrip()
        if not line:
            y -= line_height
            ensure_space(0)
            continue

        if heading_pattern.match(line):
            heading_text = heading_pattern.sub("", line).strip()
            font_size = 15 if line.startswith("## ") else 17
            wrapped_heading = wrap_line(heading_text, font_size)
            ensure_space(line_height * (len(wrapped_heading) + 1.8))
            y -= 6
            c.setFont(font_name, font_size)
            c.setFillColorRGB(*heading_color)
            for heading_line in wrapped_heading:
                c.drawString(left, y, heading_line)
                y -= line_height + 1
            c.setLineWidth(0.8)
            c.setStrokeColorRGB(0.8, 0.85, 0.96)
            c.line(left, y + 3, page_width - right, y + 3)
            y -= 9
            c.setFont(font_name, 11)
            c.setFillColorRGB(*text_color)
            continue

        indent = left
        cleaned = line
        if line.startswith("- "):
            cleaned = "• " + line[2:]
            indent = left + 8
        elif numbered_list_pattern.match(line):
            indent = left + 8

        wrapped = wrap_line(cleaned, 11)
        ensure_space(line_height * len(wrapped))
        for chunk in wrapped:
            c.drawString(indent, y, chunk)
            y -= line_height

    c.save()
