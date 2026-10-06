# Hema Creations — Jewellery Catalogue Kit (100% Free)

Turns your raw phone photos of bangles, hair clips, hair pins, saree pins,
necklaces (or any category you sell) into a professional, colourful A4
catalogue — background removed, permanent unique product codes, product
names, prices (including multi-item pricing), and your shop header on
every page. No paid software, no paid API. Runs 100% free on your PC.

Tested end-to-end with sample images — including adding new photos later,
duplicate photos, and long names/prices. Just plug in your real photos.

---

## What you need on your computer (one-time setup)

1. **Python** (free) — https://python.org (tick "Add to PATH" during install, Windows).
2. Open Command Prompt / Terminal inside this folder, then run:
   ```
   pip install -r requirements.txt
   ```
   Installs `rembg` (free AI background remover, offline after first use),
   `pillow` (image handling), `onnxruntime` (needed by rembg).
   First time you run Step 2 it auto-downloads a ~180MB AI model (one-time,
   needs internet). After that it works offline.

The `fonts/` folder is already included — nothing extra to download for the
catalogue's look.

---

## Folder structure

```
01_raw_images/            <- put your original phone photos here, sorted by category
    Bangles/
    Hair Clips/
    Hair Pins/
    Saree Pins/
    Necklace/
    (add more folders any time for any other category you sell)

00_duplicates_found/      <- auto-created by Step 1: exact duplicate photos it removed
01_raw_images_coded/      <- auto-created by Step 1 (renamed with codes)
02_processed_images/      <- auto-created by Step 2 (background removed)
03_output_catalogue/      <- auto-created by Step 3 (final A4 JPG pages)
products.csv              <- your editable price/name list (auto-created, keep editing it)
code_registry.csv          <- DO NOT EDIT - permanent record of which photo has which code
prefix_map.csv             <- DO NOT EDIT - permanent record of each category's code prefix
fonts/                     <- fonts used in the catalogue (included)
```

## The 3 steps

### Step 1 — Give every product a permanent unique code + find duplicates
1. Drop photos into `01_raw_images/<Category>/` folders (any filename is fine).
2. Run:
   ```
   python 1_prepare_codes.py
   ```
3. Creates/updates `products.csv` with columns: **Code, Category, Name,
   Rate, SourceFile**. Codes look like `BAN-001, BAN-002...` (Bangles),
   `HAC-001...` (Hair Clips), `HAP-001...` (Hair Pins), `SAP-001...`
   (Saree Pins), `NEC-001...` (Necklace) — prefix auto-generated from the
   folder name, always unique.
4. **Open `products.csv`** in Excel and fill in:
   - **Name** — shown under the photo, e.g. `Gold Plated Kada Bangle`.
     Long names automatically wrap to 2 lines (and shrink slightly) so
     they never overflow the card.
   - **Rate** — shown under the name.
     - A plain number like `250` is automatically shown as **Rs. 250/-**.
     - If one photo has multiple items at different prices, just type it
       out, e.g.: `1st clip Rs 110, 2nd clip Rs 220, 3rd clip Rs 250` —
       it automatically wraps onto as many lines as needed under that
       photo, shrinking slightly to fit if it's long.

   Save as .csv when done.

**Codes never change, ever** — even months later. If you add 10 new photos
to a category that already has 40 coded products, only the 10 new ones get
new codes (next free numbers); your existing 40 codes and the Name/Rate
you already typed for them stay exactly as they are. This works by
remembering every photo's exact content in `code_registry.csv` — never
delete or hand-edit that file.

**Duplicate photos are found automatically.** If the exact same photo file
appears more than once (e.g. you accidentally copied it twice, or into two
different category folders), only the first copy gets a code — the
repeat(s) are moved into `00_duplicates_found/<Category>/` and left out of
the catalogue completely, so you never print or price the same product
twice by mistake. If a photo merely *looks* similar to another one (e.g. a
slightly different-coloured version of the same design), it is **never**
auto-removed — you'll just see a `NOTE:` in the output asking you to take a
look, since it could easily be a genuinely different product.

### Step 2 — Remove background + professional studio background
```
python 2_remove_background.py
```
Removes the background using free local AI and places the product on a
soft ivory studio gradient with a gentle shadow.

**This step tells you exactly what it's doing and how long is left:**
- It prints `Processing 3 of 50: BAN-004 ... done (1.2s)` for every single
  photo as it works — if the command window looks blank/frozen right at
  the start, that is the **one-time AI model download** (~180MB), which
  shows no progress bar and can take a couple of minutes depending on your
  internet speed. After that first pause, each photo normally takes
  1–3 seconds on a normal laptop.
- **Rough timing**: 50 images ≈ 3–7 minutes total (mostly the one-time
  download); after the model is downloaded once, 50 images alone usually
  takes well under 2 minutes. 100 images ≈ 5–12 minutes the first time.
- **Already-processed photos are skipped automatically** on every re-run —
  so if you add 5 new photos to a 100-photo catalogue, re-running this
  only processes those 5, not all 100 again. (Delete a file from
  `02_processed_images/` if you ever want to force it to redo that one.)

Skip this step (copy `01_raw_images_coded` straight into
`02_processed_images`) if your photos already have a clean plain
background and you're short on time.

### Step 3 — Build the final colourful A4 catalogue
```
python 3_generate_catalogue.py
```
- Reads `products.csv` + `02_processed_images/`.
- **Groups products by category** — each category gets its own pages
  (**8 products per page, 2 columns × 4 rows**, large photos), never mixed
  with another category on the same page.
- Every page has:
  - A rich maroon-and-gold gradient header banner with your shop details
    in three different fonts (script "Jai Baba", serif "Hema Creations",
    clean sans-serif phone number).
  - The **category name in a big bold colourful banner** right under the
    header — every category automatically gets its own accent colour.
  - A **large product photo** with a rounded colour-matched frame border,
    a colourful "Code: XXX" ribbon tag above it, and shaded highlight
    boxes below it for the Name (white pill) and Rate (soft-tinted pill in
    the category's colour) — properly centred and aligned.
  - A footer with page numbers.
- Output files: `Bangles_Page_01.jpg`, `Saree_Pins_Page_05.jpg`, etc. — A4
  size, 2480×3508 px, 300 DPI, print-ready JPG.

Re-run any time you update `products.csv` — takes seconds.

If you'd prefer smaller photos and more products per page (10 instead of
8), open `3_generate_catalogue.py` and change `COLS, ROWS = 2, 4` to
`COLS, ROWS = 2, 5` near the top.

---

## Adding / editing / deleting categories (any time, no code changes)

Categories are simply the folder names inside `01_raw_images/`.

- **Add a category** → create a new folder, e.g. `01_raw_images/Earrings/`,
  add photos, re-run Steps 1 → 2 → 3. It gets its own code prefix and
  accent colour automatically.
- **Rename a category** → rename the folder, re-run Steps 1 → 2 → 3. Every
  photo inside keeps its existing code (codes are tied to the photo
  itself, not the folder name).
- **Delete a category** → delete (or move out) the folder, re-run Steps
  1 → 2 → 3. That category's rows simply won't appear in `products.csv`
  or the catalogue anymore; its code numbers are never reused.

For a **fixed colour** for a specific category instead of an automatic
one, open `3_generate_catalogue.py` and add/edit an entry in the
`CATEGORY_COLORS` dictionary near the top (entries already exist for
Bangles, Hair Clips, Hair Pins, Saree Pins, Necklace — copy that pattern).

---

## For your 100+ images — quickest workflow

1. Sort all photos into folders by category (the only manual step).
2. Copy those folders into `01_raw_images/`.
3. Run Step 1 → fill Name + Rate in `products.csv` → Step 2 → Step 3.
4. Whenever you get new stock, just drop new photos into the matching
   category folder and re-run all 3 steps — your existing codes, names,
   and prices are untouched, and only the new photos get processed.
5. Open `03_output_catalogue/` — your finished catalogue pages are ready
   to WhatsApp, print, or upload.

## Customizing the look
- **Category colours**: `CATEGORY_COLORS` / `AUTO_PALETTE` in `3_generate_catalogue.py`
- **Header banner colours**: `HEADER_BAND_TOP`, `HEADER_BAND_BOTTOM` in `3_generate_catalogue.py`
- **Shop name / phone text**: `SHOP_LINE_1`, `SHOP_NAME`, `SHOP_PHONE` in `3_generate_catalogue.py`
- **Product background shade** (Step 2): `BG_TOP`, `BG_BOTTOM` in `2_remove_background.py`
- **Products per page / grid**: `COLS`, `ROWS` in `3_generate_catalogue.py`
- **Duplicate sensitivity**: `WARN_DISTANCE` in `1_prepare_codes.py` (only
  affects the advisory `NOTE:` messages — exact duplicates are always
  auto-removed regardless of this setting)
- **Fonts**: swap any `.ttf` in the `fonts/` folder for another free Google
  Font of the same name, or point `poppins()` / `playfair()` / `dancing()`
  in `3_generate_catalogue.py` to a different file.

## Notes
- Tested and confirmed working with sample images, including: adding new
  photos to an existing category (old codes stay the same), an exact
  duplicate photo (auto-removed), a very long product name (wraps and
  shrinks to fit), and multi-item pricing text (wraps to multiple lines).
- 100% free, runs on your own PC — no subscriptions, no per-image charges,
  no watermarks.
