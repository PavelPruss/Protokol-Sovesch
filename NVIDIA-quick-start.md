# NVIDIA transcription quick start

## What this script does
`transcribe_nvidia.py` takes conference files (audio/video), sends them to NVIDIA model via OpenRouter, and saves plain text transcripts.

## Supported input formats
- Audio: `.m4a`, `.mp3`, `.wav`, `.aac`, `.ogg`, `.flac`, `.aiff`
- Video: `.mp4`, `.mov`, `.webm`, `.mkv`, `.avi`

## One-time check
Make sure `.env` has:
- `OPENROUTER_API_KEY=...`
- `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
- `OPENROUTER_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`

## Run
Single file:
`python transcribe_nvidia.py --file "sample-test.wav"`

Multiple files:
`python transcribe_nvidia.py --file "part1.m4a" --file "part2.mp4"`

## Where output appears
Transcripts are saved to:
- `outputs/<file_name>.transcript.txt`

## Notes for long meetings
- For long recordings, better split into 15-30 minute chunks.
- If one chunk fails, others still continue.
