# -*- coding: utf-8 -*-
"""Reference-first, single-submission product clips and offline editorial plans.

A storyboard is a plan, not evidence of delivered shots. Only structurally
inspected candidates become product_video.mp4. No concatenation, decoding,
subtitle burn-in or music synthesis is performed here. Runtime dependencies are
standard-library only; video_plan_only=True performs no network/model calls.
"""
import json
import logging
import math
import os
import re
import tempfile
import textwrap
import time
import unicodedata
import urllib.parse

from . import dsapi
from .dsapi import ApiError, extract_urls_from_output
from .media_probe import MAX_VIDEO_BYTES, inspect_video

log = logging.getLogger("agent")

# Select before submission using local capabilities; NEVER retry down the chain
# after a failed/ambiguous billable request. These are existing observed APIs.
VIDEO_CHAIN = [
    ("wan2.7-i2v-2026-04-25", "i2v"),
    ("happyhorse-1.1-r2v", "r2v"),
    ("happyhorse-1.1-t2v", "t2v"),
]
VIDEO_ENDPOINTS = [
    "/services/aigc/video-generation/video-synthesis",
    "/services/aigc/image2video/video-synthesis",
]
I2V_MODEL = VIDEO_CHAIN[0][0]
T2V_MODEL = VIDEO_CHAIN[-1][0]
VIDEO_SIZE = "1280*720"
SEGMENT_COST_SECONDS = 90  # conservative minimum budget for ONE clip
DEFAULT_CLIP_SECONDS = 5  # previously used i2v duration, not a claimed result
SRT_MAX_CUES = 10
BGM_MODEL = "fun-music-v1"
BGM_MAX_VOLUME_PERCENT = 30


def _text(value):
    return " ".join(str(value or "").split())


def _source_facts(product):
    facts = []
    for attribute in product.get("attributes") or []:
        if not isinstance(attribute, dict):
            continue
        name = _text(attribute.get("attributeNameTrans") or attribute.get("attributeName"))
        value = _text(attribute.get("valueTrans") or attribute.get("value"))
        if value:
            fact = f"{name}: {value}" if name else value
            if fact not in facts:
                facts.append(fact)
    return facts


def extract_visual_constraints(product, vision_brief=""):
    """Source facts only. A model's vision brief is not verified source evidence."""
    return "; ".join(_source_facts(product)[:12])


def _shot_prompt(pid, name, start, end, frame, body, visual):
    facts = f" Source facts (not extra performance claims): {visual}." if visual else ""
    return (
        f"{body}{facts} The supplied original reference image is authoritative; "
        "preserve its visible product identity, geometry, color and markings. "
        "Descriptions must not override the image. Do not invent hidden sides, "
        "materials, accessories, people, use cases or performance claims. "
        "Use only gentle camera movement within the visible view, stable lighting "
        "and background; no added text, logos, watermarks or price graphics."
    )


def _build_shots(product, vision_brief, boundaries):
    subject = _text(product.get("subject")) or "the source product"
    visual = extract_visual_constraints(product, vision_brief)
    bodies = [
        ("hook", "Hook", "main", f"Open on a recognizable view of {subject}; gently approach a visible feature."),
        ("problem", "Problem", "main", f"Help the viewer inspect {subject}'s visible form; reframe slightly, without inventing a problem or comparison."),
        ("product", "Product", "main", f"Hold a clear, centered view of {subject}; retain all visible product boundaries."),
        ("proof", "Proof", "detail", f"Move gently toward an already visible detail of {subject}; visual inspection only, not a test or claim of effectiveness."),
        ("cta", "CTA", "main", f"Return to a balanced view of {subject} and settle; a visual invitation to inspect, without promotional claims."),
    ]
    shots = []
    for i, (sid, name, frame, body) in enumerate(bodies):
        start, end = boundaries[i:i + 2]
        shots.append({"id": sid, "name": name, "start": start, "end": end,
                      "seconds": end - start, "frame": frame,
                      "prompt": _shot_prompt(sid, name, start, end, frame, body, visual)})
    return shots


def build_shot_prompts(product, vision_brief=None):
    """Pure 30-second, five-beat editorial plan, applicable across categories."""
    return _build_shots(product, vision_brief, (0, 3, 8, 20, 25, 30))


def build_compressed_shot_prompts(product, vision_brief=None):
    """Pure 15-second plan retaining Hook / Problem / Product / Proof / CTA."""
    return _build_shots(product, vision_brief, (0, 2, 4, 10, 13, 15))


def build_combined_t2v_prompt(shots, product, vision_brief=None):
    """Explicitly unreferenced draft: sequential cuts, not a contradictory take.

    Kept for offline planning. Runtime submits a simpler single-clip script.
    Text constraints cannot establish or restore reference-image fidelity.
    """
    subject = _text(product.get("subject")) or "the source product"
    sequence = " ".join(f"{s['start']}-{s['end']}s {s['name']}: {s['prompt']}" for s in shots)
    total = shots[-1]["end"] if shots else 0
    return (f"Unreferenced concept draft for {subject}. Editorial target: {total}s, "
            f"with sequential cuts between the planned beats. {sequence} "
            "No reference image is supplied for this draft; image-dependent instructions "
            "cannot be verified. Product fidelity is unknown and requires human review.")


def _clip_prompt(product, duration, referenced):
    subject = _text(product.get("subject")) or "the source product"
    body = (f"One self-contained product showcase clip of {subject}, target {duration:g} seconds "
            "(actual duration must be inspected). A single continuous view, not a multi-scene "
            "montage: begin with the whole visible product, make a subtle slow push-in, "
            "then settle on a stable final frame. Do not rotate to unseen surfaces.")
    if referenced:
        return _shot_prompt("clip", "Clip", 0, duration, "main", body,
                            extract_visual_constraints(product))
    return (body + " Source facts: " + (extract_visual_constraints(product) or "none supplied")
            + ". No reference image is available. This is an unverified concept draft; "
            "do not invent features, demonstrations or claims. No added text or watermarks. "
            "Product fidelity is unknown and needs human review.")


def extract_key_features(en_copy_path):
    """Read existing copy bullets; callers must separately establish grounding."""
    if not en_copy_path:
        return []
    try:
        with open(en_copy_path, "r", encoding="utf-8") as stream:
            text = stream.read()
    except (OSError, UnicodeError):
        return []
    match = re.search(r"^##\s*Key Features\s*$", text, re.M)
    section = text[match.end():].split("\n##", 1)[0] if match else text
    return [line[2:].strip() for line in section.splitlines()
            if line.startswith("- ") and line[2:].strip()]


def _verified_subtitle_features(ctx):
    """Caller attests English and grounding; source/copy text is only a draft.

    Script checks reject obvious non-English text, not certify English semantics.
    No translation or language/model call is made here.
    """
    values = ctx.get("verified_subtitle_features")
    if not isinstance(values, (list, tuple)):
        return []
    result = []
    for value in values:
        if not isinstance(value, str):
            continue
        text = _text(value)
        letters = [char for char in text if char.isalpha()]
        if letters and all("LATIN" in unicodedata.name(char, "") for char in letters):
            result.append(text)
    return result


def build_srt_entries(features, subject, fallback_sources, total_seconds):
    """Fit factual, word-wrapped cues to a *measured* timeline, without padding.

    Features must be caller-verified English facts. Legacy source arguments are
    retained for compatibility but never used as a subtitle fallback. Whole
    sentences/words are retained; unreadable text is omitted, not truncated.
    """
    try:
        duration = float(total_seconds)
    except (TypeError, ValueError):
        return []
    if not math.isfinite(duration) or duration <= 0:
        return []
    duration = math.floor(duration * 1000) / 1000
    texts = _verified_subtitle_features({"verified_subtitle_features": features})
    accepted, seen = [], set()
    used = 0.0
    for value in texts:
        for sentence in re.split(r"(?<=[.!?])\s+", _text(value)):
            if not sentence or sentence in seen:
                continue
            seen.add(sentence)
            lines = textwrap.wrap(sentence, width=42, break_long_words=False,
                                  break_on_hyphens=False)
            captions = ["\n".join(lines[index:index + 2]) for index in range(0, len(lines), 2)]
            weights = [max(1.5, len(caption) / 17.0) for caption in captions]
            # Keep the complete sentence or omit it, rather than silently
            # presenting just its first half when the measured clip is short.
            if used + sum(weights) > duration or len(accepted) + len(captions) > SRT_MAX_CUES:
                continue
            accepted.extend(zip(captions, weights))
            used += sum(weights)
    if not accepted:
        return []
    cues, start = [], 0.0
    for index, (caption, required) in enumerate(accepted):
        end = duration if index == len(accepted) - 1 else round(start + duration * required / used, 3)
        cues.append((start, end, caption))
        start = end
    return cues


def _srt_ts(sec):
    ms = max(0, int(round(sec * 1000)))
    hours, remainder = divmod(ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def format_srt(cues):
    return "\n".join(f"{i}\n{_srt_ts(start)} --> {_srt_ts(end)}\n{text}\n"
                     for i, (start, end, text) in enumerate(cues, 1))


def _is_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urllib.parse.urlsplit(value)
        return parsed.scheme in ("https", "http") and bool(parsed.hostname)
    except ValueError:
        return False


def _public_url(value):
    """Do not persist URL credentials, signatures, queries or fragments."""
    if not _is_url(value):
        return None
    parsed = urllib.parse.urlsplit(value)
    host = parsed.hostname
    if ":" in host:
        host = "[" + host + "]"
    try:
        if parsed.port:
            host += ":" + str(parsed.port)
    except ValueError:
        return None
    return urllib.parse.urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def _select_reference(ctx):
    images = ctx["product"].get("images") or []
    if isinstance(images, str):
        images = [images]
    for url in images:
        if _is_url(url):
            return url, {"url": _public_url(url), "source": "original_product_image",
                         "authority": "source_image", "fidelity": "not_verified"}
    main = ctx.get("main_image_url")
    if ctx.get("main_image_verified") is True and _is_url(main):
        return main, {"url": _public_url(main), "source": "verified_main_image",
                      "authority": "caller_verified_reference", "fidelity": "not_verified"}
    return None, {"url": None, "source": "none", "fidelity": "unknown"}


def _pick_segment_ref(ctx, frame_role, refs):
    """Compatibility helper: unverified generated anchors never replace source."""
    return _select_reference(ctx)[0]


def _capability_spec(ctx, model, known_kind, requested):
    """Local declarations only; no supplier capabilities are inferred or probed.

    video_capabilities={model: {durations: [5, 10, 15], size: '1280*720'}}
    is a caller assertion, NOT a built-in claim about any supplier. A new model
    additionally needs protocol='dashscope-video-v1' and kind='i2v'/'r2v'/'t2v'.
    This known protocol uses duration strings and the existing input fields;
    other protocols/parameters require an implemented, verified adapter first.
    """
    declarations = ctx.get("video_capabilities", {})
    if not isinstance(declarations, dict):
        raise ValueError("video_capabilities must be a local mapping")
    declared = model in declarations
    spec = declarations.get(model) if declared else {"durations": [5], "size": VIDEO_SIZE}
    if not isinstance(spec, dict) or set(spec) - {"durations", "size", "protocol", "kind", "endpoint"}:
        raise ValueError("unknown capability parameters; verification required")
    if not known_kind and (not declared or "protocol" not in spec or "kind" not in spec):
        raise ValueError("unknown model needs an explicit known-protocol declaration")
    kind = spec.get("kind", known_kind)
    if kind not in ("i2v", "r2v", "t2v") or (known_kind and kind != known_kind):
        raise ValueError("unsupported or conflicting video kind")
    if spec.get("protocol", "dashscope-video-v1") != "dashscope-video-v1":
        raise ValueError("unknown video protocol; no network probing allowed")
    endpoint = ctx.get("video_endpoint", spec.get("endpoint", VIDEO_ENDPOINTS[0]))
    if endpoint not in VIDEO_ENDPOINTS or ("endpoint" in spec and spec["endpoint"] != endpoint):
        raise ValueError("unsupported or conflicting video endpoint")
    durations, size = spec.get("durations"), spec.get("size")
    if (not isinstance(durations, (list, tuple)) or not durations
            or any(type(d) not in (int, float) or not math.isfinite(d) or d <= 0 for d in durations)
            or not isinstance(size, str) or not re.fullmatch(r"[1-9]\d{0,4}\*[1-9]\d{0,4}", size)):
        raise ValueError("invalid locally declared durations/size")
    covering = [duration for duration in durations if duration >= requested]
    if not covering:
        raise ValueError("requested duration exceeds locally declared capability; not submitted")
    return {"kind": kind, "duration": min(covering), "size": size, "endpoint": endpoint,
            "protocol": "dashscope-video-v1", "durations": sorted(set(durations)),
            "source": "caller_declared_not_probed" if declared else "existing_5s_spec"}


def _select_model(ctx, referenced, meta, requested):
    """Choose a covering local capability BEFORE the sole billable submission."""
    available = ctx.get("available_video_models")
    if isinstance(available, str):
        available = [available]
    chosen = ctx.get("video_model")
    candidates = dict(VIDEO_CHAIN)
    declarations = ctx.get("video_capabilities", {})
    if isinstance(declarations, dict):
        candidates.update({name: None for name in declarations if name not in candidates})
    if chosen and chosen not in candidates:
        candidates[chosen] = None
    failures = []
    for model, known_kind in candidates.items():
        if (available is not None and model not in available) or (chosen and chosen != model):
            continue
        try:
            spec = _capability_spec(ctx, model, known_kind, requested)
        except ValueError as exc:
            failures.append(str(exc))
            continue
        kind = spec["kind"]
        if kind in ("i2v", "r2v") and not referenced:
            continue
        if kind == "t2v" and ctx.get("allow_unreferenced_video") is not True:
            continue
        return model, kind, spec
    if failures or chosen or available is not None:
        meta.update(artifact_status="blocked_capability", blocked_capability=True,
                    capability_testing_status="pending_verification")
        meta["degradation"].extend(dict.fromkeys(failures or ["No eligible locally declared capability."]))
    else:
        meta["degradation"].append("No eligible reference-driven model; unreferenced video requires explicit opt-in.")
    return None, None, None


def _submit(task_client, model, kind, prompt, ref_url, deadline, parameters=None, label=None,
            endpoint=None):
    """Exactly one generation POST. Polling an existing task is not resubmission.

    TaskClient.generate has internal sync retries/async resubmission; use its
    already-observed synchronous wire format directly to avoid duplicate bills.
    Injected/offline clients receive exactly one generate call.
    """
    if deadline <= time.monotonic():
        raise ApiError("video deadline reached before submission")
    path = endpoint or VIDEO_ENDPOINTS[0]
    if path not in VIDEO_ENDPOINTS:
        raise ApiError("unobserved video endpoint is not allowed")
    input_obj = {"prompt": prompt}
    if kind in ("i2v", "r2v") and not ref_url:
        raise ApiError("reference required")
    if kind == "i2v":
        input_obj["img_url"] = ref_url
    elif kind == "r2v":
        input_obj["media"] = [ref_url]
    elif kind != "t2v":
        raise ApiError("unsupported video kind")
    if isinstance(task_client, dsapi.TaskClient):
        payload = {"model": model, "input": input_obj}
        if parameters:
            payload["parameters"] = parameters
        status, body, _ = dsapi._http_request(
            task_client.base_url + path, data=payload,
            headers={"Authorization": f"Bearer {task_client.api_key}"},
            timeout=max(0.001, min(600, deadline - time.monotonic())))
        dsapi._raise_for_status(status, body, "video")
        if status not in (200, 201, 202):
            raise ApiError("unexpected video submission status", status=status)
        output = json.loads(body.decode("utf-8")).get("output") or {}
        if output.get("task_id") and not extract_urls_from_output(output):
            output = task_client.poll(output["task_id"], deadline)
    else:
        output = task_client.generate(path, model, input_obj, parameters,
                                      deadline=deadline, label=label or f"video:{model}")
    if not isinstance(output, dict) or output.get("task_status") in ("FAILED", "UNKNOWN", "CANCELED"):
        raise ApiError("video task did not succeed")
    return output


def _submit_with_params(task_client, model, kind, prompt, ref_url, deadline, params):
    """Compatibility wrapper; parameters are never silently dropped/retried."""
    return _submit(task_client, model, kind, prompt, ref_url, deadline, params), params


def download_file(url, dest_path, max_retries=0, label="dl:video"):
    """Use shared authorization/deadline/size guards, without download retries."""
    size = dsapi.download_file(url, os.fspath(dest_path), max_retries=0, label=label)
    if size >= MAX_VIDEO_BYTES:
        raise ValueError("video exceeds the less-than-200-MB limit")
    return size


def _generate_segmented(ctx, shots, refs, deadline, meta):
    """Retired unsafe path: individual segments are NEVER promoted to a film."""
    meta.setdefault("degradation", []).append("Segmented generation disabled; no verified whole-film assembly is available.")
    return None


def _safe_failure(exc):
    # Provider exception text can contain signed URLs, credentials or prompts.
    status = getattr(exc, "status", None)
    suffix = f" (HTTP {status})" if isinstance(status, int) else ""
    return f"{type(exc).__name__}{suffix}; stopped without resubmission"


def _write_manifest(output_dir, meta):
    path = os.path.join(output_dir, "video_manifest.json")
    meta["manifest_path"] = path
    # All fields are constructed here, not raw ctx/provider outputs. Strip URL
    # queries in source text as well as reference metadata before persistence.
    def sanitize(value):
        if isinstance(value, str):
            return re.sub(r"https?://[^\s<>\"']+", lambda m: _public_url(m.group()) or "[URL omitted]", value)
        if isinstance(value, dict):
            return {key: sanitize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        return value
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(sanitize(meta), stream, ensure_ascii=False, indent=2, allow_nan=False)
    return path


def generate_video(ctx):
    """Plan and optionally submit one complete reference-driven clip.

    video_plan_only/offline: no network. video_capabilities: caller-declared
    durations/size and optionally a known protocol for an explicitly named model.
    requested_duration_seconds (or video_duration_seconds) defaults to a complete
    5s short clip, distinct from the 15/30s editorial plan, not a contest minimum.
    No covering capability means no paid submission. Human review remains needed:
    container inspection is not fidelity/decoding proof.
    """
    product, output_dir = ctx["product"], os.path.abspath(ctx["output_dir"])
    remaining = max(0.0, float(ctx["budget"].remaining()))
    requested = ctx.get("requested_duration_seconds", ctx.get("video_duration_seconds", DEFAULT_CLIP_SECONDS))
    invalid_requested = isinstance(requested, bool)
    try:
        requested = float(requested)
        if not math.isfinite(requested) or requested <= 0 or invalid_requested:
            raise ValueError
    except (ValueError, TypeError):
        requested, invalid_requested = None, True
    shots = (build_shot_prompts(product, ctx.get("vision_brief")) if remaining >= 300
             else build_compressed_shot_prompts(product, ctx.get("vision_brief")))
    ref_url, reference = _select_reference(ctx)
    meta = {
        "path": None, "model": None, "kind": None, "prompt_mode": "single-clip",
        "artifact_status": "planned_only", "needs_review": True, "blocked_capability": False,
        "requested_duration_seconds": requested, "requested_clip_duration_seconds": None,
        "delivery_scope": "self_contained_short_clip", "contest_minimum_duration_seconds": None,
        "actual_duration_seconds": None, "duration_seconds": None, "video_bytes": None,
        "reference": reference, "segments": [], "degradation": [],
        "planned": {"storyboard": shots, "storyboard_duration_seconds": shots[-1]["end"],
                    "storyboard_status": "plan_only_not_delivered", "submission_count_limit": 1,
                    "clip_duration_seconds": None,
                    "duration_status": "target_only_actual_pending_inspection"},
        "delivered": {"clip_count": 0, "duration_seconds": None, "has_video": False,
                      "has_audio": False, "storyboard_status": "not_verified"},
        "subtitles": {"status": "not_generated", "path": None, "cues": 0, "total_seconds": None},
        "bgm": {"status": "not_generated", "mixed": False, "file": None},
        "limitations": ["Container inspection only; codec decoding/playback is not verified.",
                        "Visual product fidelity and planned shot coverage are not verified.",
                        "Subtitles are sidecar-only, never burned in; BGM is not generated or mixed.",
                        "One self-contained clip is not delivery of the five-shot editorial plan."],
    }
    ctx["video_meta"] = meta
    meta["srt"] = meta["subtitles"]  # backwards-compatible metadata alias
    if invalid_requested:
        model = kind = spec = None
        meta.update(artifact_status="blocked_capability", blocked_capability=True,
                    capability_testing_status="pending_verification")
        meta["degradation"].append("Invalid requested duration; no submission allowed.")
    else:
        model, kind, spec = _select_model(ctx, bool(ref_url), meta, requested)
    meta.update(model=model, kind=kind + "-single" if kind else None)
    if kind == "t2v":
        meta["reference"] = {"url": None, "source": "none", "fidelity": "unknown"}
        meta["limitations"].append("Explicitly opted-in unreferenced draft; text does not restore product fidelity.")
    prompt = None
    meta["planned"]["parameters"] = None
    if spec:
        selected = spec["duration"]
        prompt = _clip_prompt(product, selected, bool(ref_url) and kind != "t2v")
        meta.update(requested_clip_duration_seconds=selected, capability=spec)
        meta["planned"].update(clip_duration_seconds=selected, clip_prompt=prompt,
                                parameters={"duration": f"{selected:g}s", "size": spec["size"]})
    candidate = None
    offline = ctx.get("video_plan_only") is True or ctx.get("offline") is True
    if not offline and model and remaining >= SEGMENT_COST_SECONDS:
        deadline = time.monotonic() + min(remaining * 0.8, 15 * 60)
        try:
            output = _submit(ctx["task_client"], model, kind, prompt,
                             ref_url if kind != "t2v" else None, deadline,
                             meta["planned"]["parameters"], endpoint=spec["endpoint"])
            urls = extract_urls_from_output(output)
            if not urls or not _is_url(urls[0]):
                raise ApiError("video succeeded without an artifact URL")
            descriptor, candidate = tempfile.mkstemp(prefix=".video_candidate_", suffix=".mp4", dir=output_dir)
            os.close(descriptor)
            download_file(urls[0], candidate, max_retries=0)
            inspection = inspect_video(candidate)
            meta["inspection"] = inspection
            if not inspection["valid"]:
                meta["artifact_status"] = inspection.get("status", "invalid")
                meta["degradation"].extend(inspection["errors"])
            else:
                path = os.path.join(output_dir, "product_video.mp4")
                os.replace(candidate, path)
                candidate = None
                actual = inspection["duration_seconds"]
                covers_target = actual + max(0.5, requested * 0.05) >= requested
                matches_spec = abs(actual - selected) <= max(0.5, selected * 0.05)
                duration_ok = covers_target and matches_spec
                meta.update(path=path, duration_seconds=actual, actual_duration_seconds=actual,
                            video_bytes=os.path.getsize(path),
                            artifact_status="needs_review" if duration_ok else "partial")
                meta["delivered"].update(clip_count=1, duration_seconds=actual,
                                         video_start_seconds=inspection.get("video_start_seconds", 0),
                                         width=inspection["width"], height=inspection["height"],
                                         has_video=True, has_audio=inspection["has_audio"],
                                         meets_duration_target=covers_target,
                                         matches_selected_duration=matches_spec,
                                         clip_completeness="complete_short_clip" if duration_ok else "partial")
                if not duration_ok:
                    meta["limitations"].append("Measured clip duration does not match the selected specification or cover the delivery target.")
        except Exception as exc:
            meta["artifact_status"] = "failed"
            meta["degradation"].append(_safe_failure(exc))
            log.warning("video: %s", _safe_failure(exc))
        finally:
            if candidate and os.path.isfile(candidate):
                os.unlink(candidate)
    elif offline:
        meta["degradation"].append("Offline plan only; no model or network calls.")
    elif remaining < SEGMENT_COST_SECONDS:
        meta["degradation"].append("Insufficient budget for one clip; planning only.")

    verified_features = _verified_subtitle_features(ctx)
    meta["subtitles"].update(language="en", source="ctx.verified_subtitle_features",
                             verification="caller_attested" if verified_features else "not_verified")
    if meta["path"] and verified_features:
        # Keep millisecond-resolution cues inside the actual presentation range,
        # including fractional starts after empty edits (never round past its end).
        content_start = meta["delivered"]["video_start_seconds"]
        start_ms = math.ceil(content_start * 1000)
        end_ms = math.floor((content_start + meta["actual_duration_seconds"]) * 1000)
        start = start_ms / 1000
        cues = build_srt_entries(verified_features, "", [], (end_ms - start_ms) / 1000)
        if cues:
            cues = [(begin + start, end + start, text) for begin, end, text in cues]
            srt_path = os.path.join(output_dir, "product_video_srt.srt")
            try:
                with open(srt_path, "w", encoding="utf-8") as stream:
                    stream.write(format_srt(cues))
                meta["subtitles"].update(status="sidecar_only", path=srt_path, cues=len(cues),
                                         total_seconds=meta["actual_duration_seconds"], start_seconds=start)
            except OSError:
                meta["limitations"].append("Subtitle sidecar could not be written.")
    if meta["subtitles"]["status"] == "not_generated":
        meta["subtitles"]["reason"] = "No caller-verified English cues fitting a measured delivered timeline."
    meta["planned"]["subtitle_sources"] = [_text(product.get("subject")), *_source_facts(product)]
    meta["planned"]["subtitle_sources_status"] = "source_language_draft_not_verified_english"
    meta["planned"]["subtitle_copy_draft"] = extract_key_features(os.path.join(output_dir, "product_description_en.md"))
    meta["planned"]["bgm"] = {"status": "instruction_only", "generated": False,
                                "instruction": "Optional instrumental only after licensed audio is available; no mixing performed."}
    # Do not accidentally expose a previous run's output as this run's result.
    for filename, active in (("product_video.mp4", meta["path"]),
                             ("product_video_srt.srt", meta["subtitles"]["path"])):
        stale = os.path.join(output_dir, filename)
        if not active and os.path.isfile(stale):
            meta["limitations"].append(f"Pre-existing {filename} is not a delivery of this run; consult this manifest.")
    _write_manifest(output_dir, meta)
    return meta
