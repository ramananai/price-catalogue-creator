"""
STEP 2 - Remove background & place on a professional studio background
-------------------------------------------------------------------------
WHAT THIS SCRIPT DOES:
  Reads every coded image from 01_raw_images_coded/<Category>/<CODE>.jpg
  Removes the background using AI (rembg - runs on your PC, free, offline
  after the first run) and places the clean product onto a soft
  professional studio background with a gentle drop shadow.
  Saves the result to 02_processed_images/<CODE>.jpg

SPEED / RE-RUNS:
  If a CODE has already been processed before (its output file already
  exists in 02_processed_images/), it is SKIPPED - so if you add 5 new
  photos to a 100-photo catalogue, re-running this only processes those 5
  new ones, not all 100 again. Delete a file from 02_processed_images/ if
  you want to force it to be redone.

HOW TO KNOW IT'S RUNNING / HOW LONG IT TAKES:
  This script prints "Processing N of TOTAL: CODE" for every single image
  as it works, with progress flushed immediately to the screen - so if you
  see nothing printing for a long time even on image 1, that first pause is
  the ONE-TIME AI model download (~180MB - a couple of minutes on a normal
  broadband connection, longer on slow internet). After that first image,
  each photo typically takes 3-8 seconds on a normal laptop with no
  graphics card - so 50 images usually finishes in about 3-7 minutes, and
  100 images in about 6-14 minutes. Exact speed depends on your PC.

RUN:
  python 2_remove_background.py

TIP:
  If your product photos already have a clean plain background and you are
  short on time, you can skip this script and just copy 01_raw_images_coded
  images straight into 02_processed_images - the catalogue will still look fine.
"""

import os
import sys
import time
from PIL import Image, ImageDraw, ImageFilter
from rembg import remove, new_session

CODED_DIR = "01_raw_images_coded"
OUT_DIR = "02_processed_images"
CANVAS_SIZE = 1000          # each product photo becomes 1000x1000 px, square
PRODUCT_SCALE = 0.80        # product occupies 80% of the canvas width/height

# ---- studio background style (edit these RGB values to change the look) ----
BG_TOP = (250, 247, 240)     # soft ivory
BG_BOTTOM = (232, 225, 210)  # warm light beige
SHADOW_OPACITY = 70          # 0-255, how dark the drop shadow is


def make_studio_background(size):
    canvas = Image.new("RGB", (size, size), BG_TOP)
    draw = ImageDraw.Draw(canvas)
    for y in range(size):
        t = y / size
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    return canvas


def add_shadow(canvas, product_rgba, paste_x, paste_y):
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    alpha = product_rgba.split()[-1]
    shadow_shape = Image.new("RGBA", product_rgba.size, (0, 0, 0, SHADOW_OPACITY))
    shadow_shape.putalpha(alpha)
    offset_y = int(product_rgba.height * 0.04)
    shadow.paste(shadow_shape, (paste_x, paste_y + offset_y), shadow_shape)
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    canvas.paste(shadow, (0, 0), shadow)


def process_one(session, src_path, dest_path):
    with Image.open(src_path) as im:
        im = im.convert("RGB")
        cutout = remove(im, session=session)  # RGBA, background transparent

    bbox = cutout.getbbox()
    if bbox:
        cutout = cutout.crop(bbox)

    target = int(CANVAS_SIZE * PRODUCT_SCALE)
    cutout.thumbnail((target, target), Image.LANCZOS)

    canvas_rgba = make_studio_background(CANVAS_SIZE).convert("RGBA")
    x = (CANVAS_SIZE - cutout.width) // 2
    y = (CANVAS_SIZE - cutout.height) // 2

    add_shadow(canvas_rgba, cutout, x, y)
    canvas_rgba.paste(cutout, (x, y), cutout)

    final = canvas_rgba.convert("RGB")
    final.save(dest_path, "JPEG", quality=92)


def main():
    if not os.path.isdir(CODED_DIR):
        print(f"'{CODED_DIR}' not found. Run 1_prepare_codes.py first.")
        return

    os.makedirs(OUT_DIR, exist_ok=True)

    # build the full worklist first, so we can show "N of TOTAL" and skip done ones
    jobs = []
    skipped = 0
    for category in sorted(os.listdir(CODED_DIR)):
        cat_folder = os.path.join(CODED_DIR, category)
        if not os.path.isdir(cat_folder):
            continue
        for filename in sorted(os.listdir(cat_folder)):
            if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                continue
            code = os.path.splitext(filename)[0]
            src_path = os.path.join(cat_folder, filename)
            dest_path = os.path.join(OUT_DIR, f"{code}.jpg")
            if os.path.isfile(dest_path):
                skipped += 1
                continue
            jobs.append((code, src_path, dest_path))

    print(f"Found {len(jobs)} new image(s) to process "
          f"({skipped} already processed earlier and will be kept as-is).")
    if not jobs:
        print("Nothing new to do. Run 3_generate_catalogue.py to build the catalogue.")
        return

    print("Loading AI background-removal model "
          "(FIRST RUN ONLY: this downloads a ~180MB file - please wait, "
          "this can take a couple of minutes and shows no progress bar)...")
    sys.stdout.flush()
    t_start = time.time()
    session = new_session("u2net")
    print(f"Model ready in {time.time() - t_start:.0f} seconds. Starting image processing...\n")
    sys.stdout.flush()

    total = len(jobs)
    done = 0
    t_process_start = time.time()
    for i, (code, src_path, dest_path) in enumerate(jobs, start=1):
        print(f"  Processing {i} of {total}: {code} ...", end=" ")
        sys.stdout.flush()
        t0 = time.time()
        try:
            process_one(session, src_path, dest_path)
            done += 1
            print(f"done ({time.time() - t0:.1f}s)")
        except Exception as e:
            print(f"FAILED ({e})")
        sys.stdout.flush()

    elapsed = time.time() - t_process_start
    avg = elapsed / total if total else 0
    print(f"\nDone. {done}/{total} new image(s) processed into '{OUT_DIR}/' "
          f"in {elapsed/60:.1f} minutes (avg {avg:.1f}s/image).")
    print("Next: run 3_generate_catalogue.py")


if __name__ == "__main__":
    main()
