"""
STEP 3 (NO PRICE VERSION) - Build A4 catalogue pages WITHOUT any price shown
--------------------------------------------------------------------------------
This is the exact same catalogue as 3_generate_catalogue.py (same header,
same colourful category banners, same big photo with frame border, same
Name highlight pill) EXCEPT the Rate/price is completely left out - not
shown, and no empty space is reserved for it either. The product photo
area simply gets that extra space instead, so photos end up slightly
bigger than the with-price version.

WHAT THIS SCRIPT DOES:
  Reads products.csv (Code, Category, Name, Rate, SourceFile) - the Rate
  column is read but ignored completely, it is never printed anywhere.
  Reads the matching processed photo from 02_processed_images/<CODE>.jpg
  Groups products BY CATEGORY, and builds a separate set of pages for each
  category (8 products per page, 2 columns x 4 rows), with the category
  name in a big bold colourful banner at the top of every page.

OUTPUT FOLDER:
  Saves pages inside:  03_output_catalogue/Without_Price_Catalogue/
  If that folder already exists (e.g. you already ran this once before),
  it just saves the new pages inside it - it will NOT create a second
  nested folder or complain, it simply (re)writes the files there.

RUN:
  python 3b_generate_catalogue_no_price.py
"""

import os
import csv
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CSV_PATH = "products.csv"
IMG_DIR = "02_processed_images"
OUT_DIR = os.path.join("03_output_catalogue", "Without_Price_Catalogue")
FONT_DIR = "fonts"

# ---- A4 at 300 DPI ----
PAGE_W, PAGE_H = 2480, 3508
MARGIN = 70

COLS, ROWS = 2, 4
PER_PAGE = COLS * ROWS

SHOP_LINE_1 = "Jai Baba"
SHOP_NAME = "Hema Creations"
SHOP_PHONE = "Cell: +91 9037070131"

CATEGORY_COLORS = {
    "Bangles":     {"accent": (168, 26, 60),   "accent2": (214, 74, 74),   "soft": (252, 233, 235)},
    "Hair Clips":  {"accent": (196, 60, 132),  "accent2": (233, 120, 170), "soft": (253, 233, 244)},
    "Hair_Clips":  {"accent": (196, 60, 132),  "accent2": (233, 120, 170), "soft": (253, 233, 244)},
    "Hair Pins":   {"accent": (110, 60, 170),  "accent2": (160, 120, 220), "soft": (240, 233, 252)},
    "Hair_Pins":   {"accent": (110, 60, 170),  "accent2": (160, 120, 220), "soft": (240, 233, 252)},
    "Saree Pins":  {"accent": (10, 120, 120),  "accent2": (60, 170, 165),  "soft": (225, 245, 244)},
    "Saree_Pins":  {"accent": (10, 120, 120),  "accent2": (60, 170, 165),  "soft": (225, 245, 244)},
    "Saree_Pin":   {"accent": (10, 120, 120),  "accent2": (60, 170, 165),  "soft": (225, 245, 244)},
    "Necklace":    {"accent": (25, 70, 150),   "accent2": (80, 130, 210),  "soft": (227, 236, 250)},
}
AUTO_PALETTE = [
    {"accent": (190, 120, 20),  "accent2": (230, 170, 70),  "soft": (252, 241, 222)},
    {"accent": (30, 130, 100),  "accent2": (80, 175, 140),  "soft": (225, 246, 238)},
    {"accent": (170, 45, 100),  "accent2": (215, 100, 150), "soft": (252, 232, 240)},
    {"accent": (60, 90, 170),   "accent2": (110, 140, 215), "soft": (231, 236, 251)},
]

HEADER_BAND_TOP = (78, 18, 30)
HEADER_BAND_BOTTOM = (150, 40, 45)
HEADER_TEXT_GOLD = (243, 205, 110)
HEADER_TEXT_WHITE = (255, 250, 240)

PAGE_BG = (255, 255, 255)
TEXT_DARK = (45, 35, 35)


# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------
def load_font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def playfair(size, weight="Bold"):
    f = load_font("PlayfairDisplay-Bold.ttf", size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def dancing(size, weight="Bold"):
    f = load_font("DancingScript-Bold.ttf", size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def poppins(size, weight="Regular"):
    files = {
        "Regular": "Poppins-Regular.ttf",
        "Medium": "Poppins-Medium.ttf",
        "SemiBold": "Poppins-SemiBold.ttf",
        "Bold": "Poppins-Bold.ttf",
    }
    return load_font(files.get(weight, "Poppins-Regular.ttf"), size)


# --------------------------------------------------------------------------
# Text measuring / wrapping / auto-shrink-to-fit helpers
# --------------------------------------------------------------------------
def text_w(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def line_height_of(font):
    ascent, descent = font.getmetrics()
    return ascent + descent


def draw_centered(draw, cx, y, text, font, fill):
    w = text_w(draw, text, font)
    draw.text((cx - w / 2, y), text, font=font, fill=fill)
    return w


def wrap_text(draw, text, font, max_width):
    """Greedy word-wrap."""
    if not text:
        return []
    rough_chunks = text.replace(", ", ",\n").split("\n")
    lines = []
    for chunk in rough_chunks:
        words = chunk.split()
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if not cur or text_w(draw, test, font) <= max_width:
                cur = test
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


def fit_text_block(draw, text, font_fn, weight, max_width, max_height,
                    start_size, min_size, max_lines_cap=4, step=3):
    """Try shrinking font size until the wrapped text fits within
    max_height. Returns (font, lines, line_height). If it still doesn't
    fit at min_size, truncates the last visible line with '...'."""
    size = start_size
    while size >= min_size:
        font = font_fn(size, weight)
        lines = wrap_text(draw, text, font, max_width)
        lh = int(line_height_of(font) * 1.18)
        if len(lines) <= max_lines_cap and lh * len(lines) <= max_height:
            return font, lines, lh
        size -= step

    font = font_fn(min_size, weight)
    lines = wrap_text(draw, text, font, max_width)
    lh = int(line_height_of(font) * 1.18)
    max_fit = max(1, max_height // lh)
    if len(lines) > max_fit:
        lines = lines[:max_fit]
        last = lines[-1]
        while last and text_w(draw, last + "...", font) > max_width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "..."
    return font, lines, lh


def draw_text_block(draw, lines, font, cx, top_y, line_height, fill):
    y = top_y
    for line in lines:
        draw_centered(draw, cx, y, line, font, fill)
        y += line_height
    return y


def category_colors(name, order_index):
    if name in CATEGORY_COLORS:
        return CATEGORY_COLORS[name]
    return AUTO_PALETTE[order_index % len(AUTO_PALETTE)]


def vertical_gradient(draw, box, top_color, bottom_color):
    x0, y0, x1, y1 = box
    h = y1 - y0
    if h <= 0:
        return
    for i in range(h):
        t = i / h
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
        draw.line([(x0, y0 + i), (x1, y0 + i)], fill=(r, g, b))


def draw_shop_header(page, draw):
    band_h = 250
    vertical_gradient(draw, (0, 0, PAGE_W, band_h), HEADER_BAND_TOP, HEADER_BAND_BOTTOM)
    draw.rectangle([0, band_h - 10, PAGE_W, band_h - 6], fill=HEADER_TEXT_GOLD)
    draw.rectangle([0, band_h, PAGE_W, band_h + 3], fill=(210, 175, 90))

    cx = PAGE_W / 2
    draw_centered(draw, cx, 14, SHOP_LINE_1, dancing(72, "Bold"), HEADER_TEXT_GOLD)
    draw_centered(draw, cx, 88, SHOP_NAME, playfair(100, "Bold"), HEADER_TEXT_WHITE)
    draw_centered(draw, cx, 195, SHOP_PHONE, poppins(40, "Medium"), HEADER_TEXT_GOLD)
    return band_h + 20


def draw_category_banner(page, draw, top_y, category_label, colors):
    banner_h = 115
    cx = PAGE_W / 2
    line_y = top_y + banner_h / 2
    f_cat = poppins(72, "Bold")
    label = category_label.upper()
    w = text_w(draw, label, f_cat)

    line_len = (PAGE_W - w - 2 * MARGIN - 140) / 2
    if line_len > 20:
        draw.line([(MARGIN, line_y), (MARGIN + line_len, line_y)], fill=colors["accent2"], width=5)
        draw.line([(PAGE_W - MARGIN - line_len, line_y), (PAGE_W - MARGIN, line_y)], fill=colors["accent2"], width=5)
        for dx in (-1, 1):
            dxp = (MARGIN + line_len + 30) if dx == -1 else (PAGE_W - MARGIN - line_len - 30)
            r = 10
            draw.polygon([(dxp, line_y - r), (dxp + r, line_y), (dxp, line_y + r), (dxp - r, line_y)], fill=colors["accent"])

    draw_centered(draw, cx, top_y + 15, label, f_cat, colors["accent"])
    return top_y + banner_h + 15


def rounded_card_with_shadow(page, box, radius, colors):
    x0, y0, x1, y1 = box
    shadow_layer = Image.new("RGBA", page.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_layer)
    offset = 16
    sd.rounded_rectangle([x0 + offset, y0 + offset, x1 + offset, y1 + offset], radius=radius, fill=(60, 40, 40, 100))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(20))
    page.paste(shadow_layer, (0, 0), shadow_layer)

    draw = ImageDraw.Draw(page)
    draw.rounded_rectangle(box, radius=radius, fill=(255, 255, 255))
    draw.rounded_rectangle(box, radius=radius, outline=colors["accent"], width=9)
    draw.rounded_rectangle([x0 + 12, y0 + 12, x1 - 12, y1 - 12], radius=max(radius - 12, 0), outline=colors["accent2"], width=2)


def draw_code_ribbon(page, draw, box, radius, code, colors, font):
    x0, y0, x1, y1 = box
    ribbon_h = 50
    ribbon_box = [x0 + 9, y0 + 9, x1 - 9, y0 + 9 + ribbon_h]
    mask = Image.new("L", page.size, 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle(ribbon_box, radius=radius - 6, fill=255)
    mdraw.rectangle([ribbon_box[0], ribbon_box[1] + ribbon_h / 2, ribbon_box[2], ribbon_box[3]], fill=255)
    solid = Image.new("RGB", page.size, colors["accent"])
    page.paste(solid, (0, 0), mask)
    draw_centered(draw, (x0 + x1) / 2, ribbon_box[1] + 7, f"Code: {code}", font, (255, 255, 255))
    return ribbon_box[3]


def rounded_paste_with_frame(page, img, top_left, colors):
    x, y = top_left
    w, h = img.size
    frame_pad = 10
    frame_box = [x - frame_pad, y - frame_pad, x + w + frame_pad, y + h + frame_pad]

    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=20, fill=255)
    page.paste(img, (x, y), mask)

    draw = ImageDraw.Draw(page)
    draw.rounded_rectangle(frame_box, radius=26, outline=colors["accent2"], width=4)
    return frame_box


def draw_highlight_pill(draw, cx, top_y, width, height, fill, outline, radius=18):
    box = [cx - width / 2, top_y, cx + width / 2, top_y + height]
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2)
    return box


def draw_footer(page, draw, page_no, total_pages, colors):
    y = PAGE_H - 55
    draw.line([(MARGIN, y - 15), (PAGE_W - MARGIN, y - 15)], fill=colors["accent2"], width=3)
    draw_centered(draw, PAGE_W / 2, y, f"Hema Creations   |   Page {page_no} of {total_pages}", poppins(34, "Medium"), (120, 100, 100))


def build_pages(products):
    os.makedirs(OUT_DIR, exist_ok=True)   # if it already exists, files just save inside it - no error, no duplicate folder

    by_category = defaultdict(list)
    category_order = []
    for p in products:
        cat = p["Category"]
        if cat not in by_category:
            category_order.append(cat)
        by_category[cat].append(p)

    total_pages = sum((len(by_category[c]) + PER_PAGE - 1) // PER_PAGE for c in category_order)

    page_no = 0
    for cat_index, category in enumerate(category_order):
        colors = category_colors(category, cat_index)
        items = by_category[category]

        for chunk_start in range(0, len(items), PER_PAGE):
            chunk = items[chunk_start:chunk_start + PER_PAGE]
            page_no += 1

            page = Image.new("RGB", (PAGE_W, PAGE_H), PAGE_BG)
            draw = ImageDraw.Draw(page)

            header_bottom = draw_shop_header(page, draw)
            grid_top = draw_category_banner(page, draw, header_bottom, category, colors)

            grid_bottom = PAGE_H - 100
            cell_w = (PAGE_W - 2 * MARGIN) // COLS
            cell_h = (grid_bottom - grid_top) // ROWS

            for idx, prod in enumerate(chunk):
                col = idx % COLS
                row = idx // COLS
                cell_x = MARGIN + col * cell_w
                cell_y = grid_top + row * cell_h

                card_pad = 16
                box = [cell_x + card_pad, cell_y + card_pad, cell_x + cell_w - card_pad, cell_y + cell_h - card_pad]
                rounded_card_with_shadow(page, box, radius=36, colors=colors)
                draw = ImageDraw.Draw(page)

                code = prod["Code"]
                name = (prod.get("Name") or "").strip()
                # NOTE: Rate is intentionally never read/shown in this version.
                img_path = os.path.join(IMG_DIR, f"{code}.jpg")

                inner_w = (box[2] - box[0]) - 90
                cx = cell_x + cell_w / 2

                ribbon_font = poppins(34, "Bold")
                ribbon_bottom = draw_code_ribbon(page, draw, box, 36, code, colors, ribbon_font)

                # ---- measure Name FIRST at its natural size, so the
                #      product photo gets whatever space is left over.
                #      There is no Rate block at all in this version, so
                #      the photo gets that space too - it ends up bigger
                #      than the with-price catalogue. ----
                if name:
                    name_font, name_lines, name_lh = fit_text_block(
                        draw, name, poppins, "SemiBold",
                        max_width=inner_w, max_height=140,
                        start_size=36, min_size=22, max_lines_cap=2,
                    )
                    name_block_h = name_lh * len(name_lines) + 16
                else:
                    name_font, name_lines, name_lh, name_block_h = None, [], 0, 0

                bottom_pad = 14
                gap_after_ribbon = 10
                gap_between_pills = 8

                thumb_max = (box[3] - ribbon_bottom) - gap_after_ribbon - name_block_h - bottom_pad
                thumb_max = int(max(thumb_max, 210))
                thumb_max = min(thumb_max, int(inner_w) + 40)

                photo_top = ribbon_bottom + gap_after_ribbon

                if os.path.isfile(img_path):
                    with Image.open(img_path) as prod_img:
                        prod_img = prod_img.copy()
                        prod_img.thumbnail((thumb_max - 20, thumb_max - 20), Image.LANCZOS)
                        ix = cell_x + (cell_w - prod_img.width) // 2
                        iy = int(photo_top + (thumb_max - prod_img.height) // 2)
                        frame_box = rounded_paste_with_frame(page, prod_img, (ix, iy), colors)
                        draw = ImageDraw.Draw(page)
                        img_bottom = frame_box[3]
                else:
                    ph_box = [box[0] + 40, photo_top, box[2] - 40, photo_top + thumb_max]
                    draw.rounded_rectangle(ph_box, radius=20, fill=(235, 235, 235))
                    msg = "image missing"
                    mw = text_w(draw, msg, ribbon_font)
                    draw.text(((ph_box[0] + ph_box[2]) / 2 - mw / 2, (ph_box[1] + ph_box[3]) / 2), msg, font=ribbon_font, fill=(150, 150, 150))
                    img_bottom = ph_box[3]

                y = img_bottom + gap_between_pills

                if name_lines:
                    pill_w = min(inner_w + 50, cell_w - 2 * card_pad - 24)
                    pill_box = draw_highlight_pill(draw, cx, y, pill_w, name_block_h, (255, 255, 255), colors["accent2"])
                    text_top = pill_box[1] + (name_block_h - name_lh * len(name_lines)) / 2
                    draw_text_block(draw, name_lines, name_font, cx, text_top, name_lh, TEXT_DARK)

                # ---- no Rate pill drawn here at all, and no space was
                #      reserved for one above - this is the only real
                #      difference from 3_generate_catalogue.py ----

            draw_footer(page, draw, page_no, total_pages, colors)

            out_path = os.path.join(OUT_DIR, f"{category.replace(' ', '_')}_Page_{page_no:02d}.jpg")
            page.save(out_path, "JPEG", quality=95, dpi=(300, 300))
            print(f"  saved {out_path}  ({len(chunk)} products, category: {category})")

    print(f"\nDone. {page_no} catalogue page(s) saved in '{OUT_DIR}/'.")


def load_products():
    if not os.path.isfile(CSV_PATH):
        raise SystemExit(f"'{CSV_PATH}' not found. Run 1_prepare_codes.py first.")
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    products = load_products()
    if not products:
        print("products.csv is empty. Run 1_prepare_codes.py first.")
        return
    build_pages(products)


if __name__ == "__main__":
    main()
