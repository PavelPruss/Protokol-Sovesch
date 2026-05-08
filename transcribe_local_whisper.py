#!/usr/bin/env python3
from __future__ import annotations

import pathlib
from typing import Optional, Tuple

_MODEL_CACHE = {}


def _get_model(model_size: str, device: str, compute_type: str):
    key = (model_size, device, compute_type)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]

    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    _MODEL_CACHE[key] = model
    return model


def transcribe_file_local(
    file_path: pathlib.Path,
    model_size: str = "base",
    language: Optional[str] = None,
    device: str = "cpu",
    compute_type: str = "int8",
) -> Tuple[str, str]:
    """
    Returns:
      (transcript_text, detected_language)
    """
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Не установлен faster-whisper. Установите: pip install faster-whisper"
        ) from exc

    model = _get_model(model_size, device, compute_type)
    segments, info = model.transcribe(
        str(file_path),
        language=language,
        vad_filter=True,
        condition_on_previous_text=False,
    )

    lines = []
    for seg in segments:
        text = (seg.text or "").strip()
        if text:
            lines.append(text)

    transcript = " ".join(lines).strip()
    if not transcript:
        raise RuntimeError("Локальная транскрибация вернула пустой текст.")

    detected_language = getattr(info, "language", "unknown") or "unknown"
    return transcript, detected_language
