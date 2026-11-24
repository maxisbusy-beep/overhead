#!/usr/bin/env python3
"""Generate Overhead's PWA / Android launcher icons.

Pure-Python (Pillow only). Re-run after changing the design:

    python tools/make-icons.py

Writes the PNGs listed in ICON_SET into icons/. The artwork is drawn on a
unit square and supersampled, so every size is crisp.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "icons"

# Palette lifted from index.html's :root custom properties.
GROUND = (11, 15, 26)      # --ground  #0b0f1a
PANEL = (20, 26, 41)       # --panel   #141a29
LINE = (42, 51, 80)        # --line    #2a3350
SUNLIT = (255, 181, 71)    # --sunlit  #ffb547
PICK = (127, 224, 208)     # --pick    #7fe0d0
INK = (223, 228, 242)      # --ink     #dfe4f2

SS = 4  # supersampling factor

# (filename, pixel size, content inset)
# Maskable icons keep their artwork inside the central ~80% safe zone, because
# Android may crop the icon to a circle or squircle.
ICON_SET = [
    ("icon-192.png", 192, 0.92),
    ("icon-512.png", 512, 0.92),
    ("icon-maskable-512.png", 512, 0.72),
    ("apple-touch-icon.png", 180, 0.92),
    ("favicon-32.png", 32, 1.0),
]

def _stars():
    return [
        (0.195, 0.205, 0.0180, 1.00),
        (0.370, 0.112, 0.0105, 0.70),
        (0.800, 0.138, 0.0125, 0.82),
        (0.300, 0.330, 0.0085, 0.55),
        (0.620, 0.455, 0.0095, 0.62),
        (0.880, 0.360, 0.0080, 0.50),
        (0.108, 0.420, 0.0075, 0.45),
    ]


def xform(p, inset):
    """Scale a unit-square point toward the centre by `inset`."""
    x, y = p
    return (0.5 + (x - 0.5) * inset, 0.5 + (y - 0.5) * inset)


def draw_icon(size, inset):
    n = size * SS
    img = Image.new("RGB", (n, n), GROUND)

    def px(p):
        x, y = xform(p, inset)
        return (x * n, y * n)

    def s(v):
        return v * n * inset

    # ---- Earth's limb: a dark cap across the bottom, teal-lit at the edge.
    cx, cy, r = 0.5, 1.46, 0.90
    box_centre = px((cx, cy))
    rr = s(r)
    bbox = [box_centre[0] - rr, box_centre[1] - rr, box_centre[0] + rr, box_centre[1] + rr]

    ground = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    ImageDraw.Draw(ground).ellipse(bbox, fill=PANEL + (255,))
    img.paste(ground, (0, 0), ground)

    limb = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    ld = ImageDraw.Draw(limb)
    ld.arc(bbox, 180, 360, fill=LINE + (255,), width=int(s(0.030)))
    ld.arc(bbox, 198, 342, fill=PICK + (190,), width=int(s(0.018)))
    glow = limb.filter(ImageFilter.GaussianBlur(s(0.022)))
    img.paste(glow, (0, 0), glow)
    img.paste(limb, (0, 0), limb)

    # ---- Stars
    star_layer = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    sd = ImageDraw.Draw(star_layer)
    for x, y, rad, b in _stars():
        c = px((x, y))
        rp = s(rad)
        a = int(90 + 165 * b)
        sd.ellipse([c[0] - rp, c[1] - rp, c[0] + rp, c[1] + rp], fill=INK + (a,))
    star_glow = star_layer.filter(ImageFilter.GaussianBlur(s(0.016)))
    img.paste(star_glow, (0, 0), star_glow)
    img.paste(star_layer, (0, 0), star_layer)

    # ---- Satellite trail: a dashed arc climbing to the right.
    trail = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    td = ImageDraw.Draw(trail)
    pts = [
        (0.170, 0.630), (0.255, 0.567), (0.340, 0.508), (0.425, 0.453),
        (0.510, 0.402), (0.578, 0.362), (0.646, 0.325),
    ]
    w = max(1, int(s(0.026)))
    for i in range(0, len(pts) - 1):
        if i % 2 == 1:          # skip every other segment -> dashes
            continue
        a = int(120 + 125 * (i / (len(pts) - 2)))
        td.line([px(pts[i]), px(pts[i + 1])], fill=SUNLIT + (a,), width=w)

    # ---- The satellite itself
    head = px((0.700, 0.300))
    hr = s(0.058)
    td.ellipse([head[0] - hr, head[1] - hr, head[0] + hr, head[1] + hr], fill=SUNLIT + (255,))

    trail_glow = trail.filter(ImageFilter.GaussianBlur(s(0.030)))
    img.paste(trail_glow, (0, 0), trail_glow)
    img.paste(trail, (0, 0), trail)

    return img.resize((size, size), Image.LANCZOS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, size, inset in ICON_SET:
        img = draw_icon(size, inset)
        path = OUT / name
        img.save(path, "PNG", optimize=True)
        print(f"wrote {path.relative_to(ROOT)}  {size}x{size}  {path.stat().st_size} B")


if __name__ == "__main__":
    main()
