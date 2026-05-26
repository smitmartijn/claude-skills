#!/usr/bin/env python3
"""Render a single thumbnail variant.

Usage:
  render.py --style <name> --frame <path> --hook "<text>" --out <path>
            [--subhook "<text>"] [--badge "<label>"]

Loads ~/.claude/skills/thumbnail-video/styles/<name>.json + matching template,
substitutes placeholders, screenshots via headless Chrome at 1280x720,
converts to JPEG, ensures <2 MB.
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
STYLES_DIR = SKILL_DIR / "styles"
TEMPLATES_DIR = SKILL_DIR / "templates"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("chromium") or "",
    shutil.which("chromium-browser") or "",
    shutil.which("google-chrome") or "",
]


def find_chrome() -> str:
    for path in CHROME_CANDIDATES:
        if path and Path(path).exists():
            return path
    sys.exit("error: no Chrome/Chromium binary found")


def load_style(name: str) -> dict:
    path = STYLES_DIR / f"{name}.json"
    if not path.exists():
        sys.exit(f"error: unknown style '{name}' (no {path})")
    return json.loads(path.read_text())


def load_template(name: str) -> str:
    path = TEMPLATES_DIR / name
    if not path.exists():
        sys.exit(f"error: missing template {path}")
    return path.read_text()


def substitute(template: str, mapping: dict[str, str]) -> str:
    """Replace {{KEY}} occurrences with mapping[key]. Unmatched keys → empty string."""
    def repl(m: "re.Match[str]") -> str:
        key = m.group(1).strip().upper()
        return mapping.get(key, "")
    return re.sub(r"\{\{([A-Z0-9_]+)\}\}", repl, template)


def subhook_block(style: dict, subhook: str | None) -> str:
    if not style.get("supports_subhook") or not subhook:
        return ""
    return f'<div class="subhook">{html.escape(subhook)}</div>'


def render_chrome(chrome: str, html_path: Path, png_path: Path) -> None:
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--default-background-color=00000000",
        "--virtual-time-budget=8000",
        "--window-size=1280,720",
        f"--screenshot={png_path}",
        html_path.as_uri(),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if not png_path.exists():
        sys.exit(f"error: chrome did not produce screenshot\nstderr:\n{proc.stderr}")


def png_to_jpeg(png_path: Path, jpeg_path: Path, max_bytes: int = 2_000_000) -> None:
    for qv in (2, 3, 5, 7, 10):
        subprocess.run([
            "ffmpeg", "-y", "-i", str(png_path),
            "-vf", "scale=1280:720", "-q:v", str(qv),
            str(jpeg_path),
        ], capture_output=True, check=True)
        if jpeg_path.stat().st_size <= max_bytes:
            return
    sys.exit("error: could not get JPEG under 2 MB even at q:v 10")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", required=True)
    ap.add_argument("--frame", required=True)
    ap.add_argument("--hook", required=True)
    ap.add_argument("--subhook", default=None)
    ap.add_argument("--badge", default=None, help="override badge label (ui-callout style)")
    ap.add_argument("--text-color", default=None, help="override the style's 'text' role color (hex)")
    ap.add_argument("--accent-color", default=None, help="override the style's 'accent' role color (hex)")
    ap.add_argument("--bg-color", default=None, help="override the style's 'bg' role color (hex)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    style = load_style(args.style)
    template = load_template(style["template"])

    frame_path = Path(args.frame).resolve()
    if not frame_path.exists():
        sys.exit(f"error: frame not found: {frame_path}")

    palette = dict(style.get("palette", {}))
    roles = style.get("roles", {})
    for role, override in (("text", args.text_color), ("accent", args.accent_color), ("bg", args.bg_color)):
        if not override:
            continue
        for palette_key in roles.get(role, []):
            palette[palette_key] = override

    mapping: dict[str, str] = {}
    for key, value in palette.items():
        mapping[key.upper()] = str(value)

    badge_label = args.badge or style.get("badge_label", "")
    if badge_label:
        mapping["BADGE_LABEL"] = html.escape(badge_label)

    mapping["FRAME"] = frame_path.as_uri()
    mapping["HOOK"] = html.escape(args.hook)
    mapping["SUBHOOK_BLOCK"] = subhook_block(style, args.subhook)

    html_out = substitute(template, mapping)

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    chrome = find_chrome()
    with tempfile.TemporaryDirectory(prefix="thumb-render-") as td:
        td_path = Path(td)
        html_path = td_path / "template.html"
        html_path.write_text(html_out)
        png_path = td_path / "shot.png"
        render_chrome(chrome, html_path, png_path)
        png_to_jpeg(png_path, out_path)

    size_kb = out_path.stat().st_size / 1024
    print(f"{out_path}  ({size_kb:.0f} KB, style={args.style})")


if __name__ == "__main__":
    main()
