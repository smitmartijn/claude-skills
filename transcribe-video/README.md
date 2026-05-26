# transcribe-video

A Claude Code skill that transcribes video and audio files to plain text using ffmpeg and OpenAI Whisper.

## What it does

Give Claude a video or audio file and say "transcribe this." It extracts the audio with hardware-accelerated ffmpeg, runs Whisper, and drops a `.txt` file next to your source. Optionally produces `.srt`, `.vtt`, or `.json` for timestamps.

## Prerequisites

| Dependency | Install |
|------------|---------|
| [ffmpeg](https://ffmpeg.org/) | `brew install ffmpeg` (macOS) / `sudo apt install ffmpeg` (Linux) |
| [openai-whisper](https://github.com/openai/whisper) | `pip install openai-whisper` |

Apple Silicon Macs get hardware-accelerated video decoding via VideoToolbox automatically. On Linux, the skill falls back to software decoding.

## Install

```bash
curl -sL https://raw.githubusercontent.com/smitmartijn/claude-skills/main/install.sh | bash -s -- transcribe-video
```

Or manually copy `SKILL.md` to `~/.claude/skills/transcribe-video/SKILL.md`.

## Usage

In Claude Code, just say:

- "transcribe this video" (then provide the path)
- "make a transcript of recording.mp4"
- "what was said in this?" (with a video/audio file)
- "transcribe this with timestamps" (produces `.srt`/`.vtt` alongside `.txt`)

### Options

| Option | Effect |
|--------|--------|
| Default | `tiny.en` model, plain `.txt` output |
| "use a better model" | Bumps to `turbo` or `base.en` |
| "with timestamps" | Adds `.srt`/`.vtt`/`.json` output |
| "it's in French" | Switches to multilingual model, auto-detects language |

## Supported formats

Any format ffmpeg can decode — `.mp4`, `.mov`, `.mkv`, `.webm`, `.avi`, `.mp3`, `.m4a`, `.wav`, `.flac`, `.ogg`, and more.

## How it works

1. **Extract audio** — ffmpeg decodes the source to mono 16 kHz WAV (hardware-accelerated on macOS)
2. **Transcribe** — Whisper processes the WAV and writes the transcript
3. **Deliver** — output file placed next to the source, path reported to user
