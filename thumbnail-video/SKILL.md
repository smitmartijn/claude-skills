---
name: thumbnail-video
description: Generate YouTube thumbnails (1280×720 JPEG) from a video. Picks frames via scene detection, overlays caption text using HTML/CSS rendered by headless Chrome, outputs multiple variants for YouTube A/B testing. Use when the user says "make a thumbnail", "generate thumbnails", "thumbnail for this video", or any variant of "youtube thumbnail".
---

# Thumbnail Video

Produce N YouTube thumbnail variants (1280×720 JPEG, <2 MB) from a video. Uses scene-detected candidate frames + HTML/CSS templates + headless Chrome for typography-grade rendering. Default 3 variants — matches YouTube Studio's "Test & Compare" cap.

## Prerequisites

Before running any commands, verify dependencies are installed:

```bash
command -v ffmpeg >/dev/null || { echo "ffmpeg not found"; exit 1; }
command -v ffprobe >/dev/null || { echo "ffprobe not found"; exit 1; }
command -v python3 >/dev/null || { echo "python3 not found"; exit 1; }
```

Chrome or Chromium must be available for HTML rendering. Check for it:
- macOS: `/Applications/Google Chrome.app` or `which chromium`
- Linux: `which google-chrome` or `which chromium-browser`

If missing, guide the user:
- **ffmpeg**: `brew install ffmpeg` (macOS) / `sudo apt install ffmpeg` (Linux)
- **Chrome**: `brew install --cask google-chrome` (macOS) / see https://www.google.com/chrome/ (Linux)

Templates load fonts from Google Fonts at render time — Chrome needs network access, or text falls back to system fonts.

The skill also depends on `transcribe-video` — if no transcript exists alongside the video, it calls `/transcribe-video` to generate one.

## Inputs

- Video path (user provides; otherwise ask)
- Optional: `--variants N` (default 3, max 5)
- Optional: `--style <name>` to lock one style; default = pick varied styles per variant
- Optional: `--hook "..."` to override generated hook copy
- Optional: `--transcript <path>` to a `.srt`/`.txt`; auto-detected from video sibling files

## Working directory

`./tmp/<basename>/` — keep candidates + intermediate renders for debugging.

## Available styles

Located in `~/.claude/skills/thumbnail-video/styles/*.json`. Each preset describes layout, palette, fonts, hook tone, and max words. Read the JSON to know what to generate.

Current presets:
- `bold-left` — huge yellow text left-third, frame right two-thirds. Benefit/promise tone.
- `face-zoom` — full-bleed frame, big bottom text with gradient. Curiosity/question tone.
- `ui-callout` — full-bleed UI screenshot, corner "NEW" badge + bottom label band. Feature-launch tone.
- `split-top` — colored top bar with bold title, frame fills below. Tutorial tone.
- `minimal` — full-bleed frame, small corner label. Atmospheric / let-the-frame-talk.

Adding a style = drop matching `styles/<name>.json` + `templates/<name>.html`. No code changes.

---

## Step 1 — Probe + plan

```bash
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC")
```

Decide variant matrix. For default 3 variants, pick 3 *different* styles so YouTube's A/B test compares meaningfully different designs (not three near-duplicates). Good default trio:

1. `bold-left` (text-driven benefit)
2. `face-zoom` (curiosity, presenter-focused)
3. `ui-callout` (feature launch, UI-focused)

Adjust based on video content — if there's no presenter face, swap `face-zoom` for `split-top`.

## Step 2 — Extract candidate frames

```bash
python3 scripts/extract_candidates.py "$SRC" ./tmp/$NAME
```

Produces:
- `frames/scene_<NN>_<TIMESTAMP>.jpg` — scene-change candidates (top ~10)
- `frames/uniform_<NN>_<TIMESTAMP>.jpg` — fallback samples every ~30s
- `candidates.json` — ordered list with timestamps and paths

## Step 3 — Draft variants (text + frame picks, no rendering yet)

Find the `.srt` next to the source. If missing, fall back to `.txt`. If neither exists, generate via `/transcribe-video` first.

For each variant draft a plan — do NOT render yet:

1. **Pick a frame.** View the candidate JPEGs (multimodal Read). Match frame content to style:
   - `bold-left` / `split-top`: any visually clean frame, ideally with negative space on the side where text will land
   - `face-zoom`: frame with presenter face on camera, centered or composed for bottom-text overlay
   - `ui-callout`: clearest UI screenshot showing the feature
   - `minimal`: most evocative single frame

2. **Generate a hook.** Read the style's `hook_pattern` and `max_words` from its JSON. Patterns:
   - `benefit` — promise an outcome ("Sync once. Use everywhere.")
   - `question` — provoke curiosity ("Still recreating profiles?")
   - `curiosity` — partial reveal ("The button that changes everything")
   - `feature` — declarative launch ("NEW: Web-managed profiles")
   - `tutorial` — instructional ("How to sync profiles across PCs")
   Pull vocabulary from the transcript. Avoid clickbait the user wouldn't say.

3. **Subhook (if the style supports it).** Tiny secondary line — context or specificity.

## Step 4 — Present plan + ask for sign-off

Print the draft plan as a clear table so the user can read it at a glance:

```
Plan (3 variants):
  v1 [bold-left]    "Build Once. Ship Everywhere." / "CI Pipelines"   frame @ 05:55
  v2 [face-zoom]    "Still deploying manually?"                       frame @ 08:59
  v3 [ui-callout]   "Auto-Rollback" / "Available Now"  + NEW          frame @ 03:58
```

Then call **AskUserQuestion** with two questions in one call:

1. **"Approve this variant plan?"** — options:
   - "Render as drafted" (default if user agrees)
   - "Change hooks"
   - "Change frames or styles"

2. **"Color treatment for text, accents, and badges?"** — options:
   - "Default palette per style" (each style keeps its own colors — yellow/pink/blue mix)
   - "YouTube-bold yellow accent" (#FFEB3B accent, white text)
   - "Blue accent" (#1565C0 accent, white text across all variants)
   - "High-contrast mono" (white text, white accent)
   If you know the user's brand colors from prior conversation/memory, offer those as options instead. "Other" is always available — user can type a hex.

If the user picks "Change hooks" or "Change frames/styles", iterate on the plan and re-ask. Only proceed to Step 5 once the plan is approved.

Translate the color choice to `--text-color` / `--accent-color` / `--bg-color` flags for render.py. "Default palette per style" → pass no overrides. "Brand color: WhatPulse blue" → `--accent-color "#1565C0" --text-color "#FFFFFF"` for every variant. For custom hex from "Other", parse what the user typed.

## Step 5 — Render

```bash
python3 scripts/render.py \
  --style bold-left \
  --frame ./tmp/$NAME/frames/scene_03_000355.jpg \
  --hook "Sync Once. Use Everywhere." \
  --subhook "WhatPulse profiles" \
  --accent-color "#1565C0" \
  --text-color "#FFFFFF" \
  --out "<source_dir>/<source_basename>.thumb_v1_bold-left.jpg"
```

Color flags are optional — omit to use the style's default palette. Each flag maps to one or more palette keys via the style's `roles` block (e.g. for `ui-callout`, `--accent-color` updates both the NEW badge fill and the bottom band accent line).

Repeat for each variant. The script handles:
- HTML template substitution
- Chrome headless screenshot at 1280×720
- PNG → JPEG q90 conversion + size check (<2 MB)

## Step 6 — Deliver + report

- Write all variants next to the source video: `<basename>.thumb_v<N>_<style>.jpg`
- Print per-variant: path, file size, style, hook
- Remind the user: in YouTube Studio → video → Thumbnail → "Test & Compare", upload all 3 to let YouTube rotate them and pick the highest-CTR variant.

---

## Pitfalls — don't repeat these

- **Don't render at the wrong size.** YouTube wants 1280×720. Chrome `--window-size=1280,720` only sets the viewport — confirm the rendered PNG is exactly that.
- **Don't ship oversized JPEGs.** YouTube rejects >2 MB. The render script clamps quality down if needed; if it can't get under 2 MB, that's a bug — report it.
- **Don't pick all three variants from the same scene.** Diversity is the point of A/B. If scene detection only yielded near-duplicate candidates, mix in uniform-sample frames.
- **Don't use frames with whisper/transcript watermarks visible.** Some recordings have a corner banner — scan candidates for them.
- **Don't write the hook as a full sentence with period.** YouTube thumbs read like billboards — fragments, not prose. "Sync once. Use everywhere." not "You can now sync once and use everywhere across your devices."
- **Don't escape the hook text wrong.** Quotes, ampersands, and emoji need to round-trip through JSON → HTML safely. The render script handles HTML-escaping; you handle JSON-escaping when passing `--hook`.
- **Don't leave intermediate PNGs in the user's directory.** Final deliverables are `.jpg`. Working PNGs stay in `./tmp/<basename>/`.

