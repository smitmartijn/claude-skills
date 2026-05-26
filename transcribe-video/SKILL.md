---
name: transcribe-video
description: Transcribe a video or audio file to a plain-text .txt file. Use when the user says "transcribe this", "make a transcript", "get the text from this video", "what was said in this", or any variant of "give me the transcription". Fast (hardware decode + whisper) — runs in seconds on M-series Macs.
---

# Transcribe Video

Produce a plain-text transcript of a video or audio file. Outputs a `.txt` next to the source. Optional: also emit `.srt`/`.vtt`/`.json` if the user asks for timestamps.

## Prerequisites

Before running any commands, verify both dependencies are installed:

```bash
command -v ffmpeg >/dev/null || { echo "ffmpeg not found"; exit 1; }
command -v whisper >/dev/null || { echo "whisper not found"; exit 1; }
```

If missing, guide the user:
- **ffmpeg**: `brew install ffmpeg` (macOS) / `sudo apt install ffmpeg` (Ubuntu/Debian)
- **whisper**: `pip install openai-whisper`

## Inputs

- Media file path (the user will provide; otherwise ask). Video or audio.
- Optional: `--model` override. Default `tiny.en` for English, `base` otherwise.
- Optional: `--language` (auto-detect if omitted; non-English forces a non-`.en` model).
- Optional: `--with-timestamps` to also emit `.srt` (segment-level) alongside the `.txt`.

## Working directory

`./tmp/<basename>/` — mkdir at start, leave artifacts for debugging.

---

## Step 1 — Extract audio

Whisper only needs mono 16 kHz audio. Hardware-decode the source to skip a slow HEVC software pass.

**macOS (Apple Silicon):**
```bash
ffmpeg -y -hwaccel videotoolbox -i "$SRC" \
  -vn -ac 1 -ar 16000 \
  ./tmp/$NAME/audio.wav
```

**Linux / other platforms:**
```bash
ffmpeg -y -i "$SRC" \
  -vn -ac 1 -ar 16000 \
  ./tmp/$NAME/audio.wav
```

To detect the platform: `[[ "$(uname)" == "Darwin" ]] && HWACCEL="-hwaccel videotoolbox" || HWACCEL=""`

**Critical flags:**

- `-hwaccel videotoolbox` (macOS only) — hardware-decodes HEVC/H.264, ~5–10× faster on Apple Silicon. Omit on Linux/Windows.
- `-vn` — skip the video stream entirely; we only need audio.
- `-ac 1 -ar 16000` — mono 16 kHz is what whisper resamples to anyway; doing it in ffmpeg is faster than letting whisper do it.

If the source is already audio (`.wav`, `.mp3`, `.m4a`, `.flac`), still run this — it normalizes the format and gives whisper a clean input.

## Step 2 — Transcribe with whisper

```bash
whisper ./tmp/$NAME/audio.wav \
  --model tiny.en \
  --output_format txt \
  --output_dir ./tmp/$NAME \
  --language en
```

**Model picker:**

- `tiny.en` — default for English. Fastest, quality fine for clear speech (tutorials, podcasts, voice-overs).
- `base.en` — bump up if `tiny.en` produces noticeable errors (proper nouns, technical terms).
- `small.en` / `medium.en` — only if the user explicitly asks for higher accuracy and accepts longer wait.
- `turbo` — best quality-to-speed ratio for any language. Use when `tiny.en` quality isn't good enough but the user hasn't asked for a specific model.
- `base` (no `.en`) — non-English or mixed-language. Drop `--language en`.

**Output format picker:**

- Plain `.txt` is the default — just the spoken words, one paragraph per whisper segment, no timestamps. This is what most users want.
- If the user asked for timestamps, use `--output_format all` to emit every format (`.txt`, `.srt`, `.vtt`, `.json`, `.tsv`). The user gets their `.txt` plus whichever timestamp format they need.
- If the user asked for a specific format only (e.g. just `.srt`), use `--output_format srt`.

Whisper writes `audio.txt` (and `audio.srt`/`audio.vtt`/`audio.json` if requested) into `--output_dir`.

## Step 3 — Deliver

- Copy `audio.txt` to `<source_dir>/<source_basename>.txt` (and `.srt`/`.vtt` if produced).
- Print one line: source path → output path, word count, runtime.
- Don't auto-open the file — it's plain text, the user can `cat` or open it themselves. Just report the path.

---

## Pitfalls — don't repeat these

- **Don't use `-hwaccel videotoolbox` on Linux.** It's macOS-only. Check `uname` first.
- **Don't skip `-hwaccel videotoolbox` on macOS.** Software HEVC decode on a 4K source takes minutes; with the flag, seconds.
- **Don't feed whisper the raw video file.** It works, but ffmpeg's resampling step is much faster than whisper's internal one — and you'd lose `-hwaccel`. Always extract `audio.wav` first.
- **Don't default to `small.en` or larger.** `tiny.en` is fine for English voice-overs, tutorials, podcasts. Only escalate if the user reports errors or asks for better quality.
- **Don't pass `--word_timestamps True` unless the user asked for word-level timing.** It roughly doubles whisper's runtime.
- **Don't write the txt to `./tmp` and stop.** Always deliver alongside the source file so the user can find it.
- **Don't strip whisper's paragraph breaks.** The default `.txt` output already segments sensibly — leave it alone unless the user asks for a single blob.

Keep this skill focused on one thing: produce a plain-text transcript from a media file, fast.
