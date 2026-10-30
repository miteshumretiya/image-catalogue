"""Create a folder of test images for demos and manual testing.

    python tools/make_sample_images.py sample_images 40

It makes colourful gradient images in a few sizes and formats, puts some in a
sub-folder, and adds one fake "broken.jpg" so you can see how the app handles
a file that isn't really an image.
"""
import os
import random
import sys

from PIL import Image, ImageDraw

SIZES = [(1920, 1080), (1600, 1200), (2400, 1600), (800, 600)]
FORMATS = [("jpg", "JPEG"), ("png", "PNG")]


def make_image(path, size, image_format, seed):
    rnd = random.Random(seed)
    start = [rnd.randint(0, 255) for _ in range(3)]
    end = [rnd.randint(0, 255) for _ in range(3)]
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    width, height = size
    for x in range(0, width, 4):
        t = x / width
        colour = tuple(int(start[i] + (end[i] - start[i]) * t) for i in range(3))
        draw.rectangle([x, 0, x + 4, height], fill=colour)
    for _ in range(15):
        cx, cy, r = rnd.randint(0, width), rnd.randint(0, height), rnd.randint(30, 200)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     fill=tuple(rnd.randint(0, 255) for _ in range(3)))
    img.save(path, image_format)


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "sample_images"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    os.makedirs(os.path.join(folder, "more"), exist_ok=True)

    for i in range(count):
        ext, fmt = FORMATS[i % len(FORMATS)]
        sub = "more" if i % 3 == 0 else ""
        path = os.path.join(folder, sub, f"photo_{i + 1:03d}.{ext}")
        make_image(path, SIZES[i % len(SIZES)], fmt, seed=i)

    with open(os.path.join(folder, "broken.jpg"), "w") as f:
        f.write("this is not really an image")
    with open(os.path.join(folder, "notes.txt"), "w") as f:
        f.write("not an image, should be ignored")

    print(f"Created {count} images (+1 broken file) in {os.path.abspath(folder)}")


if __name__ == "__main__":
    main()
