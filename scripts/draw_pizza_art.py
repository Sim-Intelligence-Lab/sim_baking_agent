"""Draw the pixel-art images used by the pizza recipe.

Run from the repository root (needs Pillow: `pip install pillow`):

    python scripts/draw_pizza_art.py

Item sprites are 16x16 grids, one character per pixel, so they are easy to
edit by hand. The end screens are drawn at 128x128 and scaled up 4x so they
stay crisp in the 512x512 game canvas. Re-running overwrites the PNGs in
baking/static/assets/.
"""

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "baking" / "static" / "assets"

OUTLINE = (74, 58, 50, 255)

# ---------------------------------------------------------------------------
# Item sprites
# ---------------------------------------------------------------------------

SPRITES = {
    "yeast": {
        "palette": {
            "k": OUTLINE,
            "y": (246, 206, 84, 255),
            "Y": (203, 158, 44, 255),
            "d": (226, 182, 62, 255),
            "r": (196, 64, 50, 255),
            "w": (255, 246, 228, 255),
        },
        "grid": [
            "................",
            "................",
            "..kkkkkkkkkkkk..",
            "..kYyYyYyYyYyk..",
            "..kyyyyyyyyyyk..",
            "..kyyyyyyyyyyk..",
            "..krrrrrrrrrrk..",
            "..krwrwrrwwrrk..",
            "..krwwwrrwrwrk..",
            "..krwrwrrwwrrk..",
            "..krrrrrrrrrrk..",
            "..kyyyyyyyyydk..",
            "..kyyyyyyyyddk..",
            "..kYyYyYyYyYyk..",
            "..kkkkkkkkkkkk..",
            "................",
        ],
    },
    "water": {
        "palette": {
            "k": (86, 110, 130, 255),
            "w": (226, 240, 248, 255),
            "h": (255, 255, 255, 255),
            "b": (150, 202, 240, 255),
            "B": (92, 160, 226, 255),
        },
        "grid": [
            "................",
            "................",
            "....kkkkkkk.....",
            "...kwwwwwwwk....",
            "...kwhbbbbwkkk..",
            "...kwhBBBBbk.k..",
            "...kbhBBBBbk.k..",
            "...kbhBBBBbk.k..",
            "...kbBBBBBbk.k..",
            "...kbBBBBBbkkk..",
            "...kbBBBBBbk....",
            "...kbBBBBBbk....",
            "...kbbbbbbbk....",
            "....kkkkkkk.....",
            "................",
            "................",
        ],
    },
    "olive_oil": {
        "palette": {
            "k": OUTLINE,
            "c": (176, 128, 78, 255),
            "g": (126, 158, 58, 255),
            "G": (82, 112, 40, 255),
            "h": (196, 220, 128, 255),
            "l": (250, 238, 204, 255),
            "o": (98, 120, 38, 255),
        },
        "grid": [
            "................",
            "......kkkk......",
            "......kcck......",
            "......kkkk......",
            "......kggk......",
            "......kggk......",
            ".....kggggk.....",
            "....kghgggGk....",
            "....kghgggGk....",
            "....kllllllk....",
            "....kllooolk....",
            "....klloollk....",
            "....kllllllk....",
            "....kghgggGk....",
            "....kkkkkkkk....",
            "................",
        ],
    },
    "tomato_sauce": {
        "palette": {
            "k": OUTLINE,
            "s": (214, 214, 220, 255),
            "S": (164, 164, 174, 255),
            "r": (200, 54, 42, 255),
            "R": (150, 36, 30, 255),
            "w": (255, 246, 232, 255),
            "v": (88, 150, 60, 255),
            "t": (226, 66, 48, 255),
            "T": (170, 40, 32, 255),
            "h": (255, 170, 150, 255),
        },
        "grid": [
            "................",
            "................",
            "....kkkkkkkk....",
            "...kssssssssk...",
            "...kSSSSSSSSk...",
            "...krrrrrrrRk...",
            "...kwwwvvwwwk...",
            "...kwwttttwwk...",
            "...kwtthttTwk...",
            "...kwttttTTwk...",
            "...kwwtTTTwwk...",
            "...kwwwwwwwwk...",
            "...krrrrrrrRk...",
            "...kSSSSSSSSk...",
            "....kkkkkkkk....",
            "................",
        ],
    },
    "mozzarella": {
        "palette": {
            "k": OUTLINE,
            "w": (252, 250, 240, 255),
            "h": (255, 255, 255, 255),
            "c": (222, 218, 200, 255),
            "B": (232, 140, 112, 255),
            "b": (206, 108, 82, 255),
        },
        "grid": [
            "................",
            "................",
            "......kkkk......",
            "....kkwwwwkk....",
            "...kwwhhwwwwk...",
            "...kwhhwwwwwk...",
            "..kwwhwwwwwwck..",
            "..kwwwwwwwwwck..",
            "..kwwwwwwwwcck..",
            "..kwwwwwwwwcck..",
            ".kBBBBBBBBBBBBk.",
            ".kbbbbbbbbbbbbk.",
            "..kbbbbbbbbbbk..",
            "...kbbbbbbbbk...",
            "....kkkkkkkk....",
            "................",
        ],
    },
    "basil": {
        "palette": {
            "k": (40, 74, 34, 255),
            "g": (96, 172, 70, 255),
            "G": (62, 128, 46, 255),
            "h": (170, 222, 130, 255),
            "s": (70, 120, 44, 255),
        },
        "grid": [
            "................",
            "......kkk.......",
            ".....kgggk......",
            ".....kghggk.....",
            ".....kghggk.....",
            "..kk..kgGk..kk..",
            ".kggk.kgGk.kggk.",
            "kghggkkgGkkgggGk",
            "kghgggksskggggGk",
            "..kGGkksskkGGk..",
            "...kk..ss..kk...",
            ".......ss.......",
            ".......ss.......",
            "........s.......",
            "................",
            "................",
        ],
    },
    "rolling_pin": {
        "palette": {
            "k": OUTLINE,
            "h": (240, 202, 150, 255),
            "w": (218, 168, 104, 255),
            "W": (180, 128, 72, 255),
            "H": (150, 98, 56, 255),
        },
        "grid": [
            "................",
            "................",
            "................",
            "................",
            "................",
            "...kkkkkkkkkk...",
            "...khhhhhhhhk...",
            ".kkkwwwwwwwwkkk.",
            "kHHkwwwwwwwwkHHk",
            ".kkkWwwwwwwWkkk.",
            "...kWWWWWWWWk...",
            "...kkkkkkkkkk...",
            "................",
            "................",
            "................",
            "................",
        ],
    },
    "pizza_pan": {
        "palette": {
            "k": (70, 70, 78, 255),
            "S": (146, 146, 156, 255),
            "s": (192, 192, 200, 255),
            "h": (230, 230, 236, 255),
            "D": (108, 108, 118, 255),
        },
        "grid": [
            "................",
            "................",
            "................",
            ".....kkkkkk.....",
            "...kkSSSSSSkk...",
            "..kSSssssssSSk..",
            ".kSshsssssssSSk.",
            ".kSsshssssssSSk.",
            ".kSSsssssssSSSk.",
            "..kSSSssssSSSk..",
            "..kDSSSSSSSSDk..",
            "...kkDDDDDDkk...",
            ".....kkkkkk.....",
            "................",
            "................",
            "................",
        ],
    },
    "pizza_cutter": {
        "palette": {
            "k": OUTLINE,
            "s": (210, 212, 220, 255),
            "S": (150, 152, 164, 255),
            "h": (250, 250, 255, 255),
            "o": (110, 112, 124, 255),
            "r": (206, 66, 58, 255),
            "R": (150, 44, 40, 255),
        },
        "grid": [
            "................",
            "........kkkkk...",
            ".......ksssssk..",
            "......kshsssssk.",
            "......kshssssSk.",
            "......ksssoosSk.",
            "......ksssoosSk.",
            "......kssssssSk.",
            ".....kksssssSk..",
            "....krrkSSSSk...",
            "...krRrkkkkk....",
            "..krRrk.........",
            ".krRrk..........",
            "krRrk...........",
            "kkkk............",
            "................",
        ],
    },
}


def draw_sprite(name: str, spec: dict) -> Image.Image:
    grid, palette = spec["grid"], spec["palette"]
    if len(grid) != 16 or any(len(row) != 16 for row in grid):
        raise ValueError(f"{name}: every sprite must be a 16x16 grid")
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(grid):
        for x, char in enumerate(row):
            if char != ".":
                image.putpixel((x, y), palette[char])
    return image


# ---------------------------------------------------------------------------
# End screens
# ---------------------------------------------------------------------------

GLYPHS = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "!": ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
    ".": ["00000", "00000", "00000", "00000", "00000", "00000", "00100"],
    " ": ["00000"] * 7,
}


def draw_text(image: Image.Image, text: str, y: int, color, shadow) -> None:
    width = len(text) * 6 - 1
    x0 = (image.width - width) // 2
    for offset, fill in (((1, 1), shadow), ((0, 0), color)):
        for i, char in enumerate(text):
            for gy, row in enumerate(GLYPHS[char]):
                for gx, bit in enumerate(row):
                    if bit == "1":
                        image.putpixel((x0 + i * 6 + gx + offset[0], y + gy + offset[1]), fill)


def draw_tablecloth(draw: ImageDraw.ImageDraw, top: int) -> None:
    red, light, mid = (214, 86, 72), (255, 241, 232), (236, 160, 146)
    for y in range(top, 128, 8):
        for x in range(0, 128, 8):
            row_red, col_red = (y // 8) % 2 == 0, (x // 8) % 2 == 0
            color = red if row_red and col_red else light if not (row_red or col_red) else mid
            draw.rectangle((x, y, x + 7, y + 7), fill=color)
    draw.line((0, top, 127, top), fill=(150, 60, 50))


def draw_pizza(draw: ImageDraw.ImageDraw, cx: int, cy: int, burnt: bool, rng: random.Random) -> None:
    radius = 31
    if burnt:
        crust, crust_dark, sauce = (78, 50, 34), (40, 26, 20), (104, 38, 28)
        cheese, cheese_light = (132, 98, 56), (156, 120, 70)
    else:
        crust, crust_dark, sauce = (226, 170, 96), (150, 96, 48), (204, 60, 40)
        cheese, cheese_light = (248, 222, 140), (255, 240, 186)

    # Wooden board with a small shadow, then the pizza on top.
    board = radius + 6
    draw.ellipse((cx - board, cy - board + 3, cx + board, cy + board + 3), fill=(120, 78, 44))
    draw.ellipse((cx - board, cy - board, cx + board, cy + board), fill=(184, 128, 74), outline=(120, 78, 44))
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=crust, outline=crust_dark)
    inner = radius - 6
    draw.ellipse((cx - inner, cy - inner, cx + inner, cy + inner), fill=sauce)

    # Melted cheese blobs, spread in rings so they cover the sauce evenly.
    for ring_radius, count in ((0, 1), (9, 6), (17, 10)):
        for i in range(count):
            angle = i * math.tau / count + rng.uniform(-0.25, 0.25)
            x = cx + math.cos(angle) * ring_radius + rng.uniform(-1.5, 1.5)
            y = cy + math.sin(angle) * ring_radius + rng.uniform(-1.5, 1.5)
            r = rng.randint(3, 5)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=cheese)
            draw.point((x - r + 2, y - r + 2), fill=cheese_light)

    if burnt:
        for _ in range(16):
            angle, dist = rng.uniform(0, math.tau), rng.uniform(0, radius - 2)
            x, y = cx + math.cos(angle) * dist, cy + math.sin(angle) * dist
            r = rng.randint(1, 2)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(28, 20, 18))
    else:
        for i in range(6):
            angle = i * math.tau / 6 + 0.5
            x, y = cx + math.cos(angle) * 13, cy + math.sin(angle) * 13
            draw.ellipse((x - 3, y - 2, x + 3, y + 2), fill=(70, 150, 60))
            draw.line((x - 2, y, x + 2, y), fill=(46, 112, 42))
        # Slice cuts.
        for i in range(4):
            angle = i * math.pi / 4 + 0.2
            dx, dy = math.cos(angle) * (radius - 1), math.sin(angle) * (radius - 1)
            draw.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=(170, 60, 40))


def paste_trang(image: Image.Image, x: int, y: int) -> None:
    sheet = Image.open(ASSETS / "char_spritesheet.png").convert("RGBA")
    image.alpha_composite(sheet.crop((0, 0, 32, 32)), (x, y))


def draw_end_screen(burnt: bool) -> Image.Image:
    rng = random.Random(7)
    image = Image.new("RGBA", (128, 128), (255, 248, 236, 255) if not burnt else (236, 232, 226, 255))
    draw = ImageDraw.Draw(image)
    draw_tablecloth(draw, 96)
    draw_pizza(draw, 52, 66, burnt, rng)

    if burnt:
        # Smoke puffs drifting up from the pizza.
        for x, y, r in ((44, 30, 5), (52, 25, 6), (61, 28, 5), (57, 19, 4), (47, 20, 3)):
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(120, 116, 112))
            draw.ellipse((x - r + 2, y - r + 1, x + r - 3, y + r - 3), fill=(160, 156, 150))
        draw_text(image, "BURNT PIZZA...", 6, (70, 60, 56, 255), (200, 194, 186, 255))
    else:
        # Steam curls.
        for x in (42, 52, 62):
            for i in range(8):
                image.putpixel((x + round(math.sin(i * 0.9) * 2), 26 - i), (255, 255, 255, 255))
                image.putpixel((x + 1 + round(math.sin(i * 0.9) * 2), 26 - i), (226, 220, 210, 255))
        draw_text(image, "PERFECT PIZZA!", 6, (196, 64, 44, 255), (250, 210, 160, 255))

    paste_trang(image, 92, 70)
    return image.resize((512, 512), Image.NEAREST)


def main() -> None:
    for name, spec in SPRITES.items():
        draw_sprite(name, spec).save(ASSETS / f"{name}.png")
    draw_end_screen(burnt=False).save(ASSETS / "success_pizza.png", optimize=True)
    draw_end_screen(burnt=True).save(ASSETS / "bad_pizza.png", optimize=True)
    print(f"Saved {len(SPRITES)} sprites and 2 end screens to {ASSETS}")


if __name__ == "__main__":
    main()
