"""Regenerates landing/og.png, the social preview image.

Social crawlers ignore SVG, so the preview has to be a raster file. Keeping the generator in
the repo means the image can be rebuilt after a wording change instead of being a binary
nobody knows how to reproduce.

    python3 landing/make-og-image.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1200, 630
BACKGROUND = (11, 11, 15)
GLOW = (99, 76, 234)
FOREGROUND = (250, 250, 250)
MUTED = (161, 161, 170)
ACCENT = (139, 133, 245)

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
OUTPUT = Path(__file__).with_name("og.png")


def radial_glow(size: tuple[int, int], center: tuple[float, float], radius: float) -> Image.Image:
    """A soft circular light, computed small then upscaled: a per-pixel loop at full size is
    needlessly slow for a shape this smooth."""
    small_w, small_h = size[0] // 8, size[1] // 8
    mask = Image.new("L", (small_w, small_h), 0)
    pixels = mask.load()
    cx, cy = center[0] / 8, center[1] / 8
    r = radius / 8
    for y in range(small_h):
        for x in range(small_w):
            distance = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if distance >= r:
                continue
            falloff = 1.0 - distance / r
            pixels[x, y] = int(255 * falloff**2)
    return mask.resize(size, Image.LANCZOS)


def draw_mark(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int) -> None:
    """The Lumia mark: a filled core inside eight rays, same shape as the favicon."""
    draw.ellipse(
        (cx - radius * 0.42, cy - radius * 0.42, cx + radius * 0.42, cy + radius * 0.42),
        fill=ACCENT,
    )
    for index in range(8):
        angle = index * (3.14159265 / 4)
        dx, dy = __import__("math").cos(angle), __import__("math").sin(angle)
        draw.line(
            (
                cx + dx * radius * 0.62,
                cy + dy * radius * 0.62,
                cx + dx * radius,
                cy + dy * radius,
            ),
            fill=ACCENT,
            width=6,
        )


def main() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    glow = Image.new("RGB", (WIDTH, HEIGHT), GLOW)
    image.paste(glow, (0, 0), radial_glow((WIDTH, HEIGHT), (250, 120), 620))

    draw = ImageDraw.Draw(image)
    bold = ImageFont.truetype(str(FONT_DIR / "DejaVuSans-Bold.ttf"), 86)
    regular = ImageFont.truetype(str(FONT_DIR / "DejaVuSans.ttf"), 34)
    small = ImageFont.truetype(str(FONT_DIR / "DejaVuSans.ttf"), 26)
    wordmark = ImageFont.truetype(str(FONT_DIR / "DejaVuSans-Bold.ttf"), 40)

    draw_mark(draw, 100, 92, 34)
    draw.text((150, 68), "Lumia", font=wordmark, fill=FOREGROUND)

    draw.text((96, 210), "Éclaircis tes flux.", font=bold, fill=FOREGROUND)
    draw.text((96, 330), "Lecteur RSS auto-hébergé. Il nettoie les articles,", font=regular, fill=MUTED)
    draw.text((96, 380), "les résume et apprend ce qui t'intéresse.", font=regular, fill=MUTED)

    draw.text((96, 520), "github.com/techmefr/lumia · AGPL-3.0", font=small, fill=ACCENT)

    image.save(OUTPUT, optimize=True)
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
