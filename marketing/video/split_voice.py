"""Splits one long voiceover file into the 8 scene clips at its 7 longest pauses.

Usage: .venv\\Scripts\\python marketing\\video\\split_voice.py bn [path\\to\\full.mp3]
Output: marketing\\video\\audio\\<lang>\\1.mp3 … 8.mp3
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
HERE = Path(__file__).resolve().parent


def duration(path: Path) -> float:
    r = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True, errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def silences(path: Path, noise="-35dB", min_d=0.35):
    r = subprocess.run([FF, "-i", str(path), "-af", f"silencedetect=noise={noise}:d={min_d}", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace")
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(starts, ends))


def main() -> None:
    lang = sys.argv[1]
    out = HERE / "audio" / lang
    src = Path(sys.argv[2]) if len(sys.argv) > 2 else out / "full.mp3"
    total = duration(src)
    gaps = [g for g in silences(src, min_d=0.2) if 0.5 < g[0] < total - 0.5]   # ignore lead-in / tail silence
    if len(gaps) < 7:
        sys.exit(f"Only {len(gaps)} pauses found; need 7.")

    lines = json.loads((HERE / "voiceover.json").read_text(encoding="utf-8"))[lang]
    chars = [len(s) for s in lines]
    # Where each paragraph should end if speech speed were even (from text length).
    expected = [total * sum(chars[:k + 1]) / sum(chars) for k in range(7)]
    mids = [(a + b) / 2 for a, b in gaps]
    lens = [b - a for a, b in gaps]

    # Pick 7 pauses in order that sit closest to the expected boundaries, preferring longer pauses.
    def cost(k, c):
        return ((mids[c] - expected[k]) / 4.0) ** 2 - 3.0 * lens[c]

    n, INF = len(gaps), float("inf")
    best = [[INF] * n for _ in range(7)]
    prev = [[-1] * n for _ in range(7)]
    for c in range(n):
        best[0][c] = cost(0, c)
    for k in range(1, 7):
        for c in range(n):
            for b in range(c):
                v = best[k - 1][b] + cost(k, c)
                if v < best[k][c]:
                    best[k][c], prev[k][c] = v, b
    c = min(range(n), key=lambda i: best[6][i])
    chosen = []
    for k in range(6, -1, -1):
        chosen.append(c)
        c = prev[k][c]
    cuts = [gaps[i] for i in reversed(chosen)]
    points = [0.0] + [(a + b) / 2 for a, b in cuts] + [total]
    seg = [points[i + 1] - points[i] for i in range(8)]
    print(f"total {total:.1f}s | pauses used: " + ", ".join(f"{a:.1f}-{b:.1f}" for a, b in cuts))
    worst = 0.0
    for i in range(8):
        expect = total * chars[i] / sum(chars)
        ratio = seg[i] / expect
        worst = max(worst, abs(1 - ratio))
        print(f"  scene {i + 1}: {seg[i]:5.1f}s  (expected ~{expect:4.1f}s from text length, x{ratio:.2f})")
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(src), "-ss", f"{points[i]:.3f}",
                        "-to", f"{points[i + 1]:.3f}", "-af", "silenceremove=start_periods=1:start_threshold=-45dB,"
                        "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                        "-c:a", "libmp3lame", "-b:a", "192k", str(out / f"{i + 1}.mp3")], check=True)
    print("OK" if worst < 0.45 else "WARNING: a scene length looks off – check the split points")


if __name__ == "__main__":
    main()
