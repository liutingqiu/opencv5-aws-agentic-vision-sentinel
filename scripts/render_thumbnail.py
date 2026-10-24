"""Build a 1280x720 thumbnail from a real annotated frame."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
FONTS = Path("C:/Windows/Fonts")


def f(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


frame = Image.open("runs/video/check2.png").convert("RGB").resize((W, H), Image.LANCZOS)
canvas = Image.new("RGB", (W, H), (6, 11, 19))
# Left: cropped camera view. Right: title slab.
crop = frame.crop((160, 0, 1120, 720)).resize((760, 720), Image.LANCZOS)
canvas.paste(crop, (0, 0))

d = ImageDraw.Draw(canvas)
d.rectangle([760, 0, W, H], fill=(9, 16, 26))
d.rectangle([760, 0, 766, H], fill=(18, 176, 232))

d.text((806, 96), "OPENCV AI COMPETITION 2026", font=f("consola.ttf", 17), fill=(139, 160, 182))
d.text((806, 124), "POWERED BY AWS", font=f("consola.ttf", 17), fill=(139, 160, 182))
d.text((806, 178), "Agentic", font=f("seguisb.ttf", 52), fill=(232, 240, 248))
d.text((806, 238), "Vision", font=f("seguisb.ttf", 52), fill=(232, 240, 248))
d.text((806, 298), "Sentinel", font=f("seguisb.ttf", 52), fill=(18, 176, 232))
d.line([(806, 384), (1216, 384)], fill=(29, 44, 63), width=2)
d.text((806, 406), "OpenCV 5.0.0 edge analysis", font=f("consola.ttf", 19), fill=(232, 240, 248))
d.text((806, 436), "boto3 -> S3 / EventBridge / SQS", font=f("consola.ttf", 19), fill=(255, 153, 0))
d.text((806, 490), "795 frames   p50 23.3 ms", font=f("consola.ttf", 18), fill=(139, 160, 182))
d.text((806, 516), "92 alerts dispatched", font=f("consola.ttf", 18), fill=(139, 160, 182))
d.text((806, 576), "Real run, not a mockup", font=f("consola.ttf", 17), fill=(37, 208, 125))

Path("runs/video").mkdir(parents=True, exist_ok=True)
canvas.save("runs/video/thumbnail.png")
print("thumbnail written")
