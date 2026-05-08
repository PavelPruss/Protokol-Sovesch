#!/usr/bin/env python3
from __future__ import annotations

import pathlib

from transcribe_nvidia import call_openrouter, read_api_config


DEFAULT_PROTOCOL_MODEL = "nvidia/nemotron-nano-9b-v2:free"
MAX_TRANSCRIPT_CHARS = 120000


def _build_protocol_prompt(transcript_text: str) -> str:
    trimmed = transcript_text.strip()
    if len(trimmed) > MAX_TRANSCRIPT_CHARS:
        trimmed = trimmed[:MAX_TRANSCRIPT_CHARS]

    return (
        "Ты помощник руководителя IT-проектов. "
        "На основе расшифровки совещания сформируй деловой протокол на русском языке.\n\n"
        "Важно:\n"
        "1) Пиши только проверяемые факты из текста, без выдумок.\n"
        "2) Если данных недостаточно, явно укажи 'не указано'.\n"
        "3) Для каждой договоренности/задачи обязательно укажи поле 'Зачем'.\n"
        "4) Сформируй ответ строго в markdown-структуре ниже.\n\n"
        "5) Не показывай внутренние размышления и технические комментарии.\n\n"
        "Структура протокола:\n"
        "## Общая информация\n"
        "- Дата/время: ...\n"
        "- Участники: ...\n"
        "- Тема: ...\n\n"
        "## Краткие итоги\n"
        "- ...\n\n"
        "## Принятые решения\n"
        "- ...\n\n"
        "## Договоренности и задачи\n"
        "1. Задача: ...\n"
        "   Зачем: ...\n"
        "   Ответственный: ...\n"
        "   Срок: ...\n"
        "   Статус: Новая\n\n"
        "## Открытые вопросы\n"
        "- ...\n\n"
        "## Риски и блокеры\n"
        "- ...\n\n"
        "## Следующие шаги\n"
        "- ...\n\n"
        "Расшифровка совещания:\n"
        f"{trimmed}"
    )


def _extract_protocol_content(response_json: dict) -> str:
    choices = response_json.get("choices") or []
    if not choices:
        return ""
    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    return ""


def _sanitize_protocol(text: str) -> str:
    cleaned = text.strip()
    marker = "## Общая информация"
    idx = cleaned.find(marker)
    if idx >= 0:
        cleaned = cleaned[idx:]
    return cleaned.strip()


def build_protocol_from_transcript(transcript_text: str, env_file: pathlib.Path) -> str:
    cfg = read_api_config(env_file)
    if not cfg["api_key"]:
        raise RuntimeError("OPENROUTER_API_KEY не найден в .env")

    model = DEFAULT_PROTOCOL_MODEL
    prompt = _build_protocol_prompt(transcript_text)
    parts = [{"type": "text", "text": prompt}]

    response_json = call_openrouter(
        cfg["base_url"],
        cfg["api_key"],
        model,
        parts,
        extra_payload={"temperature": 0.1},
    )
    protocol_text = _sanitize_protocol(_extract_protocol_content(response_json))
    if not protocol_text:
        raise RuntimeError("Модель вернула пустой текст протокола.")
    return protocol_text
