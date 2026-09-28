# -*- coding: utf-8 -*-
"""Input parsing: extract paths from --prompt, load product/category/attribute data."""
import glob
import json
import logging
import os
import re

log = logging.getLogger("agent")


def _to_dir(p):
    """If the path looks like a file (has an extension), return its parent dir."""
    base = os.path.basename(p)
    if "." in base and not p.endswith("/"):
        ext = base.rsplit(".", 1)[-1].lower()
        if ext in ("json", "txt", "md", "csv", "zip", "png", "jpg", "jpeg", "mp4", "mov"):
            return os.path.dirname(p) or p
    return p


def parse_prompt_paths(prompt):
    """Extract input and output directories from the natural-language prompt."""
    quoted = re.findall(r'[\"\x27](/[^\"\x27]+)[\"\x27]', prompt or '')
    unquoted = re.findall(r'(?<![:/])(/[A-Za-z0-9_\-./()]+)', prompt or '')
    paths = quoted if quoted else unquoted
    paths = [p.rstrip("/") or "/" for p in paths]
    input_dir, output_dir = None, None
    for p in paths:
        lp = p.lower()
        if input_dir is None and ("input" in lp or "dataset" in lp or "data" in lp):
            input_dir = _to_dir(p)
        elif output_dir is None and ("output" in lp or "result" in lp):
            output_dir = _to_dir(p)
    # fallback: first path = input, last distinct path = output
    if input_dir is None and paths:
        input_dir = _to_dir(paths[0])
    if output_dir is None:
        for p in reversed(paths):
            if _to_dir(p) != input_dir:
                output_dir = _to_dir(p)
                break
    return input_dir, output_dir


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("failed to load %s: %s", path, e)
        return None


def find_product_files(input_dir):
    """Locate product JSON files under input dir."""
    candidates = []
    for pattern in ("product_info/*.json", "product_info/**/*.json", "*.json", "**/*.json"):
        found = glob.glob(os.path.join(input_dir, pattern), recursive=True)
        for f in found:
            base = os.path.basename(f).lower()
            if "categor" in base or "attribute" in base or base.startswith("."):
                continue
            if f not in candidates:
                candidates.append(f)
        if candidates:
            break
    return sorted(candidates)


def find_support_files(input_dir):
    """Locate clothing_categories.json / clothing_attributes.json."""
    cats, attrs = None, None
    for root, _dirs, files in os.walk(input_dir):
        for fn in files:
            low = fn.lower()
            full = os.path.join(root, fn)
            if cats is None and "categor" in low and low.endswith(".json"):
                cats = full
            if attrs is None and "attribute" in low and low.endswith(".json"):
                attrs = full
    return cats, attrs


def extract_product(obj, source_file):
    """Normalize product JSON into a flat dict regardless of wrapper shape."""
    # unwrap ret.result.result / result / data wrappers
    cur = obj
    for _ in range(5):
        if isinstance(cur, dict) and len(cur) == 1:
            key = list(cur.keys())[0]
            if key in ("ret", "result", "data", "response"):
                cur = cur[key]
                continue
        if isinstance(cur, dict) and "result" in cur and "subject" not in cur:
            cur = cur["result"]
            continue
        break
    if not isinstance(cur, dict):
        return None
    prod = {
        "source_file": source_file,
        "platform": cur.get("platform") or "",
        "url": cur.get("url") or "",
        "offer_id": str(cur.get("offerId") or cur.get("offer_id") or ""),
        "subject": cur.get("subject") or cur.get("subjectTrans") or "",
        "subject_trans": cur.get("subjectTrans") or "",
        "category_id": cur.get("categoryId"),
        "category_name": cur.get("category_name") or "",
        "description_html": cur.get("description") or "",
        "attributes": cur.get("productAttribute") or [],
        "images": (cur.get("productImage") or {}).get("images") or [],
        "skus": cur.get("productSkuInfos") or [],
        "min_order_quantity": cur.get("minOrderQuantity"),
        "sale_info": cur.get("productSaleInfo") or {},
        "trade_score": cur.get("tradeScore"),
    }
    # description image urls
    desc_imgs = re.findall(r"<img[^>]+src='([^']+)'", prod["description_html"])
    if not desc_imgs:
        desc_imgs = re.findall(r'<img[^>]+src="([^"]+)"', prod["description_html"])
    prod["description_images"] = desc_imgs
    return prod


def select_target_product(prompt, product_files):
    """Pick the target product file: prompt hint > single file > first file."""
    if not product_files:
        return None
    if len(product_files) == 1:
        return product_files[0]
    # try to match an id mentioned in the prompt
    digits = set(re.findall(r"(\d{6,})", prompt or ""))
    for f in product_files:
        base = os.path.basename(f)
        for d in digits:
            if d in base:
                log.info("product selected by prompt hint: %s", base)
                return f
    raise ValueError(f'{len(product_files)} products found: specify the target product ID; never guess the first')


def load_input(prompt):
    """Full input loading. Returns dict with dirs, product, category tree, attribute table."""
    input_dir, output_dir = parse_prompt_paths(prompt)
    if not input_dir or not os.path.isdir(input_dir):
        raise RuntimeError(f"input directory not found or invalid: {input_dir!r} (prompt: {prompt[:200]!r})")
    if not output_dir:
        raise RuntimeError(f"output directory could not be determined from prompt: {prompt[:200]!r}")
    os.makedirs(output_dir, exist_ok=True)

    product_files = find_product_files(input_dir)
    target_file = select_target_product(prompt, product_files)
    if not target_file:
        raise RuntimeError(f"no product JSON found under {input_dir}")
    raw = _load_json(target_file)
    if raw is None:
        raise RuntimeError(f"target product file unreadable: {target_file}")
    product = extract_product(raw, target_file)
    if not product or not product["subject"]:
        raise RuntimeError(f"product extraction failed for {target_file}")
    log.info("loaded product: %s (offer %s, %d attrs, %d images, %d skus)",
             product["subject"][:40], product["offer_id"],
             len(product["attributes"]), len(product["images"]), len(product["skus"]))

    cat_file, attr_file = find_support_files(input_dir)
    categories = _load_json(cat_file) if cat_file else None
    attributes = _load_json(attr_file) if attr_file else None
    if cat_file:
        log.info("category tree loaded: %s", cat_file)
    if attr_file:
        log.info("attribute table loaded: %s", attr_file)

    return {
        "input_dir": input_dir,
        "output_dir": output_dir,
        "product": product,
        "categories": categories,
        "attributes": attributes,
    }
