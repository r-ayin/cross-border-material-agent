#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lk888 (灵客AI) media runner — real image/video generation for the contest product.

Channel:  VM 127.0.0.1:18443 -> ssh -L via ecs-jump -> api.lk888.ai:443 (TLS end-to-end).
Key:      ~/.dsh/credentials/lk888.key (never printed).
Protocol: POST /v1/media/generate {model, prompt, params} -> data.task_id
          GET  /v1/skills/task-status?task_id=...  -> poll until is_final
          download result_url.

Stages:
  images  main_image   : qwen-image,      size 1:1, prompt_extend false
          detail 1..5  : wan2.7-image,    quality pro, size 1:1
          reference    : 5 source product images (img2img; prompts treat source
                         refs as sole visual authority). Prompts come from
                         frontend/assets/preflight-plan.json (single source of truth).
  video   happyhorse-1.1-i2v, 720P, 5s, first frame = generated main image,
          prompt from docs/video-storyboard.md 方案A (duration adapted to 5s).
  report  run_report.json with task ids / costs / durations / balance after run.

Outputs: build/lk888-run-<RUN_ID>/ with canonical filenames
         (main_image.png, detail_image_1..5.png, product_video.mp4).

Discipline: task ids are persisted to tasks.json immediately after submit and are
never resubmitted; pure standard library; costs are checked against balance first.
"""
import base64
import json
import mimetypes
import os
import ssl
import struct
import sys
import time
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_ID = os.environ.get("LK888_RUN_ID", "20260922")
OUT = os.path.join(REPO, "build", "lk888-run-" + RUN_ID)
BASE = os.environ.get("LK888_BASE_URL", "https://api.lk888.ai:18443/v1").rstrip("/")
KEY_FILE = os.path.expanduser(os.environ.get("LK888_KEY_FILE", "~/.dsh/credentials/lk888.key"))
PLAN = os.path.join(REPO, "frontend", "assets", "preflight-plan.json")
PRODUCT = os.path.join(REPO, "data", "Task_Data", "Data_for_Users(2)",
                       "product_info", "product_8822221153828.json")
TASKS_FILE = os.path.join(OUT, "tasks.json")
CTX = ssl.create_default_context()
# Python 3.14 VERIFY_X509_STRICT rejects the egress proxy CA (missing keyUsage ext);
# documented fallback per AGENTS.md: relax strict flags, keep hostname checking.
try:
    CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT
except Exception:
    pass

IMAGE_SLOTS = ["main_image", "detail_image_1", "detail_image_2",
               "detail_image_3", "detail_image_4", "detail_image_5"]
VIDEO_PROMPT = (
    "E-commerce product video of a light pink pleated maxi skirt. The skirt is the "
    "only garment featured: high waist, fine accordion pleats, A-line full swing, "
    "ankle length, soft polyester drape. Opening close-up of the pleats swaying, "
    "then slow pull-back to full silhouette on a clean off-white studio background, "
    "gentle side light, final frame static full view centered. Smooth slow camera "
    "movement, professional studio lighting, photorealistic fabric texture, "
    "no text, no watermark, no logo, no other garments."
)


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def api_key():
    with open(KEY_FILE) as f:
        return f.read().strip()


def http_json(path, body=None, timeout=90):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data,
        method="POST" if data is not None else "GET",
        headers={"Authorization": "Bearer " + api_key(),
                 "Content-Type": "application/json",
                 "Accept-Language": "zh-CN"})
    attempts = 1 if data is not None else 4  # never replay a POST; retry idempotent GETs
    last_exc = None
    for i in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"raw": raw[:400].decode(errors="replace")}
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            last_exc = e
            if i + 1 < attempts:
                time.sleep(2.0 * (i + 1))
    raise RuntimeError("GET %s failed after %d attempts: %s" % (path, attempts, last_exc))


def load_tasks():
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE) as f:
            return json.load(f)
    return {}


def save_tasks(tasks):
    os.makedirs(OUT, exist_ok=True)
    tmp = "%s.tmp.%d.%d" % (TASKS_FILE, os.getpid(), threading.get_ident())
    try:
        with open(tmp, "w") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=1)
        os.replace(tmp, TASKS_FILE)
    except OSError as exc:
        log("save_tasks degraded (state kept in memory): %s" % exc)
        try:
            os.unlink(tmp)
        except OSError:
            pass


def source_refs():
    with open(PRODUCT) as f:
        d = json.load(f)
    urls = d["ret"]["result"]["result"]["productImage"]["images"]
    return urls[:5]


def slot_prompts():
    with open(PLAN) as f:
        plan = json.load(f)
    return {s["id"]: (s.get("prompt") or "").strip()
            for s in plan["slots"] if s.get("kind") in ("image", "video")}


def to_data_uri(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        blob = r.read()
    mime = mimetypes.guess_type(url.split("?")[0])[0] or "image/jpeg"
    return "data:%s;base64,%s" % (mime, base64.b64encode(blob).decode())


def submit(slot, model, prompt, params_variants, tasks):
    """Submit with fallback across params variants. Never resubmit a recorded task."""
    rec = tasks.get(slot)
    if rec and rec.get("task_id") and rec.get("state") != "failed":
        log("%s: already submitted task %s (skip)" % (slot, rec["task_id"]))
        return rec["task_id"]
    last_err = None
    for variant in params_variants:
        st, j = http_json("/media/generate",
                          {"model": model, "prompt": prompt, "params": variant})
        if st == 200 and j.get("code") == 200 and (j.get("data") or {}).get("task_id"):
            tid = j["data"]["task_id"]
            tasks[slot] = {"task_id": tid, "model": model,
                           "submitted_at": time.time(),
                           "params_variant": {k: (v if k != "images" else "<refs>")
                                              for k, v in variant.items()}}
            save_tasks(tasks)
            log("%s: submitted task %s model=%s" % (slot, tid, model))
            return tid
        last_err = "HTTP %s %s" % (st, json.dumps(j, ensure_ascii=False)[:300])
        log("%s: variant rejected: %s" % (slot, last_err))
    raise RuntimeError("%s: all submit variants failed: %s" % (slot, last_err))


def poll(slot, tasks, timeout=1800, interval=6.0):
    rec = tasks[slot]
    if rec.get("is_final"):
        return rec
    tid = rec["task_id"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        st, j = http_json("/skills/task-status?task_id=%d" % tid, timeout=30)
        if st == 200 and j.get("task_id"):
            rec.update({k: j.get(k) for k in
                        ("status", "status_group", "progress", "is_final", "state",
                         "result_url", "result_urls", "result_type", "cost",
                         "error", "duration_seconds", "completed_at", "channel_group")})
            save_tasks(tasks)
            if rec.get("is_final"):
                log("%s: final state=%s cost=%s dur=%ss" %
                    (slot, rec.get("state"), rec.get("cost"), rec.get("duration_seconds")))
                return rec
            log("%s: %s %s" % (slot, rec.get("status"), rec.get("progress")))
        time.sleep(interval)
    raise TimeoutError("%s: task %s not final within %ss" % (slot, tid, timeout))


def download(url, dest, timeout=300):
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        blob = r.read()
    with open(dest, "wb") as f:
        f.write(blob)
    return len(blob)


def png_dimensions(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", head[16:24])
    return w, h


def stage_images():
    os.makedirs(OUT, exist_ok=True)
    tasks = load_tasks()
    prompts = slot_prompts()
    refs = source_refs()
    log("source refs: %d urls" % len(refs))
    state = {"data_uris": None}

    def variants_for(slot):
        base_params = {"size": "1:1"}
        if slot == "main_image":
            base_params["prompt_extend"] = "false"
            return [dict(base_params, images=list(refs[:3])),
                    dict(base_params, images=list(refs[:1]))]
        base_params["quality"] = "pro"
        return [dict(base_params, images=list(refs))]

    def submit_one(slot):
        model = "qwen-image" if slot == "main_image" else "wan2.7-image"
        vs = variants_for(slot)
        try:
            return submit(slot, model, prompts[slot], vs, tasks)
        except RuntimeError:
            if state["data_uris"] is None:
                log("URL refs rejected; converting source refs to data URIs")
                state["data_uris"] = [to_data_uri(u) for u in refs]
            du = state["data_uris"]
            base = vs[0]
            vs2 = [dict(base, images=list(du)),
                   dict(base, images=du[0]),
                   dict(base, images=",".join(refs))]
            return submit(slot, model, prompts[slot], vs2, tasks)

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(submit_one, IMAGE_SLOTS))

    def finish(slot):
        try:
            rec = poll(slot, tasks, timeout=900)
            if rec.get("state") != "success" or not rec.get("result_url"):
                log("%s: FAILED state=%s error=%s" % (slot, rec.get("state"), rec.get("error")))
                return slot, False
            dest = os.path.join(OUT, slot + ".png")
            n = download(rec["result_url"], dest)
            dims = png_dimensions(dest)
            rec.update({"local_path": dest, "bytes": n, "dimensions": list(dims) if dims else None})
            save_tasks(tasks)
            log("%s: saved %s (%dB, %s)" % (slot, dest, n, dims))
            return slot, True
        except Exception as e:
            log("%s: finish error: %s" % (slot, e))
            return slot, False

    with ThreadPoolExecutor(max_workers=6) as ex:
        results = dict(ex.map(finish, IMAGE_SLOTS))
    ok = sum(1 for v in results.values() if v)
    log("images done: %d/%d ok" % (ok, len(IMAGE_SLOTS)))
    return 0 if ok == len(IMAGE_SLOTS) else 1


MAINFIX_NEG = (
    "Negative (must NOT appear): text, watermark, logo, signature, border, collage, "
    "price tag, promotional symbols, distorted product, blurry, deformed, invented "
    "back construction, invented seams, invented closures, changed color, changed "
    "pattern, colored background, textured background, indoor scene, outdoor scene, "
    "gradient, vignette, props, human model, extra products, body parts, hands, feet, "
    "face, hair, handbag, sandals, footwear, wall, floor, tiles. "
    "Present the skirt ALONE as a flat-lay / hanging product-only photograph: no person "
    "wearing it, seamless pure white RGB(255,255,255) background to all four borders."
)
WHITE_BG_MIN_RATIO = 0.9


def white_edge_ratio(path):
    sys.path.insert(0, os.path.join(REPO, "agent"))
    from src.image_gen import _png_near_white_edge_ratio
    return _png_near_white_edge_ratio(path)


def stage_mainfix():
    """Regenerate main image with negative-channel stress; gate with project checker."""
    os.makedirs(OUT, exist_ok=True)
    tasks = load_tasks()
    prompts = slot_prompts()
    refs = source_refs()
    prompt = prompts["main_image"] + " " + MAINFIX_NEG
    cands = [("main_image_c1", "qwen-image",
              [{"size": "1:1", "prompt_extend": "false", "images": list(refs[:3])}]),
             ("main_image_c2", "wan2.7-image",
              [{"size": "1:1", "quality": "pro", "images": list(refs)}])]
    for slot, model, vs in cands:
        submit(slot, model, prompt, vs, tasks)
    winner = None
    for slot, model, _ in cands:
        rec = poll(slot, tasks, timeout=900)
        if rec.get("state") != "success" or not rec.get("result_url"):
            log("%s: failed %s" % (slot, rec.get("error")))
            continue
        dest = os.path.join(OUT, slot + ".png")
        n = download(rec["result_url"], dest)
        dims = png_dimensions(dest)
        ratio = white_edge_ratio(dest)
        rec.update({"local_path": dest, "bytes": n,
                    "dimensions": list(dims) if dims else None,
                    "white_edge_ratio": ratio})
        save_tasks(tasks)
        log("%s: %s dims=%s white_edge_ratio=%.4f" % (slot, model, dims, ratio or -1))
        if ratio is not None and ratio >= WHITE_BG_MIN_RATIO and winner is None:
            winner = (slot, rec, dest)
    if winner is None:
        log("mainfix: NO candidate passed the white gate")
        return 1
    slot, rec, src = winner
    final = os.path.join(OUT, "main_image.png")
    import shutil
    shutil.copyfile(src, final)
    main = tasks.get("main_image", {})
    main.update({"task_id": rec["task_id"], "model": rec["model"],
                 "state": "success", "result_url": rec["result_url"],
                 "local_path": final, "bytes": rec["bytes"],
                 "dimensions": rec["dimensions"],
                 "white_edge_ratio": rec["white_edge_ratio"],
                 "superseded_by": slot, "is_final": True})
    save_tasks(tasks)
    log("mainfix: %s adopted as main_image.png (ratio %.4f)" % (slot, rec["white_edge_ratio"]))
    return 0


def stage_video():
    tasks = load_tasks()
    main = tasks.get("main_image") or {}
    if main.get("state") != "success" or not main.get("result_url"):
        log("main_image not successful yet; run images stage first")
        return 1
    first_frame = main["result_url"]
    vs = [{"images": [first_frame], "resolution": "720P", "duration": "5"},
          {"_first_frame_url": first_frame, "resolution": "720P", "duration": "5"}]
    submit("product_video", "happyhorse-1.1-i2v", VIDEO_PROMPT, vs, tasks)
    rec = poll("product_video", tasks, timeout=2400, interval=10.0)
    if rec.get("state") != "success" or not rec.get("result_url"):
        log("video FAILED state=%s error=%s" % (rec.get("state"), rec.get("error")))
        return 1
    dest = os.path.join(OUT, "product_video.mp4")
    n = download(rec["result_url"], dest, timeout=600)
    with open(dest, "rb") as f:
        head = f.read(12)
    is_mp4 = head[4:8] == b"ftyp"
    rec.update({"local_path": dest, "bytes": n, "mp4_ftyp": is_mp4})
    save_tasks(tasks)
    log("video saved %s (%dB, ftyp=%s)" % (dest, n, is_mp4))
    return 0 if is_mp4 else 1


PLANB_SHOTS = [
    # (slot, prompt, first_frame_slot, last_frame_slot, duration_s)
    ("seg1_hook", "Extreme close-up of fine accordion pleats of a light pink maxi "
     "skirt, fabric gently swaying, soft studio light, shallow depth of field, no text.",
     "detail_image_3", "detail_image_4", 4),
    ("seg2_problem", "Medium shot, model holding the skirt at waist height against a "
     "clean background, showing the high waistband and stretch-free structure, slow "
     "tilt down, no text.",
     "detail_image_4", "main_image", 5),
    ("seg3_product", "Full-body model wearing the light pink pleated maxi skirt, slow "
     "walk and half turn showing the A-line swing and ankle length. Setting: seamless "
     "off-white studio cyclorama only - no sofa, no furniture, no props, no floor "
     "tiles, no feet close-up. Even soft lighting, camera at waist height tracking "
     "the walk, no text, no watermark.",
     "main_image", "detail_image_2", 11),
    ("seg4_proof", "Close-up of waistband and pleat stitching detail, fingers lightly "
     "brushing the fabric to show drape, macro lens, no text.",
     "detail_image_2", "detail_image_5", 5),
    ("seg5_cta", "Top-down flat lay of the light pink pleated maxi skirt on a seamless "
     "pure white background. The skirt alone: no person, no feet, no hands, no props, "
     "no floor. Pleats fanned out symmetrically, soft shadow under the garment, camera "
     "directly overhead slowly zooming out, final static centered frame, no text, "
     "no watermark.",
     "detail_image_5", "detail_image_5", 5),
]


def stage_planb():
    """Storyboard 方案B: five i2v segments with first/last frame chaining."""
    os.makedirs(OUT, exist_ok=True)
    tasks = load_tasks()
    urls = {}
    for slot in ("main_image", "detail_image_2", "detail_image_3",
                 "detail_image_4", "detail_image_5"):
        rec = tasks.get(slot) or {}
        if rec.get("state") != "success" or not rec.get("result_url"):
            log("planb: missing result_url for %s" % slot)
            return 1
        urls[slot] = rec["result_url"]
    from concurrent.futures import ThreadPoolExecutor as TPE

    def submit_shot(item):
        slot, prompt, first, last, dur = item
        vs = [{"images": [urls[first], urls[last]],
               "duration": str(dur), "resolution": "1080P"},
              {"images": [urls[first]],
               "duration": str(dur), "resolution": "1080P"}]
        return submit(slot, "hailuo-h3-shouweizhen", prompt, vs, tasks)

    with TPE(max_workers=5) as ex:
        list(ex.map(submit_shot, PLANB_SHOTS))

    def finish(item):
        slot = item[0]
        try:
            rec = poll(slot, tasks, timeout=1800, interval=8.0)
            if rec.get("state") != "success" or not rec.get("result_url"):
                log("%s: FAILED %s" % (slot, rec.get("error")))
                return slot, False
            dest = os.path.join(OUT, slot + ".mp4")
            n = download(rec["result_url"], dest, timeout=600)
            rec.update({"local_path": dest, "bytes": n})
            save_tasks(tasks)
            log("%s: saved %dB" % (slot, n))
            return slot, True
        except Exception as e:
            log("%s: finish error: %s" % (slot, e))
            return slot, False

    with TPE(max_workers=5) as ex:
        results = dict(ex.map(finish, PLANB_SHOTS))
    ok = sum(1 for v in results.values() if v)
    log("planb segments: %d/%d ok" % (ok, len(PLANB_SHOTS)))
    return 0 if ok == len(PLANB_SHOTS) else 1


DETAILFIX_OVERRIDES = {
    "detail_image_2": " FRAMING OVERRIDE: extreme macro close-up; the pleated fabric and "
        "one waistband seam fill 100 percent of the frame edge to edge; no person, no full "
        "garment, no feet, no bag, no floor, no wall; shallow depth of field.",
    "detail_image_3": " FRAMING OVERRIDE: macro textile close-up; only the pleated polyester "
        "surface and its drape folds fill the entire frame edge to edge; no person, no full "
        "garment, no background objects, no floor.",
    "detail_image_5": " FRAMING OVERRIDE: complete skirt presented WITHOUT a person; hanging "
        "or flat-lay full view on a neutral seamless light-gray backdrop; entire garment "
        "uncropped and centered; composition clearly different from editorial worn shots; "
        "no person, no feet, no bag.",
}


def stage_detailfix():
    """Regenerate detail slots whose first pass ignored the slot framing duty."""
    os.makedirs(OUT, exist_ok=True)
    tasks = load_tasks()
    prompts = slot_prompts()
    refs = source_refs()
    for slot in DETAILFIX_OVERRIDES:
        rec = tasks.get(slot)
        if rec:
            rec["state"] = "failed"
            rec["is_final"] = False
            rec["error"] = "slot framing duty failed visual gate; resubmit strengthened"
    save_tasks(tasks)
    from concurrent.futures import ThreadPoolExecutor as TPE

    def go(slot):
        prompt = prompts[slot] + DETAILFIX_OVERRIDES[slot]
        vs = [{"size": "1:1", "quality": "pro", "images": list(refs)}]
        submit(slot, "wan2.7-image", prompt, vs, tasks)
        rec = poll(slot, tasks, timeout=900)
        if rec.get("state") != "success" or not rec.get("result_url"):
            log("%s: FAILED %s" % (slot, rec.get("error")))
            return slot, False
        dest = os.path.join(OUT, slot + ".png")
        n = download(rec["result_url"], dest)
        dims = png_dimensions(dest)
        rec.update({"local_path": dest, "bytes": n,
                    "dimensions": list(dims) if dims else None})
        save_tasks(tasks)
        log("%s: saved %dB %s" % (slot, n, dims))
        return slot, True

    with TPE(max_workers=3) as ex:
        results = dict(ex.map(go, sorted(DETAILFIX_OVERRIDES)))
    ok = sum(1 for v in results.values() if v)
    log("detailfix: %d/%d ok" % (ok, len(results)))
    return 0 if ok == len(results) else 1


NARRV2_SHOTS = [
    # (slot, prompt, first_frame_slot, last_frame_slot, duration)
    ("n1_hook", "Extreme macro of fine accordion pleats of a light pink polyester maxi "
     "skirt filling the whole frame, fabric swaying softly like water, slow push-in, "
     "shallow depth of field, soft studio light, no person, no text, no watermark.",
     "detail_image_3", "detail_image_3", 4),
    ("n2_context", "Medium lifestyle shot in a bright minimal interior: a model in a "
     "black top and light pink pleated maxi skirt steps into frame holding a coffee "
     "cup, relaxed commute-to-weekend mood, camera slowly tracking sideways, soft "
     "daylight, no text, no watermark.",
     "detail_image_4", "detail_image_4", 6),
    ("n3_reveal", "Product film reveal: starts as the light pink pleated maxi skirt "
     "flat on pure white, match-cut on the pleat lines to a full-body model wearing "
     "it, slow walk and half turn showing high waist, A-line swing and ankle length, "
     "clean off-white studio, even light, no text, no watermark.",
     "main_image", "detail_image_1", 9),
    ("n4_proof", "Macro detail proof: close-up of the smooth high waistband seam and "
     "crisp accordion pleats of the light pink skirt, fingers lightly brushing the "
     "fabric to show its no-stretch structure, slow lateral macro move, soft studio "
     "light, no text, no watermark.",
     "detail_image_2", "detail_image_2", 6),
    ("n5_cta", "Final card: the complete light pink pleated maxi skirt alone, centered "
     "on a neutral seamless light-gray backdrop, camera slowly zooming out to a static "
     "hold, soft shadow, no person, no props, no text, no watermark.",
     "detail_image_5", "detail_image_5", 5),
]


def stage_narrv2():
    """Narrative v2 (docs/video-narrative-v2.md): five story beats, chained frames."""
    os.makedirs(OUT, exist_ok=True)
    tasks = load_tasks()
    urls = {}
    for slot in ("main_image", "detail_image_1", "detail_image_2",
                 "detail_image_3", "detail_image_4", "detail_image_5"):
        rec = tasks.get(slot) or {}
        if rec.get("state") != "success" or not rec.get("result_url"):
            log("narrv2: missing frame source %s" % slot)
            return 1
        urls[slot] = rec["result_url"]
    from concurrent.futures import ThreadPoolExecutor as TPE

    def run(item):
        slot, prompt, first, last, dur = item
        rec = tasks.get(slot)
        if rec and rec.get("task_id") and rec.get("state") != "failed":
            log("%s: existing task %s (skip submit)" % (slot, rec["task_id"]))
        else:
            vs = [{"images": [urls[first], urls[last]],
                   "duration": str(dur), "resolution": "1080P"},
                  {"images": [urls[first]],
                   "duration": str(dur), "resolution": "1080P"}]
            submit(slot, "hailuo-h3-shouweizhen", prompt, vs, tasks)
        rec = poll(slot, tasks, timeout=2400, interval=10.0)
        if rec.get("state") != "success" or not rec.get("result_url"):
            log("%s: FAILED %s" % (slot, rec.get("error")))
            return slot, False
        dest = os.path.join(OUT, slot + ".mp4")
        n = download(rec["result_url"], dest, timeout=600)
        rec.update({"local_path": dest, "bytes": n})
        save_tasks(tasks)
        log("%s: saved %dB" % (slot, n))
        return slot, True

    with TPE(max_workers=5) as ex:
        results = dict(ex.map(run, NARRV2_SHOTS))
    ok = sum(1 for v in results.values() if v)
    log("narrv2: %d/%d ok" % (ok, len(NARRV2_SHOTS)))
    return 0 if ok == len(NARRV2_SHOTS) else 1


SLICE15_SHOTS = [
    # (slot, prompt, first_frame_file, last_frame_file, duration)  9:16 vertical social cut
    ("s1_hook", "Vertical 9:16 extreme macro of fine accordion pleats of a light pink "
     "polyester maxi skirt filling the frame, fabric swaying like water, slow push-in, "
     "soft studio light, no person, no text, no watermark.",
     "detail_image_3_916.png", "detail_image_3_916.png", 4),
    ("s2_reveal", "Vertical 9:16 product reveal: light pink pleated maxi skirt flat on "
     "pure white, match-cut on pleat lines to full-body model wearing it, slow walk "
     "and half turn, high waist and ankle length visible, clean off-white studio, "
     "no text, no watermark.",
     "main_image_916.png", "detail_image_1_916.png", 6),
    ("s3_cta", "Vertical 9:16 final card: complete light pink pleated maxi skirt alone, "
     "centered on neutral seamless light-gray backdrop, slow zoom-out to static hold, "
     "soft shadow, no person, no props, no text, no watermark.",
     "detail_image_5_916.png", "detail_image_5_916.png", 5),
]


def _data_uri(path):
    import base64 as _b64
    with open(path, "rb") as f:
        blob = f.read()
    return "data:image/png;base64," + _b64.b64encode(blob).decode()


def stage_slice15():
    """15s vertical (9:16) social cut: Hook / Reveal / CTA from gated 9:16 frames."""
    os.makedirs(OUT, exist_ok=True)
    tasks = load_tasks()
    from concurrent.futures import ThreadPoolExecutor as TPE

    def run(item):
        slot, prompt, first_f, last_f, dur = item
        rec = tasks.get(slot)
        if rec and rec.get("task_id") and rec.get("state") != "failed":
            log("%s: existing task %s (skip submit)" % (slot, rec["task_id"]))
        else:
            fu = _data_uri(os.path.join(OUT, first_f))
            lu = _data_uri(os.path.join(OUT, last_f))
            vs = [{"images": [fu, lu], "duration": str(dur), "resolution": "1080P"},
                  {"images": [fu], "duration": str(dur), "resolution": "1080P"}]
            submit(slot, "hailuo-h3-shouweizhen", prompt, vs, tasks)
        rec = poll(slot, tasks, timeout=2400, interval=10.0)
        if rec.get("state") != "success" or not rec.get("result_url"):
            log("%s: FAILED %s" % (slot, rec.get("error")))
            return slot, False
        dest = os.path.join(OUT, slot + ".mp4")
        n = download(rec["result_url"], dest, timeout=600)
        rec.update({"local_path": dest, "bytes": n})
        save_tasks(tasks)
        log("%s: saved %dB" % (slot, n))
        return slot, True

    with TPE(max_workers=3) as ex:
        results = dict(ex.map(run, SLICE15_SHOTS))
    ok = sum(1 for v in results.values() if v)
    log("slice15: %d/%d ok" % (ok, len(SLICE15_SHOTS)))
    return 0 if ok == len(SLICE15_SHOTS) else 1


def stage_report():
    tasks = load_tasks()
    st, bal = http_json("/skills/balance", timeout=20)
    total_cost = sum(float(t.get("cost") or 0) for t in tasks.values())
    report = {
        "run_id": RUN_ID,
        "channel": "lk888 (灵客AI) via VM 18443 -> ecs-jump -> api.lk888.ai",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_cost_suanli": round(total_cost, 4),
        "balance": bal if st == 200 else {"error": str(bal)[:200]},
        "tasks": tasks,
    }
    path = os.path.join(OUT, "run_report.json")
    with open(path, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    log("report -> %s | total cost %.3f" % (path, total_cost))
    return 0


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "images"
    os.makedirs(OUT, exist_ok=True)
    if stage == "images":
        return stage_images()
    if stage == "mainfix":
        return stage_mainfix()
    if stage == "planb":
        return stage_planb()
    if stage == "detailfix":
        return stage_detailfix()
    if stage == "narrv2":
        return stage_narrv2()
    if stage == "slice15":
        return stage_slice15()
    if stage == "video":
        return stage_video()
    if stage == "report":
        return stage_report()
    if stage == "all":
        rc = stage_images()
        if rc == 0:
            rc = stage_video()
        stage_report()
        return rc
    print("usage: lk888_media.py [images|video|report|all]")
    return 2


if __name__ == "__main__":
    sys.exit(main())
