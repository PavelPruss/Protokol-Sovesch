# Transcription Light Tests

## What audio format to upload
Use one of these formats:
- `.m4a` (recommended for Zoom audio)
- `.mp3`
- `.wav`
- `.mp4` (if audio is inside video)

## Recommended upload rules
- Preferred: one file per meeting (`.m4a` from Zoom).
- Max file size for first MVP tests: up to `200 MB`.
- If file is larger: split into parts of `15-30` minutes.
- File naming example:
  - `2026-05-08_owner-meeting_part1.m4a`
  - `2026-05-08_owner-meeting_part2.m4a`

## 3 light tests (fast start)

### Test 1: Basic transcription quality
Goal: check if speech turns into readable text.
- Input: 10-15 minutes audio.
- Expected result:
  - no major gaps in transcript,
  - minimal random symbols/noise,
  - understandable sentence flow.

### Test 2: Business entities
Goal: check names, terms, and numbers.
- Input: audio with:
  - participant names,
  - project names,
  - dates/numbers/budgets.
- Expected result:
  - at least 80% of key names/terms recognized correctly.

### Test 3: Cost and speed
Goal: choose practical model.
- Run same audio through 2-3 model options.
- Track:
  - processing time,
  - estimated token/cost usage,
  - final readability score (1-5).
- Expected result:
  - one "best value" option selected for MVP.

## Fallback for difficult fragments
If AI transcript has low confidence in a fragment:
- review that segment manually in Express Scribe,
- correct only problematic blocks,
- keep the rest AI-generated.

## MVP acceptance criteria
- Transcript generated for files up to 2 hours total.
- Action items can be extracted from transcript.
- Draft protocol can be assembled from extracted content.
