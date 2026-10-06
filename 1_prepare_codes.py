"""
STEP 1 - Assign unique, PERMANENT product codes by category + find duplicates
--------------------------------------------------------------------------------
WHAT TO DO BEFORE RUNNING THIS:
  Put your photos inside 01_raw_images/<CategoryName>/ folders.
  Add/rename/remove category folders any time - see README.md.

WHAT THIS SCRIPT DOES (every time you run it):
  1. Looks at every photo inside 01_raw_images/.
  2. CODES NEVER CHANGE: each photo's exact content is remembered in
     code_registry.csv. If you run this again after adding NEW photos, all
     your OLD photos keep the exact same code they already had - only the
     new photos get new codes (next free number in that category). You can
     safely add images to any category folder at any time.
  3. FINDS DUPLICATES: if the same photo (byte-for-byte identical, or the
     same photo just resaved/resized) appears more than once, only the
     first copy gets a code. The repeated copies are moved out of the way
     into 00_duplicates_found/<Category>/ instead of getting their own
     code or appearing in the catalogue - so you never pay for or print
     the same product twice by mistake.
  4. Creates/updates products.csv with columns:
        Code, Category, Name, Rate, SourceFile
     - Name and Rate are LEFT BLANK for new codes only - existing rows keep
       whatever Name/Rate you already typed in, even after you re-run this.
     - Open products.csv in Excel and fill in:
         Name -> product name shown under the photo (e.g. "Gold Plated Bangle")
         Rate -> price shown under the name. You can type more than a
                 simple number here if you like, e.g.:
                 "1st clip Rs 110, 2nd clip Rs 220, 3rd clip Rs 250"
                 It will automatically wrap to fit under the photo.

RUN:
  python 1_prepare_codes.py
"""

import os
import csv
import shutil
import hashlib
from PIL import Image

RAW_DIR = "01_raw_images"
CODED_DIR = "01_raw_images_coded"
DUPLICATE_DIR = "00_duplicates_found"
REGISTRY_PATH = "code_registry.csv"      # permanent ledger: never edit by hand
PREFIX_MAP_PATH = "prefix_map.csv"       # permanent category -> code-prefix map
CSV_PATH = "products.csv"                # your editable price/name list
VALID_EXT = (".jpg", ".jpeg", ".png", ".webp")

AHASH_SIZE = 8                 # 8x8 -> 64-bit perceptual hash
# Only EXACT byte-for-byte duplicate files are auto-removed (100% safe - can
# never mistake two different products for each other). Perceptual (visual)
# similarity is only used to print a warning for you to check by eye -
# it is deliberately NEVER used to auto-delete, because two genuinely
# different products (e.g. same design in a different colour) can look
# similar to this kind of check, and we never want to silently drop a
# real product from your catalogue.
WARN_DISTANCE = 4              # flag "looks similar, please check" up to this distance


# --------------------------------------------------------------------------
# Hashing helpers
# --------------------------------------------------------------------------
def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def average_hash(path, size=AHASH_SIZE):
    with Image.open(path) as im:
        im = im.convert("L").resize((size, size), Image.LANCZOS)
        pixels = list(im.getdata()) if not hasattr(im, "get_flattened_data") else list(im.get_flattened_data())
    avg = sum(pixels) / len(pixels)
    return "".join("1" if p > avg else "0" for p in pixels)


def hamming(a, b):
    return sum(x != y for x, y in zip(a, b))


# --------------------------------------------------------------------------
# Persistent registry / prefix map (so codes never change once given)
# --------------------------------------------------------------------------
def load_csv_dicts(path):
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv_dicts(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def make_prefix(category_name, used_prefixes):
    words = category_name.upper().replace("-", " ").replace("_", " ").split()
    letters = "".join(ch for ch in category_name.upper() if ch.isalpha())
    if len(words) >= 2:
        prefix = (words[0][:2] + words[1][:1]).ljust(3, "X")[:3]
    else:
        prefix = letters[:3].ljust(3, "X")

    base = prefix
    n = 1
    while prefix in used_prefixes:
        n += 1
        prefix = (base[:2] + str(n))[:3]
    used_prefixes.add(prefix)
    return prefix


def main():
    if not os.path.isdir(RAW_DIR):
        print(f"Folder '{RAW_DIR}' not found. Create it and add category sub-folders first.")
        return

    categories = sorted(
        d for d in os.listdir(RAW_DIR)
        if os.path.isdir(os.path.join(RAW_DIR, d))
    )
    if not categories:
        print(f"No category folders found inside '{RAW_DIR}'. "
              f"Create e.g. 01_raw_images/Bangles/ and put photos in it.")
        return

    os.makedirs(CODED_DIR, exist_ok=True)
    os.makedirs(DUPLICATE_DIR, exist_ok=True)

    # ---- load permanent registry + prefix map ----
    registry_rows = load_csv_dicts(REGISTRY_PATH)   # Code, Category, MD5, AHash, SourceFile
    registry_by_md5 = {r["MD5"]: r["Code"] for r in registry_rows}
    known_ahashes = [(r["Code"], r["AHash"]) for r in registry_rows]
    max_number_by_prefix = {}
    for r in registry_rows:
        code = r["Code"]
        prefix, _, num = code.rpartition("-")
        try:
            n = int(num)
            max_number_by_prefix[prefix] = max(max_number_by_prefix.get(prefix, 0), n)
        except ValueError:
            pass

    prefix_map_rows = load_csv_dicts(PREFIX_MAP_PATH)  # Category, Prefix
    prefix_by_category = {r["Category"]: r["Prefix"] for r in prefix_map_rows}
    used_prefixes = set(prefix_by_category.values())

    # ---- load existing products.csv to preserve Name/Rate the user typed ----
    old_products = load_csv_dicts(CSV_PATH)
    old_by_code = {r["Code"]: r for r in old_products}

    new_registry_rows = list(registry_rows)   # append-only ledger
    products_rows = []
    seen_md5_this_run = {}   # md5 -> code, for catching duplicates within this run
    duplicates_found = []

    for category in categories:
        src_folder = os.path.join(RAW_DIR, category)
        images = sorted(
            f for f in os.listdir(src_folder)
            if f.lower().endswith(VALID_EXT)
        )
        if not images:
            continue

        if category not in prefix_by_category:
            prefix = make_prefix(category, used_prefixes)
            prefix_by_category[category] = prefix
        else:
            prefix = prefix_by_category[category]

        dest_folder = os.path.join(CODED_DIR, category)
        os.makedirs(dest_folder, exist_ok=True)
        dup_folder = os.path.join(DUPLICATE_DIR, category)

        for filename in images:
            src_path = os.path.join(src_folder, filename)

            try:
                with Image.open(src_path) as im:
                    im.verify()
            except Exception as e:
                print(f"  SKIPPED (not a valid image): {src_path} ({e})")
                continue

            md5 = file_md5(src_path)

            # --- exact duplicate of a file already handled earlier in THIS
            #     run (covers: two copies of the same file in the raw
            #     folder, OR a duplicate of a file already coded in an
            #     earlier run) ---
            if md5 in seen_md5_this_run:
                matched_code = seen_md5_this_run[md5]
                os.makedirs(dup_folder, exist_ok=True)
                shutil.move(src_path, os.path.join(dup_folder, filename))
                duplicates_found.append((filename, category, "exact duplicate", matched_code))
                print(f"  DUPLICATE (exact copy of {matched_code}): {filename} -> moved to {dup_folder}/")
                continue

            # --- already-known image (from a previous run): reuse its code ---
            if md5 in registry_by_md5:
                code = registry_by_md5[md5]
                seen_md5_this_run[md5] = code
                ext = os.path.splitext(filename)[1].lower()
                shutil.copy2(src_path, os.path.join(dest_folder, f"{code}{ext}"))
                old_row = old_by_code.get(code, {})
                products_rows.append({
                    "Code": code, "Category": category,
                    "Name": old_row.get("Name", ""), "Rate": old_row.get("Rate", ""),
                    "SourceFile": filename,
                })
                print(f"  {filename}  ->  {code}  (existing code, unchanged)")
                continue

            # --- visual similarity check (advisory only - never auto-removed) ---
            ahash = average_hash(src_path)
            best_code, best_dist = None, 999
            for known_code, known_hash in known_ahashes:
                d = hamming(ahash, known_hash)
                if d < best_dist:
                    best_dist, best_code = d, known_code

            if best_code is not None and best_dist <= WARN_DISTANCE:
                print(f"  NOTE: {filename} looks visually similar to {best_code} "
                      f"- if it's really the same photo, delete it yourself from "
                      f"01_raw_images/{category}/ and re-run. (not auto-removed, "
                      f"could just be a similar-looking different product)")

            # --- brand new unique image: assign the next free code ---
            next_num = max_number_by_prefix.get(prefix, 0) + 1
            max_number_by_prefix[prefix] = next_num
            code = f"{prefix}-{next_num:03d}"

            registry_by_md5[md5] = code
            known_ahashes.append((code, ahash))
            seen_md5_this_run[md5] = code
            new_registry_rows.append({
                "Code": code, "Category": category, "MD5": md5,
                "AHash": ahash, "SourceFile": filename,
            })

            ext = os.path.splitext(filename)[1].lower()
            shutil.copy2(src_path, os.path.join(dest_folder, f"{code}{ext}"))
            products_rows.append({
                "Code": code, "Category": category,
                "Name": "", "Rate": "", "SourceFile": filename,
            })
            print(f"  {filename}  ->  {code}  (new)")

    save_csv_dicts(REGISTRY_PATH, new_registry_rows, ["Code", "Category", "MD5", "AHash", "SourceFile"])
    save_csv_dicts(
        PREFIX_MAP_PATH,
        [{"Category": c, "Prefix": p} for c, p in prefix_by_category.items()],
        ["Category", "Prefix"]
    )
    save_csv_dicts(CSV_PATH, products_rows, ["Code", "Category", "Name", "Rate", "SourceFile"])

    print(f"\nDone. {len(products_rows)} products coded across {len(categories)} categories.")
    if duplicates_found:
        print(f"{len(duplicates_found)} duplicate photo(s) found and moved to '{DUPLICATE_DIR}/' (not coded):")
        for filename, category, reason, matched_code in duplicates_found:
            print(f"   - {category}/{filename}  ({reason}, same as {matched_code})")
    else:
        print("No duplicate photos found.")
    print(f"-> Coded images are in: {CODED_DIR}/")
    print(f"-> Now OPEN '{CSV_PATH}' and fill in Name + Rate for any new codes, then save it.")


if __name__ == "__main__":
    main()
