# thumbnail-video

A Claude Code skill that generates YouTube thumbnail variants from a video. Uses scene detection to pick frames, overlays text via HTML/CSS templates, and renders with headless Chrome at 1280x720.

## What it does

Give Claude a video and say "make a thumbnail." It extracts candidate frames, drafts hook text from the transcript, presents a plan for approval, then renders multiple thumbnail variants sized for YouTube's "Test & Compare" A/B testing.

## Prerequisites

| Dependency | Install |
|------------|---------|
| [ffmpeg](https://ffmpeg.org/) (includes ffprobe) | `brew install ffmpeg` (macOS) / `sudo apt install ffmpeg` (Linux) |
| [Python 3](https://python.org/) | Usually pre-installed |
| [Chrome](https://www.google.com/chrome/) or Chromium | `brew install --cask google-chrome` (macOS) |
| [transcribe-video](../transcribe-video/) skill | Installed alongside; used to generate transcript if none exists |

Templates load fonts from [Google Fonts](https://fonts.google.com/) at render time — Chrome needs network access.

## Install

```bash
curl -sL https://raw.githubusercontent.com/smitmartijn/claude-skills/main/install.sh | bash -s -- thumbnail-video
```

Or manually copy the entire `thumbnail-video/` directory to `~/.claude/skills/thumbnail-video/`.

## Usage

In Claude Code, say:

- "make a thumbnail for this video"
- "generate youtube thumbnails"
- "thumbnail for recording.mp4"

### Options

| Option | Effect |
|--------|--------|
| Default | 3 variants, mixed styles, auto-generated hook text |
| "make 5 variants" | Up to 5 variants |
| "use the bold-left style" | Locks all variants to one style |
| "use this hook: ..." | Overrides the auto-generated text |

### Workflow

1. Claude extracts ~20 candidate frames via scene detection
2. Reads the transcript (or generates one via `transcribe-video`)
3. Drafts a variant plan: style + frame + hook text per variant
4. **Asks for your approval** before rendering — you can tweak hooks, swap frames, or pick brand colors
5. Renders via headless Chrome and delivers JPEGs next to the source video

## Styles

| Style | Description | Best for |
|-------|-------------|----------|
| `bold-left` | Large text on left third, frame on right | Benefit/promise hooks |
| `face-zoom` | Full-bleed frame, big bottom text with gradient | Curiosity/question hooks, presenter shots |
| `ui-callout` | Full-bleed screenshot, corner badge, bottom band | Feature launches, product demos |
| `split-top` | Colored top bar with title, frame below | Tutorials, how-to content |
| `minimal` | Full-bleed frame, small corner label | Atmospheric, visual-first content |

### Adding a custom style

Drop two files — no code changes needed:

1. `styles/<name>.json` — palette, fonts, hook pattern, layout config
2. `templates/<name>.html` — HTML/CSS template with `{{PLACEHOLDER}}` tokens

See existing styles for the schema.

## Output

- Files: `<video_name>.thumb_v1_<style>.jpg`, `<video_name>.thumb_v2_<style>.jpg`, ...
- Format: JPEG, 1280x720, under 2 MB (YouTube's limit)
- Location: next to the source video

## File structure

```
thumbnail-video/
├── SKILL.md                      # Skill instructions
├── scripts/
│   ├── extract_candidates.py     # Scene detection + frame extraction
│   └── render.py                 # HTML template → Chrome screenshot → JPEG
├── styles/
│   ├── bold-left.json
│   ├── face-zoom.json
│   ├── minimal.json
│   ├── split-top.json
│   └── ui-callout.json
└── templates/
    ├── bold-left.html
    ├── face-zoom.html
    ├── minimal.html
    ├── split-top.html
    └── ui-callout.html
```
