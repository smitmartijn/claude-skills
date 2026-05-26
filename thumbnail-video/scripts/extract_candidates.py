#!/usr/bin/env python3
"""Extract candidate thumbnail frames from a video.

Usage: extract_candidates.py <video> <out_dir>

Writes:
  <out_dir>/frames/scene_NN_HHMMSS.jpg    — scene-change candidates
  <out_dir>/frames/uniform_NN_HHMMSS.jpg  — uniform-sample fallbacks
  <out_dir>/candidates.json               — ordered list with timestamps

Hardware-decodes via VideoToolbox, scales to 1280-wide preserving aspect.
"""

import json
import platform
import re
import subprocess
import sys
from pathlib import Path

IS_MAC = platform.system() == "Darwin"


def ffprobe_duration(src: Path) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(src)
    ]).decode().strip())


def scene_timestamps(src: Path, threshold: float = 0.3, limit: int = 12) -> list[float]:
    cmd = ["ffmpeg"]
    if IS_MAC:
        cmd += ["-hwaccel", "videotoolbox"]
    cmd += ["-i", str(src), "-vf", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    times = [float(t) for t in re.findall(r"pts_time:([\d.]+)", proc.stderr)]
    return times[:limit]


def uniform_timestamps(duration: float, target_count: int = 8) -> list[float]:
    step = max(20.0, duration / target_count)
    out, t = [], step / 2
    while t < duration:
        out.append(t)
        t += step
    return out


def hms(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    return f"{h:02d}{m:02d}{s:02d}"


def extract_frame(src: Path, ts: float, out_path: Path) -> None:
    cmd = ["ffmpeg", "-y"]
    if IS_MAC:
        cmd += ["-hwaccel", "videotoolbox"]
    cmd += ["-ss", f"{ts:.3f}", "-i", str(src), "-frames:v", "1", "-q:v", "2",
            "-vf", "scale=1280:-2", str(out_path)]
    subprocess.run(cmd, capture_output=True, check=True)


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: extract_candidates.py <video> <out_dir>", file=sys.stderr)
        sys.exit(2)

    src = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve()
    (out / "frames").mkdir(parents=True, exist_ok=True)

    duration = ffprobe_duration(src)
    scene_ts = scene_timestamps(src)
    uniform_ts = uniform_timestamps(duration)

    candidates = []
    for kind, ts_list in (("scene", scene_ts), ("uniform", uniform_ts)):
        for i, ts in enumerate(ts_list, start=1):
            out_path = out / "frames" / f"{kind}_{i:02d}_{hms(ts)}.jpg"
            try:
                extract_frame(src, ts, out_path)
            except subprocess.CalledProcessError:
                continue
            candidates.append({
                "t": round(ts, 3),
                "kind": kind,
                "path": str(out_path),
            })

    (out / "candidates.json").write_text(json.dumps(candidates, indent=2))

    for c in candidates:
        print(f"{c['t']:7.2f}  {c['kind']:8}  {c['path']}")


if __name__ == "__main__":
    main()
