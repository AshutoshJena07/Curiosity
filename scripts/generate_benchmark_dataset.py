"""Generate a clean 4-class computer vision benchmark dataset locally.

Creates 4 visually distinct classes:
- airplane: Sky background with aerodynamic wing & fuselage contours
- automobile: Road/asphalt background with boxy chassis & wheel ellipses
- animal: Warm organic textures, curved contours, natural patterns
- document: Crisp paper background with horizontal text block lines

Usage: python scripts/generate_benchmark_dataset.py
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "vision_benchmark"

CLASSES = ["airplane", "automobile", "animal", "document"]
SAMPLES_PER_CLASS = 200

def generate_airplane(idx: int) -> Image.Image:
    # Sky backdrop with random clouds
    sky_colors = [(135, 206, 235), (100, 149, 237), (70, 130, 180), (176, 224, 230)]
    bg = random.choice(sky_colors)
    img = Image.new("RGB", (64, 64), color=bg)
    draw = ImageDraw.Draw(img)

    # Cloud puffs
    for _ in range(random.randint(1, 3)):
        cx, cy = random.randint(5, 55), random.randint(5, 30)
        draw.ellipse([cx, cy, cx + random.randint(10, 20), cy + random.randint(6, 12)], fill=(240, 248, 255))

    # Metallic airplane fuselage (elongated gray/white ellipse)
    fuselage_color = random.choice([(220, 220, 220), (200, 210, 225), (245, 245, 245)])
    fy = random.randint(25, 38)
    draw.ellipse([10, fy - 4, 54, fy + 4], fill=fuselage_color, outline=(100, 100, 100))

    # Wings
    draw.polygon([(26, fy), (18, fy - 14), (32, fy)], fill=fuselage_color, outline=(120, 120, 120))
    draw.polygon([(26, fy), (18, fy + 14), (32, fy)], fill=fuselage_color, outline=(120, 120, 120))
    # Tail fin
    draw.polygon([(46, fy), (54, fy - 10), (52, fy)], fill=(200, 50, 50))
    return img

def generate_automobile(idx: int) -> Image.Image:
    # Road / city ground
    img = Image.new("RGB", (64, 64), color=(60, 65, 75))
    draw = ImageDraw.Draw(img)

    # Asphalt horizon
    draw.rectangle([0, 0, 64, 30], fill=(120, 140, 160)) # horizon sky
    draw.rectangle([0, 30, 64, 64], fill=(50, 50, 50))   # road

    # Vehicle body
    body_color = random.choice([(220, 40, 40), (30, 100, 200), (240, 200, 20), (220, 220, 220), (30, 30, 30)])
    draw.rectangle([12, 34, 52, 46], fill=body_color, outline=(20, 20, 20))
    # Cabin roof
    draw.polygon([(18, 34), (24, 24), (42, 24), (48, 34)], fill=body_color, outline=(20, 20, 20))
    # Windshield glass
    draw.polygon([(20, 33), (25, 26), (40, 26), (45, 33)], fill=(160, 210, 240))

    # Wheels (black with silver rims)
    draw.ellipse([16, 42, 24, 50], fill=(10, 10, 10), outline=(180, 180, 180))
    draw.ellipse([40, 42, 48, 50], fill=(10, 10, 10), outline=(180, 180, 180))
    return img

def generate_animal(idx: int) -> Image.Image:
    # Natural green / forest / savanna background
    grass_colors = [(46, 125, 50), (67, 160, 71), (139, 195, 74), (161, 136, 127)]
    img = Image.new("RGB", (64, 64), color=random.choice(grass_colors))
    draw = ImageDraw.Draw(img)

    # Organic animal coat color
    coat_colors = [(139, 69, 19), (205, 133, 63), (245, 222, 179), (80, 50, 20), (230, 140, 60)]
    coat = random.choice(coat_colors)

    # Body ellipse
    bx = random.randint(20, 26)
    by = random.randint(30, 36)
    draw.ellipse([bx, by, bx + 24, by + 16], fill=coat, outline=(40, 25, 10))

    # Head ellipse
    hx = bx - 8
    hy = by - 10
    draw.ellipse([hx, hy, hx + 14, hy + 14], fill=coat, outline=(40, 25, 10))

    # Ears
    draw.polygon([(hx + 2, hy + 2), (hx + 5, hy - 6), (hx + 8, hy + 2)], fill=coat)
    draw.polygon([(hx + 7, hy + 2), (hx + 10, hy - 6), (hx + 13, hy + 2)], fill=coat)

    # Eyes & nose
    draw.point((hx + 4, hy + 6), fill=(0, 0, 0))
    draw.point((hx - 1, hy + 8), fill=(0, 0, 0))

    # 4 Legs
    for lx in [bx + 4, bx + 8, bx + 16, bx + 20]:
        draw.line([(lx, by + 14), (lx, by + 24)], fill=coat, width=2)
    return img

def generate_document(idx: int) -> Image.Image:
    # Clean paper background
    img = Image.new("RGB", (64, 64), color=(250, 250, 252))
    draw = ImageDraw.Draw(img)

    # Paper margin border
    draw.rectangle([6, 4, 58, 60], fill=(255, 255, 255), outline=(200, 205, 215))

    # Header bar
    header_color = random.choice([(30, 64, 175), (15, 118, 110), (120, 50, 50), (70, 70, 80)])
    draw.rectangle([10, 8, 38, 14], fill=header_color)

    # Text paragraph line textures
    ink_color = (60, 64, 75)
    line_y = 20
    while line_y < 54:
        line_w = random.randint(24, 44)
        draw.line([(10, line_y), (10 + line_w, line_y)], fill=ink_color, width=2)
        line_y += 5

    # Seal or stamp in bottom corner
    draw.ellipse([42, 42, 54, 54], outline=(220, 38, 38), width=1)
    return img

def main():
    print("=" * 60)
    print("Generating Local Vision Benchmark Dataset (4 Classes)...")
    print("=" * 60)
    random.seed(42)

    generators = {
        "airplane": generate_airplane,
        "automobile": generate_automobile,
        "animal": generate_animal,
        "document": generate_document,
    }

    total_created = 0
    for cls_name, gen_fn in generators.items():
        cls_dir = OUTPUT_DIR / cls_name
        cls_dir.mkdir(parents=True, exist_ok=True)
        for i in range(SAMPLES_PER_CLASS):
            img = gen_fn(i)
            img.save(cls_dir / f"{cls_name}_{i:04d}.png")
            total_created += 1
        print(f"[+] Created {SAMPLES_PER_CLASS} samples for class: '{cls_name}' -> {cls_dir}")

    print("=" * 60)
    print(f"SUCCESS: {total_created} benchmark images ready at: {OUTPUT_DIR}")
    print("You can train the model instantly on this dataset!")
    print("=" * 60)

if __name__ == "__main__":
    main()
