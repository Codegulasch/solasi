#!/usr/bin/env python3
"""Erzeugt icon.png (128x128) und logo.png (250x100) für das Add-on. Braucht Pillow (pip install pillow).

Aufruf:  tools/make_logo.py "Name" [Ausgabeordner]
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont


def sun(size):
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22), fill=(32, 34, 40, 255))
    c = s / 2
    for k in range(8):
        a = k * math.pi / 4
        x1, y1 = c + math.cos(a) * s * 0.30, c + math.sin(a) * s * 0.30
        x2, y2 = c + math.cos(a) * s * 0.42, c + math.sin(a) * s * 0.42
        d.line([x1, y1, x2, y2], fill=(251, 191, 36, 255), width=int(s * 0.045))
        for x, y in ((x1, y1), (x2, y2)):
            r = s * 0.0225
            d.ellipse([x - r, y - r, x + r, y + r], fill=(251, 191, 36, 255))
    r = s * 0.22
    d.ellipse([c - r, c - r, c + r, c + r], fill=(249, 160, 20, 255))
    r = s * 0.10
    d.ellipse([c - r, c - r, c + r, c + r], fill=(255, 244, 214, 255))
    return im.resize((size, size), Image.LANCZOS)


def font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/Library/Fonts/Arial Bold.ttf",
                 "C:\\Windows\\Fonts\\arialbd.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make(name, out="."):
    sun(128).save(os.path.join(out, "icon.png"))
    logo = Image.new("RGBA", (250, 100), (0, 0, 0, 0))
    mark = sun(84)
    logo.paste(mark, (8, 8), mark)
    size = 34
    f = font(size)
    d = ImageDraw.Draw(logo)
    while size > 14 and d.textlength(name, font=f) > 140:    # lange Namen verkleinern
        size -= 2
        f = font(size)
    d.text((100, 50 - size * 0.62), name, font=f, fill=(249, 160, 20, 255))
    logo.save(os.path.join(out, "logo.png"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    make(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ".")
    print("icon.png und logo.png erzeugt")
