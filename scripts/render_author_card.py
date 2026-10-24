"""Author card for the demo video: real GitHub avatar plus framing."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
BG = (6, 11, 19)
LINE = (29, 44, 63)
INK = (232, 240, 248)
MUTED = (139, 160, 182)
CV = (18, 176, 232)
FONTS = Path("C:/Windows/Fonts")


def f(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/video")
    avatar_path = out / "avatar.png"
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for y in range(0, H, 4):
        shade = 8 + int(10 * (1 - y / H))
        d.line([(0, y), (W, y)], fill=(shade, shade + 4, shade + 8))
    d.rectangle([0, 0, 8, H], fill=CV)
    if avatar_path.exists():
        size = 190
        avatar = Image.open(avatar_path).convert("RGB").resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        img.paste(avatar, (72, 150), mask)
        d.ellipse((72, 150, 72 + size, 150 + size), outline=CV, width=3)
    d.text((300, 168), "Tingqiu Liu", font=f("seguisb.ttf", 44), fill=INK)
    d.text((300, 226), "@liutingqiu", font=f("consola.ttf", 19), fill=CV)
    d.text((300, 262), "design, implementation, evaluation, documentation", font=f("consola.ttf", 16), fill=MUTED)
    d.line([(72, 392), (1208, 392)], fill=LINE)
    d.text((72, 420), "One person, one repository, no starter-kit pipeline inherited from a template.", font=f("consola.ttf", 19), fill=INK)
    d.text((72, 452), "Detector, motion channel, zone logic, dispatch layer and tests were written for", font=f("consola.ttf", 19), fill=MUTED)
    d.text((72, 480), "this entry and are auditable file by file.", font=f("consola.ttf", 19), fill=MUTED)
    d.text((72, 560), "github.com/liutingqiu   /   devpost.com/liutingqiu", font=f("consola.ttf", 17), fill=MUTED)
    img.save(out / "card_author.png")
    print("author card written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
