"""Render the profile banner as two SVGs (dark + light).

Run daily by .github/workflows/banner.yml. Pure standard library, no installs.
The terrain is fixed; the drone's position along its survey loop, its
heading, the detection confidences and the IMU trace change with the date.
"""

import math
import random
from datetime import datetime, timezone

W, H = 720, 320
CX, CY = 360, 150                      # centre of the sensor frame
FX0, FY0, FX1, FY1 = 196, 66, 524, 238  # sensor frame bounds
LOOP_DAYS = 41                          # days for the drone to complete one loop

THEMES = {
    "dark": dict(
        bg="#0d1117", mark="#30363d", faint="#1c2128", contour="#262c36",
        dim="#7d8590", text="#d1d7e0",
        amber="#e3b341", green="#3fb950", red="#f85149", blue="#58a6ff",
    ),
    "light": dict(
        bg="#ffffff", mark="#d0d7de", faint="#eef1f4", contour="#e1e6eb",
        dim="#656d76", text="#1f2328",
        amber="#9a6700", green="#1a7f37", red="#cf222e", blue="#0969da",
    ),
}


def f(x):
    return f"{x:.2f}".rstrip("0").rstrip(".")


def contour_path(cx, cy, r0, harmonics, steps=96):
    """Closed blob: radius modulated by a few sine harmonics."""
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        r = r0 * (1 + sum(a * math.sin(k * t + p) for k, a, p in harmonics))
        pts.append((cx + r * math.cos(t) * 1.45, cy + r * math.sin(t)))
    d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"
    return d


def lemniscate(t, ax=132, ay=74):
    """Figure-of-eight survey loop around the frame centre."""
    return CX + ax * math.sin(t), CY + ay * math.sin(t) * math.cos(t)


def render(theme, now):
    c = THEMES[theme]
    doy = now.timetuple().tm_yday
    day_index = (now.date() - datetime(2024, 1, 1).date()).days
    rng = random.Random(now.strftime("%Y%m%d"))

    out = []
    add = out.append

    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">')
    add('<title id="t">JS/R-01 aerial reconnaissance display</title>')
    add(f'<desc id="d">James Scott, KCL engineering. Sortie {doy:04d}: a drone '
        f'surveys terrain while a detector tracks three objects.</desc>')
    add(f"""<style>
  text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }}
  .des {{ font-size: 11px; font-weight: 700; letter-spacing: 2.6px; fill: {c['text']}; }}
  .tel {{ font-size: 9px; letter-spacing: 1.4px; fill: {c['text']}; }}
  .lab {{ font-size: 6.5px; letter-spacing: 1.6px; fill: {c['dim']}; }}
  .box {{ font-size: 6.5px; letter-spacing: 1.2px; font-weight: 600; }}
</style>""")
    add(f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>')

    # registration marks
    add(f'<g fill="none" stroke="{c["mark"]}" stroke-width="1">')
    for d in ("M16 32V16H32", f"M{W-32} 16H{W-16}V32",
              f"M16 {H-32}V{H-16}H32", f"M{W-32} {H-16}H{W-16}V{H-32}"):
        add(f'<path d="{d}"/>')
    add("</g>")

    # sensor frame: corner brackets, clipped terrain, grid ticks
    add(f'<clipPath id="fr"><rect x="{FX0}" y="{FY0}" width="{FX1-FX0}" height="{FY1-FY0}"/></clipPath>')
    add(f'<g clip-path="url(#fr)" fill="none" stroke="{c["contour"]}" stroke-width="0.8">')
    terrain = random.Random(1912)  # fixed terrain
    for hx, hy, levels in ((300, 120, 6), (440, 190, 5), (520, 80, 3)):
        harm = [(k, terrain.uniform(0.04, 0.12), terrain.uniform(0, 6.28)) for k in (2, 3, 5)]
        for lv in range(1, levels + 1):
            add(f'<path d="{contour_path(hx, hy, 11 * lv, harm)}"/>')
    add("</g>")
    add(f'<g stroke="{c["faint"]}" stroke-width="0.6">'
        f'<line x1="{FX0}" y1="{CY}" x2="{FX1}" y2="{CY}"/>'
        f'<line x1="{CX}" y1="{FY0}" x2="{CX}" y2="{FY1}"/></g>')
    b = 12
    add(f'<g fill="none" stroke="{c["mark"]}" stroke-width="1">'
        f'<path d="M{FX0} {FY0+b}V{FY0}H{FX0+b}"/><path d="M{FX1-b} {FY0}H{FX1}V{FY0+b}"/>'
        f'<path d="M{FX0} {FY1-b}V{FY1}H{FX0+b}"/><path d="M{FX1-b} {FY1}H{FX1}V{FY1-b}"/></g>')
    add(f'<g stroke="{c["mark"]}" stroke-width="0.8">')
    for i in range(1, 8):
        x = FX0 + (FX1 - FX0) * i / 8
        add(f'<line x1="{f(x)}" y1="{FY1}" x2="{f(x)}" y2="{FY1-3 if i % 2 else FY1-6}"/>')
    add("</g>")

    # detections: two confirmed, one below threshold (dashed)
    dets = [
        (238, 92, 34, 22, c["green"], "VEH", rng.uniform(0.82, 0.93), True),
        (446, 168, 40, 26, c["blue"], "APC", rng.uniform(0.66, 0.79), True),
        (300, 196, 26, 18, c["red"], "UNK", rng.uniform(0.21, 0.34), False),
    ]
    for x, y, w, h, col, cls, conf, ok in dets:
        k = 6
        dash = "" if ok else ' stroke-dasharray="2 2" opacity="0.7"'
        add(f'<g fill="none" stroke="{col}" stroke-width="1.1"{dash}>'
            f'<path d="M{x} {y+k}V{y}H{x+k}"/><path d="M{x+w-k} {y}H{x+w}V{y+k}"/>'
            f'<path d="M{x} {y+h-k}V{y+h}H{x+k}"/><path d="M{x+w-k} {y+h}H{x+w}V{y+h-k}"/></g>')
        add(f'<rect x="{f(x+w/2-1.5)}" y="{f(y+h/2-1.5)}" width="3" height="3" fill="{col}"{dash}/>')
        tag = f"{cls} {conf:.2f}" + ("" if ok else " &lt;τ")
        add(f'<text x="{x}" y="{y-4}" class="box" fill="{col}"{dash}>{tag}</text>')

    # survey loop and drone
    loop = [lemniscate(2 * math.pi * i / 160) for i in range(161)]
    d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in loop)
    add(f'<path d="{d}" fill="none" stroke="{c["amber"]}" stroke-width="0.9" '
        f'stroke-dasharray="1.5 3.5" opacity="0.55"/>')

    t = 2 * math.pi * (day_index % LOOP_DAYS) / LOOP_DAYS
    trail = [lemniscate(t - 0.5 + 0.5 * i / 20) for i in range(21)]
    d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in trail)
    add(f'<path d="{d}" fill="none" stroke="{c["amber"]}" stroke-width="1.4" opacity="0.9"/>')

    px, py = lemniscate(t)
    nx, ny = lemniscate(t + 0.01)
    ang = math.degrees(math.atan2(ny - py, nx - px))
    heading = (ang + 90) % 360  # screen-up is north
    add(f'<circle cx="{f(px)}" cy="{f(py)}" r="16" fill="{c["amber"]}" opacity="0.08"/>')
    add(f'<g transform="translate({f(px)} {f(py)}) rotate({f(ang + 45)})" stroke="{c["amber"]}" '
        f'stroke-width="1.3" fill="none">'
        f'<line x1="-6" y1="-6" x2="6" y2="6"/><line x1="-6" y1="6" x2="6" y2="-6"/>'
        f'<circle cx="-6" cy="-6" r="2.6"/><circle cx="6" cy="6" r="2.6"/>'
        f'<circle cx="-6" cy="6" r="2.6"/><circle cx="6" cy="-6" r="2.6"/></g>')
    add(f'<circle cx="{f(px)}" cy="{f(py)}" r="1.6" fill="{c["amber"]}"/>')

    # centre reticle
    add(f'<g fill="none" stroke="{c["dim"]}" stroke-width="0.8" opacity="0.8">'
        f'<circle cx="{CX}" cy="{CY}" r="9"/>'
        f'<line x1="{CX-15}" y1="{CY}" x2="{CX-11}" y2="{CY}"/><line x1="{CX+11}" y1="{CY}" x2="{CX+15}" y2="{CY}"/>'
        f'<line x1="{CX}" y1="{CY-15}" x2="{CX}" y2="{CY-11}"/><line x1="{CX}" y1="{CY+11}" x2="{CX}" y2="{CY+15}"/></g>')

    # header
    add(f'<text x="32" y="38" class="des">JS/R–01</text>')
    add(f'<text x="32" y="53" class="lab">AERIAL RECONNAISSANCE</text>')
    add(f'<text x="{W-32}" y="38" text-anchor="end" class="tel">{now.year}.{doy:03d}</text>')
    add(f'<text x="{W-32}" y="53" text-anchor="end" class="lab">TRACK 02/03</text>')

    # telemetry: left (platform) and right (models)
    left = [("POSITION", "51.5115N 0.1160W"), ("ALTITUDE", f"{rng.randint(112, 128)} M AGL"),
            ("HEADING", f"{heading:05.1f}°")]
    right = [("DETECTOR", "mAP@.5 0.511"), ("PRECISION / RECALL", "0.631 / 0.469"),
             ("STATUS", "GRAD ROLES 2027")]
    for i, (lab, val) in enumerate(left):
        y = 104 + i * 40
        add(f'<text x="32" y="{y}" class="lab">{lab}</text>')
        add(f'<text x="32" y="{y+13}" class="tel">{val}</text>')
        add(f'<line x1="32" y1="{y+19}" x2="150" y2="{y+19}" stroke="{c["mark"]}" stroke-width="0.6"/>')
    for i, (lab, val) in enumerate(right):
        y = 104 + i * 40
        add(f'<text x="{W-32}" y="{y}" text-anchor="end" class="lab">{lab}</text>')
        add(f'<text x="{W-32}" y="{y+13}" text-anchor="end" class="tel">{val}</text>')
        add(f'<line x1="{W-150}" y1="{y+19}" x2="{W-32}" y2="{y+19}" stroke="{c["mark"]}" stroke-width="0.6"/>')

    # IMU trace (roll + pitch) under the frame
    ph = rng.uniform(0, 6.28)
    for col, amp, freqs, op in ((c["blue"], 5.5, (0.11, 0.37, 0.83), 0.75),
                                (c["green"], 3.5, (0.07, 0.29, 1.21), 0.6)):
        pts = []
        for i in range(0, 329, 2):
            x = FX0 + i
            y = 272 + amp * (0.6 * math.sin(freqs[0] * i + ph) + 0.3 * math.sin(freqs[1] * i + 2 * ph)
                             + 0.1 * math.sin(freqs[2] * i - ph))
            pts.append(f"{x} {f(y)}")
        add(f'<path d="M{" L".join(pts)}" fill="none" stroke="{col}" stroke-width="0.8" opacity="{op}"/>')
    add(f'<line x1="{FX0}" y1="272" x2="{FX1}" y2="272" stroke="{c["faint"]}" stroke-width="0.6"/>')

    # footer
    add(f'<text x="32" y="276" class="lab">IMU // ROLL · PITCH</text>')
    add(f'<text x="32" y="292" class="lab">VIOXACUTE · KCL ENGINEERING</text>')
    add(f'<text x="{W-32}" y="276" text-anchor="end" class="lab">SORTIE {doy:04d}</text>')
    add(f'<text x="{W-32}" y="292" text-anchor="end" class="lab">SYS NOMINAL</text>')

    add("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    for name in THEMES:
        with open(f"banner-{name}.svg", "w", encoding="utf-8") as fh:
            fh.write(render(name, now))
    print(f"rendered banners for {now:%Y-%m-%d}")
