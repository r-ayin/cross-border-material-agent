# -*- coding: utf-8 -*-
"""Six source-locked image jobs with bounded, fail-closed quality checks.

Only accepted images receive canonical filenames. Unavailable checks retain a
*.needs_review asset and explicit metadata, never a qualified delivery filename.
No generated image becomes the authoritative source for another image.
"""
import logging
import os
import struct
import time
import zlib
from concurrent.futures import ThreadPoolExecutor

from .aesthetic_critic import check_compliance, score_image_url, validate_critique
from .creative_plan import image_brief
from .dsapi import ApiError, TaskAcceptedError, download_file, extract_urls_from_output

log = logging.getLogger("agent")

MAIN_MODEL_PRIMARY = "qwen-image-3.0-pro"
MAIN_MODEL_FALLBACKS = ["wan2.7-image-pro", "wan2.7-image"]
DETAIL_MODELS = ["wan2.7-image-pro", "wan2.7-image", "qwen-image-3.0-pro"]
MAIN_SIZE = "1328*1328"
DETAIL_SIZES = [MAIN_SIZE] * 5
MAX_SOURCE_REFS = 5
MAX_CANDIDATES_PER_SLOT = 3
WHITE_BG_NEAR = 245
WHITE_BG_MIN_RATIO = 0.9
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 4 * 1024 * 1024
MAX_PNG_DECOMPRESSED_BYTES = 20 * 1024 * 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

WHITE_BG_STRESS = (
    " The entire background must be FLAT SOLID PURE WHITE (RGB 255,255,255), "
    "unbroken to all four borders: no gradient, vignette, props or floor line. "
    "Only a soft shadow directly under the product is allowed."
)
COMPLIANCE_STRESS = (
    " Remove all text, watermark, logo, promotional stickers, price tags, "
    "borders, frames and collage overlays. Preserve the product and the requested setting."
)
COMMON_NEGATIVE_PROMPT = (
    "text, watermark, logo, signature, border, collage, price tag, promotional "
    "symbols, distorted product, blurry, deformed, invented back construction, "
    "invented seams, invented closures, changed color, changed pattern"
)
MAIN_NEGATIVE_PROMPT = COMMON_NEGATIVE_PROMPT + (
    ", colored background, textured background, indoor scene, outdoor scene, "
    "gradient, vignette, props, human model, extra products"
)
DEFAULT_DETAIL_THEMES = (
    "Overall selling point: show the whole product with emphasis on its most "
    "distinctive SOURCE-VISIBLE design feature; communicate visually, without claims or labels.",
    "Craftsmanship: one close-up of an actually visible seam, edge, finish or "
    "construction detail. If no fine construction is resolved, use a wider source-supported "
    "crop rather than inventing stitches or hardware.",
    "Material appearance: a close-up showing only SOURCE-VISIBLE surface texture, "
    "drape or finish. Do not infer fiber identity, composition, hidden layers or microscopic weave.",
    "Lifestyle context: a tasteful real indoor or outdoor everyday setting appropriate "
    "for the product, not a white cutout backdrop. Keep the product recognizable. "
    "It may be displayed naturally without a person; if worn, use normal complete, "
    "modest styling and keep other clothing secondary, never part of the advertised product.",
    "Complete overview: show the entire product, uncropped, in ONE source-supported "
    "view with clear silhouette and proportions. Neutral uncluttered setting, no "
    "multi-angle grid, no invented rear or side view, no measurement diagram.",
)
DETAIL_ROLES = ("overall_selling_point", "craftsmanship", "material_appearance",
                "lifestyle", "complete_overview")


def _normalize_refs(ref_image_url, max_refs=MAX_SOURCE_REFS):
    if isinstance(ref_image_url, str):
        ref_image_url = [ref_image_url]
    refs = []
    for url in ref_image_url or []:
        if not isinstance(url, str):
            continue
        url = url.strip()
        if url.startswith(("https://", "http://")) and url not in refs:
            refs.append(url)
    return refs[:max_refs]


def build_image_jobs(ctx):
    """Pure offline plan: exactly one main + five fixed-role details.

    Does not access clients, budget, clock, filesystem or mutate ctx. The original
    source URLs are authoritative even if ctx contains an older generated anchor.
    Style themes cannot shorten the plan or override these factual responsibilities.
    """
    product = ctx.get("product") or {}
    refs = _normalize_refs(product.get("images"))
    subject = str(product.get("subject") or "the product in the source references")
    base = (
        f"E-commerce photograph of the source product labeled: {subject}. "
        "The ORIGINAL SOURCE REFERENCE IMAGES are the sole visual authority. "
        "Preserve the exact source-visible color, pattern, silhouette, proportions "
        "and construction. Show only source-supported views and details; never "
        "invent an unseen back, side, seam, closure or accessory. Do not invent "
        "dimensions, measurements, material composition, percentages or performance "
        "claims. Do not use generated images or descriptions as product evidence. "
        "One photograph, no text, watermark, logo, border, collage or promotional symbols. "
        "Sharp focus and natural color. "
    )
    profile = ctx.get("style_profile") or {}
    lighting = profile.get("lighting_refinement")
    if isinstance(lighting, str) and lighting.strip():
        base += ("Optional lighting inspiration, subordinate to source colors and the "
                 "slot-specific background: " + lighting.strip() + ". ")
    main_prompt = (
        base + "Main product image: exactly ONE complete product, flat lay or hanging "
        "product-only presentation; no human model and no unrelated clothing or accessories. "
        "Keep the entire product visible, centered in a square composition. " + WHITE_BG_STRESS
    )
    jobs = [{
        "name": "main_image", "role": "main", "prompt": main_prompt,
        "ref": list(refs), "size": MAIN_SIZE,
        "chain": [MAIN_MODEL_PRIMARY] + list(MAIN_MODEL_FALLBACKS),
        "dest": os.path.join(ctx["output_dir"], "main_image"),
        "white_bg": True, "negative_prompt": MAIN_NEGATIVE_PROMPT,
    }]
    style = str(profile.get('image_modifiers') or '')
    style_note = (' Styling inspiration for lighting and environment only: ' + style +
                  ' Never change product color, texture or slot responsibilities.') if style else ''
    for i, (role, theme) in enumerate(zip(DETAIL_ROLES, DEFAULT_DETAIL_THEMES), 1):
        # Minimal-studio wording must not turn the lifestyle slot into another cutout.
        accent = '' if role == 'lifestyle' and profile.get('style_name') == 'minimal-studio' else style_note
        jobs.append({
            "name": f"detail_image_{i}", "role": role,
            "prompt": base + theme + accent, "ref": list(refs), "size": DETAIL_SIZES[i - 1],
            "chain": list(DETAIL_MODELS),
            "dest": os.path.join(ctx["output_dir"], f"detail_image_{i}"),
            "white_bg": False, "negative_prompt": COMMON_NEGATIVE_PROMPT,
        })
    for job in jobs:
        brief = image_brief(job['role'])
        job['brief'] = brief
        job['prompt'] += ' ' + brief['prompt']
    return jobs


def _require_time(deadline):
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError("image deadline exceeded")


def _endpoints():
    return ["/services/aigc/multimodal-generation/generation",
            "/services/aigc/text2image/image-synthesis"]


def submit_image_task(task_client, model, prompt, ref_image_url, size, deadline,
                      negative_prompt=None):
    """Probe reference-preserving layouts; never silently drop all references."""
    refs = _normalize_refs(ref_image_url)
    if not refs:
        raise ApiError("source reference URLs are required")
    last_err = None
    for path in _endpoints():
        if "multimodal-generation" in path:
            ref_sets = [refs, refs[:1]] if len(refs) > 1 else [refs]
            layouts = [{"messages": [{"role": "user", "content":
                        [{"image": u} for u in ref_set] + [{"text": prompt}]}]}
                       for ref_set in ref_sets]
        else:
            layouts = [{"prompt": prompt, "ref_image_url": refs[0]}]
        for input_obj in layouts:
            _require_time(deadline)
            params = {"size": size, "n": 1, "negative_prompt":
                      COMMON_NEGATIVE_PROMPT if negative_prompt is None else negative_prompt}
            try:
                output = task_client.generate(path, model, input_obj, params,
                                              deadline=deadline, label=f"img:{model}")
                _require_time(deadline)
                return output
            except ApiError as e:
                last_err = e
                if isinstance(e, TaskAcceptedError) or e.status not in (400, 404, 405, 422):
                    # A timeout/5xx after POST may already have created a paid task.
                    raise
                log.warning("image layout rejected: model=%s endpoint=%s", model, path)
    raise last_err or ApiError("all image layouts failed")


def generate_anchor(ctx, deadline):
    """Compatibility helper: lock the first original source, with no generation."""
    refs = _normalize_refs((ctx.get("product") or {}).get("images"))
    return (refs[0] if refs else None), None


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def _read_image_bytes(path):
    if os.path.getsize(path) > MAX_IMAGE_BYTES:
        raise ValueError("image exceeds byte limit")
    with open(path, "rb") as fh:
        data = fh.read(MAX_IMAGE_BYTES + 1)
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError("empty image or byte limit exceeded")
    return data


def _inspect_png(data, edge_frac=0.05, near=WHITE_BG_NEAR, max_samples=300000,
                 deadline=None):
    """Validate CRCs, chunk layout, bounded complete zlib stream and every row."""
    if not data.startswith(PNG_MAGIC):
        raise ValueError("not a PNG")
    pos = 8
    width = height = channels = color_type = None
    palette = trns = None
    parts = []
    seen = set()
    idat_ended = False
    ended = False
    while pos < len(data):
        _require_time(deadline)
        if pos + 12 > len(data):
            raise ValueError("truncated PNG chunk")
        length = struct.unpack_from(">I", data, pos)[0]
        tag = data[pos + 4:pos + 8]
        end = pos + 12 + length
        if (end > len(data) or tag[2] & 32
                or not all(65 <= c <= 90 or 97 <= c <= 122 for c in tag)):
            raise ValueError("invalid PNG chunk length/type")
        body = data[pos + 8:end - 4]
        crc = zlib.crc32(body, zlib.crc32(tag)) & 0xffffffff
        if crc != struct.unpack_from(">I", data, end - 4)[0]:
            raise ValueError("PNG CRC mismatch")
        if not seen and tag != b"IHDR":
            raise ValueError("IHDR must be first")
        if parts and tag != b"IDAT":
            idat_ended = True
        if tag == b"IHDR":
            if tag in seen or length != 13:
                raise ValueError("invalid IHDR")
            width, height, depth, color_type, comp, filt, interlace = struct.unpack(">IIBBBBB", body)
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
            if (not width or not height or width * height > MAX_IMAGE_PIXELS
                    or depth != 8 or channels is None or comp or filt or interlace):
                raise ValueError("unsupported PNG encoding or pixel limit exceeded")
            if height * (1 + width * channels) > MAX_PNG_DECOMPRESSED_BYTES:
                raise ValueError("PNG decompression limit exceeded")
        elif tag == b"PLTE":
            if tag in seen or parts or color_type in (0, 4) or not length or length % 3 or length > 768:
                raise ValueError("invalid PNG palette")
            palette = [tuple(body[i:i + 3]) for i in range(0, length, 3)]
        elif tag == b"tRNS":
            if tag in seen or parts:
                raise ValueError("invalid PNG transparency order")
            if not ((color_type == 0 and length == 2)
                    or (color_type == 2 and length == 6)
                    or (color_type == 3 and palette and 0 < length <= len(palette))):
                raise ValueError("invalid PNG transparency")
            trns = body
        elif tag == b"IDAT":
            if idat_ended or (color_type == 3 and not palette):
                raise ValueError("invalid PNG image data order")
            parts.append(body)
        elif tag == b"IEND":
            if length or not parts or end != len(data):
                raise ValueError("invalid PNG end")
            ended = True
            break
        elif not tag[0] & 32:
            raise ValueError("unsupported critical PNG chunk")
        seen.add(tag)
        pos = end
    if not ended:
        raise ValueError("missing PNG IEND")
    row_bytes = width * channels
    expected = height * (1 + row_bytes)
    decomp = zlib.decompressobj()
    # max_length is essential: no unbounded decompress() or flush().
    raw = decomp.decompress(b"".join(parts), expected + 1)
    if (len(raw) != expected or not decomp.eof
            or decomp.unconsumed_tail or decomp.unused_data):
        raise ValueError("invalid or oversized PNG decompressed stream")
    edge = max(1, int(min(width, height) * edge_frac))
    step = max(1, (2 * edge * (width + height) + max_samples - 1) // max_samples)
    previous = bytearray(row_bytes)
    sampled = white = 0
    for y in range(height):
        if y % 32 == 0:
            _require_time(deadline)
        offset = y * (row_bytes + 1)
        kind = raw[offset]
        if kind > 4:
            raise ValueError("invalid PNG row filter")
        row = bytearray(raw[offset + 1:offset + 1 + row_bytes])
        if kind:
            for i in range(row_bytes):
                left = row[i - channels] if i >= channels else 0
                up, upper_left = previous[i], previous[i - channels] if i >= channels else 0
                predictor = (left if kind == 1 else up if kind == 2 else
                             (left + up) // 2 if kind == 3 else _paeth(left, up, upper_left))
                row[i] = (row[i] + predictor) & 255
        if color_type == 3 and any(index >= len(palette) for index in row):
            raise ValueError("PNG palette index out of range")
        for x in range(0, width, step):
            if not (y < edge or y >= height - edge or x < edge or x >= width - edge):
                continue
            px = row[x * channels:(x + 1) * channels]
            alpha = 255
            if color_type == 3:
                alpha = trns[px[0]] if trns and px[0] < len(trns) else 255
                values = palette[px[0]]
            elif color_type in (4, 6):
                values, alpha = px[:-1], px[-1]
            else:
                values = px
                if trns and tuple(px) == struct.unpack(">" + "H" * channels, trns):
                    alpha = 0
            sampled += 1
            white += int(alpha >= near and all(value >= near for value in values))
        previous = row
    return white / sampled


def _validate_jpeg_structure(data):
    """Check markers, dimensions and scan termination, not JPEG entropy decoding."""
    pos = 2
    frame = scan = False
    while pos < len(data):
        if data[pos] != 255:
            raise ValueError("invalid JPEG marker")
        while pos < len(data) and data[pos] == 255:
            pos += 1
        if pos >= len(data):
            break
        marker = data[pos]
        pos += 1
        if marker == 0xd9:
            if frame and scan and pos == len(data):
                return
            raise ValueError("incomplete JPEG")
        if marker in (0, 0xd8) or 0xd0 <= marker <= 0xd7 or pos + 2 > len(data):
            raise ValueError("invalid JPEG segment")
        length = struct.unpack_from(">H", data, pos)[0]
        end = pos + length
        if length < 2 or end > len(data):
            raise ValueError("truncated JPEG segment")
        if marker in (0xc0, 0xc1, 0xc2):
            if length < 8:
                raise ValueError("invalid JPEG frame")
            height, width = struct.unpack_from(">HH", data, pos + 3)
            if not width or not height or width * height > MAX_IMAGE_PIXELS:
                raise ValueError("JPEG pixel limit exceeded")
            frame = True
        pos = end
        if marker == 0xda:
            if not frame or length < 6:
                raise ValueError("invalid JPEG scan")
            start = pos
            while pos < len(data):
                if data[pos] == 255:
                    if pos + 1 >= len(data):
                        break
                    if data[pos + 1] == 0 or 0xd0 <= data[pos + 1] <= 0xd7:
                        pos += 2
                        continue
                    break
                pos += 1
            if pos == start:
                raise ValueError("empty JPEG scan")
            scan = True
    raise ValueError("missing JPEG EOI")


def _inspect_image(path, deadline=None):
    _require_time(deadline)
    data = _read_image_bytes(path)
    if data.startswith(PNG_MAGIC):
        ratio = _inspect_png(data, deadline=deadline)
        return {"extension": "png", "status": "passed", "white_ratio": ratio}
    if data.startswith(b"\xff\xd8\xff"):
        _validate_jpeg_structure(data)
        # Without a JPEG decoder we cannot certify entropy integrity or white edges.
        return {"extension": "jpeg", "status": "unknown", "white_ratio": None}
    raise ValueError("unknown image magic; expected PNG or JPEG")


def _detect_ext_and_finalize(tmp_path, dest_base, inspection=None):
    inspection = inspection or _inspect_image(tmp_path)
    final = f"{dest_base}.{inspection['extension']}"
    os.replace(tmp_path, final)
    return final


def _png_near_white_edge_ratio(path, edge_frac=0.05, near=WHITE_BG_NEAR,
                               max_pixels=300000):
    """Compatibility sampler; malformed/unsupported PNGs return None safely."""
    try:
        return _inspect_png(_read_image_bytes(path), edge_frac, near, max(1, max_pixels))
    except (OSError, ValueError, zlib.error, struct.error):
        return None


def _make_critique(ctx, label, min_budget=20, reference_urls=None, deadline=None):
    chat, budget = ctx.get("chat"), ctx.get("budget")
    if chat is None:
        return None
    refs = (_normalize_refs((ctx.get("product") or {}).get("images"))
            if reference_urls is None else reference_urls)

    def critique(url):
        _require_time(deadline)
        if budget is not None and not budget.enough(min_budget):
            return None
        return score_image_url(chat, url, label=label, reference_urls=refs, deadline=deadline)

    return critique


def _make_compliance_hook(ctx, label, min_budget=20, deadline=None):
    chat, budget = ctx.get("chat"), ctx.get("budget")
    if chat is None:
        return None

    def compliance(url):
        _require_time(deadline)
        if budget is not None and not budget.enough(min_budget):
            return None
        return check_compliance(chat, url, label=label, deadline=deadline)

    return compliance


def _run_check(hook, url, deadline):
    _require_time(deadline)
    try:
        result = hook(url) if hook is not None else None
    except TimeoutError:
        raise
    except Exception:
        log.warning("image quality check unavailable", exc_info=True)
        result = None
    _require_time(deadline)
    return result


def _gen_one(task_client, ctx, slot_name, prompt, ref_url, size, model_chain,
             dest_base, deadline, critique=None, critique_retries=1, url_sink=None,
             white_bg=False, compliance=None, negative_prompt=None):
    """At most three attempts TOTAL, advancing models after any failed candidate.

    critique_retries remains accepted for caller compatibility but cannot enlarge
    the hard cap. Explicit ctx['allow_unreferenced_image_fallback'] is required to
    reserve the last attempt for OpenAI text-only generation; it ALWAYS needs review.
    Every transport uses the very same download/format/critic/compliance/white gate.
    """
    refs = _normalize_refs(ref_url)
    quality = {"status": "failed", "checks": {}, "reasons": [], "model": None,
               "path": None, "attempts": []}
    ctx.setdefault("image_quality", {})[slot_name] = quality
    if url_sink is not None:
        url_sink.pop(slot_name, None)
    if negative_prompt is None:
        negative_prompt = MAIN_NEGATIVE_PROMPT if white_bg else COMMON_NEGATIVE_PROMPT
    openai = ctx.get("openai_image")
    allow_unreferenced = ctx.get("allow_unreferenced_image_fallback") is True and openai is not None
    chain = list(model_chain or [])
    routes = []
    if refs and chain:
        count = MAX_CANDIDATES_PER_SLOT - int(allow_unreferenced)
        routes = [(chain[i % len(chain)], False) for i in range(count)]
    if allow_unreferenced:
        routes.append((MAIN_MODEL_PRIMARY, True))
    if not routes:
        quality.update(checks={"source_reference": "failed"},
                       reasons=["No source reference or reference-capable model available"])
        return None
    if critique is None:
        critique = _make_critique(ctx, slot_name, reference_urls=refs, deadline=deadline)
    if compliance is None:
        compliance = _make_compliance_hook(ctx, slot_name, deadline=deadline)
    notes = []
    tmp_path = dest_base + ".tmp"
    for model, unreferenced in routes:
        checks = {"source_reference": "unknown" if unreferenced else "passed",
                  "format": "not_run", "critic": "not_run", "compliance": "not_run",
                  "white_background": "not_run" if white_bg else "not_applicable"}
        reasons = ["Explicitly authorized text-only fallback lost source conditioning"] if unreferenced else []
        attempt = {"model": model, "status": "failed", "checks": checks, "reasons": reasons}
        try:
            _require_time(deadline)
            current_prompt = prompt + "".join(notes)
            if unreferenced:
                urls = openai.generate(model, current_prompt + " Avoid: " + negative_prompt, size=size)
            else:
                output = submit_image_task(task_client, model, current_prompt, refs, size,
                                           deadline, negative_prompt=negative_prompt)
                urls = extract_urls_from_output(output)
            _require_time(deadline)
            urls = _normalize_refs(urls, 1)
            if not urls:
                raise ApiError("image task returned no usable candidate URL")
            chosen = urls[0]  # n=1 requested; ignore unsolicited extras, never expand the budget.
            download_file(chosen, tmp_path, max_retries=0, label=f"dl:{slot_name}")
            _require_time(deadline)
            try:
                inspection = _inspect_image(tmp_path, deadline)
            except (ValueError, zlib.error, struct.error) as e:
                checks["format"] = "failed"
                reasons.append(str(e))
                attempt["status"] = "rejected"
                continue
            checks["format"] = inspection["status"]
            if inspection["status"] != "passed":
                reasons.append("JPEG decoding integrity cannot be verified with the stdlib")
            if white_bg:
                ratio = inspection["white_ratio"]
                checks["white_background"] = ("unknown" if ratio is None else
                                               "passed" if ratio >= WHITE_BG_MIN_RATIO else "failed")
                if checks["white_background"] == "failed":
                    reasons.append(f"White edge ratio {ratio:.3f} < {WHITE_BG_MIN_RATIO}")
                    notes.append(WHITE_BG_STRESS)
                elif ratio is None:
                    reasons.append("White background could not be verified")
            verdict = _run_check(critique, chosen, deadline)
            validated = validate_critique(verdict)
            if verdict is None:
                checks["critic"] = "unknown"
                reasons.append("Source fidelity/aesthetic check unavailable")
            elif validated is None:
                checks["critic"] = "failed"
                reasons.append("Malformed critic scores")
            else:
                checks["critic"] = {"accept": "passed", "retry": "failed", "unknown": "unknown"}[validated["verdict"]]
                if checks["critic"] != "passed":
                    reasons.append(validated["reason"] or "Critic did not accept the candidate")
                    if checks["critic"] == "failed":
                        notes.append(" Correct source fidelity and visual quality without inventing details.")
            result = _run_check(compliance, chosen, deadline)
            checks["compliance"] = "failed" if result is True else "passed" if result is False else "unknown"
            if result is True:
                reasons.append("Known compliance violation")
                notes.append(COMPLIANCE_STRESS)
            elif result is not False:
                reasons.append("Compliance check unavailable or ambiguous")
            if "failed" in checks.values():
                attempt["status"] = "rejected"
                continue
            status = "needs_review" if "unknown" in checks.values() else "accepted"
            _require_time(deadline)
            final = _detect_ext_and_finalize(tmp_path, dest_base if status == "accepted"
                                            else dest_base + ".needs_review", inspection)
            attempt["status"] = status
            quality["path"] = final
            if url_sink is not None:
                url_sink[slot_name] = chosen
            return final
        except Exception as e:
            reasons.append(str(e)[:200])
            log.warning("%s attempt failed via %s: %s", slot_name, model, str(e)[:150])
            if isinstance(e, TaskAcceptedError):
                quality['accepted_task_id'] = e.task_id
            if isinstance(e, (TimeoutError, TaskAcceptedError)) or (isinstance(e, ApiError) and
                    (e.status in (401, 403) or e.retryable)):
                break
        finally:
            quality["attempts"].append(attempt)
            quality.update(status=attempt["status"], checks=checks, reasons=list(reasons), model=model)
            for path in (tmp_path, tmp_path + ".part"):
                try:
                    os.remove(path)
                except FileNotFoundError:
                    pass
    return None


def generate_images(ctx):
    """Return {slot: retained_path}; review paths are explicitly noncanonical."""
    jobs = build_image_jobs(ctx)
    budget = ctx.get("budget")
    deadline = time.monotonic() + (min(max(0, budget.remaining()) * 0.55, 12 * 60)
                                   if budget is not None else 12 * 60)
    refs = _normalize_refs((ctx.get("product") or {}).get("images"))
    # Legacy video callers still use anchor_url: it now means the ORIGINAL source.
    ctx["anchor_url"] = refs[0] if refs else None
    ctx["main_image_url"] = None
    ctx["image_quality"] = {}
    url_sink, results = {}, {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {}
        for job in jobs:
            futures[pool.submit(
                _gen_one, ctx["task_client"], ctx, job["name"], job["prompt"], job["ref"],
                job["size"], job["chain"], job["dest"], deadline,
                url_sink=url_sink, white_bg=job["white_bg"],
                negative_prompt=job["negative_prompt"],
            )] = job["name"]
        for future, name in futures.items():
            try:
                path = future.result()
                if path:
                    results[name] = path
            except Exception as e:
                log.error("image job %s crashed: %s", name, e)
                ctx["image_quality"][name] = {
                    "status": "failed", "checks": {}, "reasons": [str(e)[:200]],
                    "model": None, "path": None,
                }
    # Review assets are retained for a human, not promoted into video input.
    if ctx["image_quality"].get("main_image", {}).get("status") == "accepted":
        ctx["main_image_url"] = url_sink.get("main_image")
    log.info("image generation finished: %d retained / 6 planned", len(results))
    return results
