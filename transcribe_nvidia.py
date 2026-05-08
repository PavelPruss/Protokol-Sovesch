#!/usr/bin/env python3
"""
Small local CLI for conference transcription via NVIDIA model on OpenRouter.

Usage examples:
  python transcribe_nvidia.py --file meeting.m4a
  python transcribe_nvidia.py --file part1.m4a --file part2.mp4
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import pathlib
import sys
import urllib.error
import urllib.request
from typing import Dict, List, Optional


DEFAULT_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

AUDIO_FORMATS: Dict[str, str] = {
    ".wav": "wav",
    ".mp3": "mp3",
    ".aiff": "aiff",
    ".aac": "aac",
    ".ogg": "ogg",
    ".flac": "flac",
    ".m4a": "m4a",
}

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}


def load_env(path: pathlib.Path) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if not path.exists():
        return result

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def read_api_config(env_file: pathlib.Path) -> Dict[str, str]:
    file_env = load_env(env_file)

    api_key = os.environ.get("OPENROUTER_API_KEY", file_env.get("OPENROUTER_API_KEY", ""))
    base_url = os.environ.get("OPENROUTER_BASE_URL", file_env.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))
    model = os.environ.get("OPENROUTER_MODEL", file_env.get("OPENROUTER_MODEL", DEFAULT_MODEL))

    return {"api_key": api_key, "base_url": base_url.rstrip("/"), "model": model}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe conference files via NVIDIA on OpenRouter.")
    parser.add_argument("--file", action="append", required=True, help="Path to audio/video file. Can be used multiple times.")
    parser.add_argument("--env-file", default=".env", help="Path to .env file (default: .env).")
    parser.add_argument("--out-dir", default="outputs", help="Directory for transcript txt files.")
    parser.add_argument("--model", default=None, help="Override model id.")
    parser.add_argument(
        "--prompt",
        default=(
            "Сделай точную транскрибацию аудио/видео. Верни только чистый текст речи, "
            "без пояснений, без markdown, сохрани смысл и последовательность реплик."
        ),
        help="Instruction prompt for transcription.",
    )
    return parser.parse_args()


def detect_kind(file_path: pathlib.Path) -> str:
    ext = file_path.suffix.lower()
    if ext in AUDIO_FORMATS:
        return "audio"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return "unknown"


def build_content(file_path: pathlib.Path, prompt: str) -> List[dict]:
    ext = file_path.suffix.lower()
    raw_bytes = file_path.read_bytes()
    b64 = base64.b64encode(raw_bytes).decode("ascii")

    parts: List[dict] = [{"type": "text", "text": prompt}]

    if ext in AUDIO_FORMATS:
        parts.append(
            {
                "type": "input_audio",
                "input_audio": {
                    "data": b64,
                    "format": AUDIO_FORMATS[ext],
                },
            }
        )
        return parts

    if ext in VIDEO_EXTENSIONS:
        mime_type = mimetypes.guess_type(str(file_path))[0] or "video/mp4"
        parts.append(
            {
                "type": "video_url",
                "video_url": {
                    "url": f"data:{mime_type};base64,{b64}",
                },
            }
        )
        return parts

    raise ValueError(
        f"Unsupported extension: {ext}. Supported audio: {', '.join(sorted(AUDIO_FORMATS.keys()))}; "
        f"video: {', '.join(sorted(VIDEO_EXTENSIONS))}."
    )


def call_openrouter(
    base_url: str,
    api_key: str,
    model: str,
    content_parts: List[dict],
    extra_payload: Optional[Dict[str, object]] = None,
) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content_parts}],
        "max_tokens": 4000,
        "temperature": 0,
    }
    if extra_payload:
        payload.update(extra_payload)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        url=f"{base_url}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc


def extract_text(response_json: dict) -> str:
    choices = response_json.get("choices") or []
    if not choices:
        return ""

    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()

    # Fallback for reasoning-only responses.
    reasoning = message.get("reasoning")
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning.strip()

    return ""


def main() -> int:
    args = parse_args()
    env_file = pathlib.Path(args.env_file)
    cfg = read_api_config(env_file)

    if not cfg["api_key"]:
        print("ERROR: OPENROUTER_API_KEY is empty. Fill it in .env or environment variables.")
        return 1

    model = args.model or cfg["model"] or DEFAULT_MODEL
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Using model: {model}")
    print(f"Output dir: {out_dir.resolve()}")

    exit_code = 0
    for raw_path in args.file:
        file_path = pathlib.Path(raw_path)
        if not file_path.exists():
            print(f"[FAIL] File not found: {file_path}")
            exit_code = 1
            continue

        kind = detect_kind(file_path)
        if kind == "unknown":
            print(f"[FAIL] Unsupported file type: {file_path.name}")
            exit_code = 1
            continue

        print(f"[START] {file_path.name} ({kind})")
        try:
            content_parts = build_content(file_path, args.prompt)
            resp = call_openrouter(cfg["base_url"], cfg["api_key"], model, content_parts)
            transcript = extract_text(resp)
            if not transcript:
                raise RuntimeError("Empty transcript in model response.")

            out_file = out_dir / f"{file_path.stem}.transcript.txt"
            out_file.write_text(transcript, encoding="utf-8")
            print(f"[OK] Saved transcript: {out_file}")
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[FAIL] {file_path.name}: {exc}")
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
