#!/usr/bin/env python3
from __future__ import annotations

import warnings

# Keep terminal output clean on Python 3.12+ (cgi is still functional here).
warnings.filterwarnings("ignore", category=DeprecationWarning, module="cgi")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*cgi.*deprecated.*")

import cgi
import html
import os
import pathlib
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from protocol_builder import build_protocol_from_transcript
from protocol_pdf import save_protocol_pdf
from transcribe_local_whisper import transcribe_file_local


HOST = "127.0.0.1"
PORT = 8090
OUT_DIR = pathlib.Path("outputs")
ENV_FILE = pathlib.Path(".env")
# Reduce noisy Windows cache warning from huggingface_hub.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

def _load_simple_env(path: pathlib.Path) -> dict:
    result = {}
    if not path.exists():
        return result
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


_ENV = _load_simple_env(pathlib.Path(".env"))
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", _ENV.get("WHISPER_MODEL_SIZE", "base"))
WHISPER_LANGUAGE = os.environ.get("WHISPER_LANGUAGE", _ENV.get("WHISPER_LANGUAGE", "auto"))
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", _ENV.get("WHISPER_DEVICE", "cpu"))
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", _ENV.get("WHISPER_COMPUTE_TYPE", "int8"))


def _resolve_output_dir(output_dir_raw: str) -> pathlib.Path:
    trimmed = (output_dir_raw or "").strip()
    if not trimmed:
        return OUT_DIR
    p = pathlib.Path(trimmed)
    return p if p.is_absolute() else pathlib.Path.cwd() / p


def render_page(
    message: str = "",
    transcript: str = "",
    protocol_text: str = "",
    output_dir_value: str = "outputs",
    protocol_download_url: str = "",
) -> str:
    safe_message = html.escape(message)
    safe_transcript = html.escape(transcript)
    safe_protocol = html.escape(protocol_text)
    safe_output_dir = html.escape(output_dir_value)
    safe_download_url = html.escape(protocol_download_url)
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Protokol Sovesch | Local Whisper</title>
  <style>
    :root {{
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #1a2233;
      --muted: #5c6780;
      --line: #dfe6f3;
      --primary: #3d66f5;
      --primary-2: #6b89ff;
      --ok-bg: #eef5ff;
      --ok-line: #cfe0ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--text);
      background: radial-gradient(circle at 0% 0%, #edf2ff 0, #f8faff 30%, var(--bg) 80%);
    }}
    .page {{
      width: min(1080px, 92vw);
      margin: 28px auto 40px;
    }}
    .hero {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 14px;
    }}
    .hero h1 {{
      margin: 0;
      font-size: 28px;
      letter-spacing: 0.2px;
    }}
    .badge {{
      border: 1px solid var(--line);
      background: #fff;
      color: var(--muted);
      border-radius: 999px;
      padding: 6px 12px;
      font-size: 12px;
      font-weight: 600;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 18px;
      background: var(--card);
      box-shadow: 0 10px 28px rgba(44, 66, 120, 0.08);
    }}
    .upload-title {{
      margin: 0 0 10px;
      font-size: 18px;
      font-weight: 700;
    }}
    .file-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }}
    input[type="file"], input[type="text"] {{
      flex: 1 1 420px;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 9px;
      background: #fff;
    }}
    button {{
      border: 0;
      border-radius: 10px;
      background: linear-gradient(90deg, var(--primary), var(--primary-2));
      color: #fff;
      font-weight: 600;
      padding: 11px 16px;
      cursor: pointer;
      transition: transform 0.08s ease, opacity 0.2s ease;
    }}
    button:hover {{ transform: translateY(-1px); }}
    button:disabled {{ opacity: 0.85; cursor: wait; }}
    .help-grid {{
      margin-top: 12px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 8px;
    }}
    .help-item {{
      border: 1px solid var(--line);
      background: #fafcff;
      border-radius: 10px;
      padding: 8px 10px;
      color: var(--muted);
      font-size: 12.5px;
    }}
    .msg {{
      margin-top: 14px;
      padding: 12px;
      background: var(--ok-bg);
      border: 1px solid var(--ok-line);
      border-radius: 10px;
      line-height: 1.45;
    }}
    .status {{
      display: none;
      margin-top: 12px;
      padding: 10px;
      border-radius: 10px;
      background: #f3f8ff;
      border: 1px solid #dbe8ff;
    }}
    .status-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 6px;
    }}
    .percent {{
      font-size: 12px;
      font-weight: 700;
      color: #2f5df4;
      min-width: 42px;
      text-align: right;
    }}
    .small {{ color: var(--muted); font-size: 12px; }}
    .bar-wrap {{ width: 100%; height: 10px; border-radius: 999px; background: #dde8ff; overflow: hidden; margin-top: 8px; }}
    .bar {{ width: 0%; height: 100%; border-radius: 999px; background: linear-gradient(90deg, #3a7afe, #6b89ff); transition: width 0.25s ease; }}
    .results {{
      margin-top: 14px;
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
    }}
    .panel h3 {{
      margin: 0 0 8px;
      font-size: 16px;
    }}
    textarea {{
      width: 100%;
      min-height: 220px;
      margin-top: 0;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      line-height: 1.5;
      resize: vertical;
      background: #fcfdff;
      color: var(--text);
    }}
  </style>
</head>
<body>
  <main class="page">
    <div class="hero">
      <h1>Protokol Sovesch</h1>
      <div class="badge">Локальная расшифровка + автопротокол</div>
    </div>
    <section class="card">
      <p class="upload-title">Загрузка файла встречи</p>
      <form id="upload-form" method="post" enctype="multipart/form-data">
        <div class="file-row">
          <input type="file" name="conference_file" required />
          <button id="submit-btn" type="submit">Транскрибировать</button>
        </div>
        <div class="file-row" style="margin-top:10px;">
          <input type="text" name="output_dir" value="{safe_output_dir}" placeholder="Папка сохранения, например: outputs или C:\\Reports\\Meetings" />
        </div>
      </form>
      <div id="progress-status" class="status">
        <div class="status-row">
          <b id="progress-label">Идет обработка файла...</b>
          <span id="progress-percent" class="percent">0%</span>
        </div>
        <span id="progress-subtext" class="small">Это может занять до нескольких минут. Обработка идет на вашем компьютере.</span>
        <div class="bar-wrap"><div class="bar"></div></div>
      </div>
      <div class="help-grid">
        <div class="help-item">Форматы: m4a, mp3, wav, aac, ogg, flac, aiff, mp4, mov, webm, mkv, avi</div>
        <div class="help-item">Режим: локальная транскрибация faster-whisper</div>
        <div class="help-item">Параметры: model={WHISPER_MODEL_SIZE}, language={WHISPER_LANGUAGE}, device={WHISPER_DEVICE}, compute={WHISPER_COMPUTE_TYPE}</div>
      </div>
      {f'<div class="msg">{safe_message}</div>' if safe_message else ""}
      {f'<div style="margin-top:10px;"><a href="{safe_download_url}" style="display:inline-block;padding:10px 14px;background:#2f5df4;color:#fff;text-decoration:none;border-radius:10px;font-weight:600;">Скачать протокол (PDF)</a></div>' if safe_download_url else ""}
      <div class="results">
        {f'<section class="panel"><h3>Транскрипт</h3><textarea readonly>{safe_transcript}</textarea></section>' if safe_transcript else ""}
        {f'<section class="panel"><h3>Черновик протокола</h3><textarea readonly>{safe_protocol}</textarea></section>' if safe_protocol else ""}
      </div>
    </section>
  </main>
  <script>
    const form = document.getElementById("upload-form");
    const statusBox = document.getElementById("progress-status");
    const submitBtn = document.getElementById("submit-btn");
    const progressBar = statusBox.querySelector(".bar");
    const progressPercent = document.getElementById("progress-percent");
    const progressLabel = document.getElementById("progress-label");
    const progressSubtext = document.getElementById("progress-subtext");
    let progressTimer = null;

    function setProgress(value, labelText, subText) {{
      const clamped = Math.max(0, Math.min(100, value));
      progressBar.style.width = clamped + "%";
      progressPercent.textContent = clamped + "%";
      if (labelText) progressLabel.textContent = labelText;
      if (subText) progressSubtext.textContent = subText;
    }}

    function startProgressSimulation() {{
      const timeline = [
        {{ limit: 18, step: 2, label: "Загрузка файла...", sub: "Получаем файл из браузера." }},
        {{ limit: 48, step: 2, label: "Распознавание речи...", sub: "Локальный faster-whisper обрабатывает запись." }},
        {{ limit: 78, step: 1, label: "Сборка протокола...", sub: "Формируем структуру итогов и договоренностей." }},
        {{ limit: 95, step: 1, label: "Подготовка файлов...", sub: "Сохраняем TXT / MD / PDF результаты." }},
      ];
      let stageIdx = 0;
      let progress = 0;

      progressTimer = setInterval(() => {{
        const stage = timeline[Math.min(stageIdx, timeline.length - 1)];
        if (progress < stage.limit) {{
          progress += stage.step;
          if (progress > stage.limit) progress = stage.limit;
          setProgress(progress, stage.label, stage.sub);
        }} else if (stageIdx < timeline.length - 1) {{
          stageIdx += 1;
        }}
      }}, 380);
    }}

    form.addEventListener("submit", () => {{
      statusBox.style.display = "block";
      submitBtn.disabled = true;
      submitBtn.textContent = "Обработка...";
      setProgress(2, "Идет обработка файла...", "Это может занять до нескольких минут. Обработка идет на вашем компьютере.");
      startProgressSimulation();
    }});

    // If page was returned with final result, show completion.
    if (document.querySelector(".msg")) {{
      if (progressTimer) clearInterval(progressTimer);
      setProgress(100, "Готово", "Обработка завершена.");
    }}
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send_html(self, content: str, status: int = HTTPStatus.OK) -> None:
        data = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/download":
            params = urllib.parse.parse_qs(parsed.query)
            file_path_raw = (params.get("file") or [""])[0]
            file_path = pathlib.Path(file_path_raw)
            if not file_path.exists() or not file_path.is_file():
                self._send_html(render_page("Файл для скачивания не найден."), status=HTTPStatus.NOT_FOUND)
                return
            data = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f'attachment; filename="{file_path.name}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self._send_html(render_page())

    def do_POST(self) -> None:  # noqa: N802
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": self.headers.get("Content-Type", "")},
        )

        uploaded = form["conference_file"] if "conference_file" in form else None
        if uploaded is None or not getattr(uploaded, "filename", ""):
            self._send_html(render_page("Не выбран файл."), status=HTTPStatus.BAD_REQUEST)
            return

        output_dir_raw = form.getvalue("output_dir", "outputs")
        target_out_dir = _resolve_output_dir(output_dir_raw)

        file_name = pathlib.Path(uploaded.filename).name
        upload_dir = pathlib.Path("uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        source_path = upload_dir / file_name
        source_path.write_bytes(uploaded.file.read())

        try:
            lang = None if WHISPER_LANGUAGE.lower() in {"", "auto", "none"} else WHISPER_LANGUAGE
            transcript, detected_lang = transcribe_file_local(
                source_path,
                model_size=WHISPER_MODEL_SIZE,
                language=lang,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )

            target_out_dir.mkdir(parents=True, exist_ok=True)
            out_file = target_out_dir / f"{source_path.stem}.transcript.txt"
            out_file.write_text(transcript, encoding="utf-8")

            protocol_text = ""
            protocol_note = ""
            protocol_download_url = ""
            try:
                protocol_text = build_protocol_from_transcript(transcript, ENV_FILE)
                protocol_file = target_out_dir / f"{source_path.stem}.protocol.md"
                protocol_file.write_text(protocol_text, encoding="utf-8")
                protocol_pdf_file = target_out_dir / f"{source_path.stem}.protocol.pdf"
                save_protocol_pdf(protocol_text, protocol_pdf_file, meeting_title=source_path.stem)
                protocol_note = f" Протокол сохранен в {protocol_file} и {protocol_pdf_file}."
                protocol_download_url = "/download?file=" + urllib.parse.quote(str(protocol_pdf_file))
            except Exception as protocol_exc:  # pylint: disable=broad-except
                protocol_note = f" Протокол не сформирован: {protocol_exc}"

            msg = (
                f"Готово. Файл обработан локально: {file_name}. "
                f"Язык: {detected_lang}. Транскрипт сохранен в {out_file}.{protocol_note}"
            )
            self._send_html(
                render_page(
                    msg,
                    transcript,
                    protocol_text,
                    output_dir_value=str(output_dir_raw),
                    protocol_download_url=protocol_download_url,
                )
            )
        except Exception as exc:  # pylint: disable=broad-except
            self._send_html(
                render_page(
                    f"Ошибка: {exc}",
                    output_dir_value=str(output_dir_raw),
                ),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )


if __name__ == "__main__":
    print(f"Starting local server on http://{HOST}:{PORT}")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()
