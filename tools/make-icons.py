#!/usr/bin/env python3
"""Generate Overhead's icons: PWA icons and the Android launcher icon.

Pure Python (Pillow only). Re-run after changing the design:

    python tools/make-icons.py

Writes:
  icons/                              PWA / home-screen icons
  android/app/src/main/res/mipmap-*/  Android launcher icons
  android/app/src/main/res/values/ic_launcher_background.xml

The artwork is drawn on a unit square and supersampled, so every size is crisp.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "icons"
RES = ROOT / "android/app/src/main/res"

# Palette lifted from index.html's :root custom properties.
GROUND = (11, 15, 26)      # --ground  #0b0f1a
PANEL = (20, 26, 41)       # --panel   #141a29
LINE = (42, 51, 80)        # --line    #2a3350
SUNLIT = (255, 181, 71)    # --sunlit  #ffb547
PICK = (127, 224, 208)     # --pick    #7fe0d0
INK = (223, 228, 242)      # --ink     #dfe4f2

GROUND_HEX = "#0b0f1a"

SS = 4  # supersampling factor

# (filename, pixel size, content inset)
# Maskable icons keep their artwork inside the central ~80% safe zone, because
# Android may crop the icon to a circle or squircle.
PWA_SET = [
    ("icon-192.png", 192, 0.92),
    ("icon-512.png", 512, 0.92),
    ("icon-maskable-512.png", 512, 0.72),
    ("apple-touch-icon.png", 180, 0.92),
    ("favicon-32.png", 32, 1.0),
]

# Android adaptive icons: the foreground layer is 108dp and only the central
# 72dp is guaranteed visible, so content is inset to roughly that fraction.
FG_INSET = 0.62
DENSITIES = [
    ("mdpi", 48, 108),
    ("hdpi", 72, 162),
    ("xhdpi", 96, 216),
    ("xxhdpi", 144, 324),
    ("xxxhdpi", 192, 432),
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


def compose(size, inset, background=True, round_mask=False):
    n = size * SS
    img = Image.new("RGBA", (n, n), GROUND + (255,) if background else (0, 0, 0, 0))

    def px(p):
        x, y = xform(p, inset)
        return (x * n, y * n)

    def s(v):
        return v * n * inset

    # ---- Earth's limb: a dark cap across the bottom, teal-lit at the edge.
    cx, cy, r = 0.5, 1.46, 0.90
    c = px((cx, cy))
    rr = s(r)
    bbox = [c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr]

    ground = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    ImageDraw.Draw(ground).ellipse(bbox, fill=PANEL + (255,))
    img.alpha_composite(ground)

    limb = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    ld = ImageDraw.Draw(limb)
    ld.arc(bbox, 180, 360, fill=LINE + (255,), width=int(s(0.030)))
    ld.arc(bbox, 198, 342, fill=PICK + (190,), width=int(s(0.018)))
    glow = limb.filter(ImageFilter.GaussianBlur(s(0.022)))
    img.alpha_composite(glow)
    img.alpha_composite(limb)

    # ---- Stars
    star_layer = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    sd = ImageDraw.Draw(star_layer)
    for x, y, rad, b in _stars():
        p = px((x, y))
        rp = s(rad)
        sd.ellipse([p[0] - rp, p[1] - rp, p[0] + rp, p[1] + rp], fill=INK + (int(90 + 165 * b),))
    img.alpha_composite(star_layer.filter(ImageFilter.GaussianBlur(s(0.016))))
    img.alpha_composite(star_layer)

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

    head = px((0.700, 0.300))
    hr = s(0.058)
    td.ellipse([head[0] - hr, head[1] - hr, head[0] + hr, head[1] + hr], fill=SUNLIT + (255,))

    img.alpha_composite(trail.filter(ImageFilter.GaussianBlur(s(0.030))))
    img.alpha_composite(trail)

    if round_mask:
        mask = Image.new("L", (n, n), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, n - 1, n - 1], fill=255)
        img.putalpha(mask)

    return img.resize((size, size), Image.LANCZOS)


def write(img, path, mode="RGBA"):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert(mode).save(path, "PNG", optimize=True)
    print(f"  {path.relative_to(ROOT).as_posix()}  {img.size[0]}x{img.size[1]}  {path.stat().st_size} B")


def main():
    print("PWA icons:")
    for name, size, inset in PWA_SET:
        write(compose(size, inset), ICONS / name, mode="RGB")

    print("Android launcher icons:")
    for density, legacy, fg in DENSITIES:
        d = RES / f"mipmap-{density}"
        write(compose(legacy, 0.92), d / "ic_launcher.png", mode="RGB")
        write(compose(legacy, 0.92, round_mask=True), d / "ic_launcher_round.png")
        write(compose(fg, FG_INSET, background=False), d / "ic_launcher_foreground.png")

    # The adaptive icon's background layer is a flat colour behind the foreground.
    bg = RES / "values/ic_launcher_background.xml"
    bg.parent.mkdir(parents=True, exist_ok=True)
    bg.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<resources>\n"
        f'    <color name="ic_launcher_background">{GROUND_HEX}</color>\n'
        "</resources>\n",
        encoding="utf-8",
    )
    print(f"  {bg.relative_to(ROOT).as_posix()}  -> {GROUND_HEX}")


if __name__ == "__main__":
    main()
