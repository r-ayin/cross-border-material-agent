# -*- coding: utf-8 -*-
"""URL-only image quality checks against authoritative source product images."""
import logging
import math
import re
import time

from .dsapi import extract_json_block

log = logging.getLogger("agent")

CRITIC_MODEL_PRIMARY = "qwen-vl-max"
CRITIC_MODEL_FALLBACK = "qwen3-vl-plus"
SCORE_KEYS = ("background_cleanliness", "product_fidelity", "aesthetic_appeal", "artifact_free")
ROLE_REQUIREMENTS = {
    'main_image': 'One complete product alone, uncropped, on pure white background.',
    'detail_image_1': 'Whole-product selling-point composition, clear source-visible distinctive feature.',
    'detail_image_2': 'Actual close-up of source-visible craftsmanship/edge/seam; a repeated full-product view fails.',
    'detail_image_3': 'Actual close-up of source-visible material appearance; a repeated full-product view fails.',
    'detail_image_4': 'Recognizable lifestyle setting; plain-background cutout or repeated catalog image fails.',
    'detail_image_5': 'Complete uncropped product overview in one source-supported view, no invented angles.',
}

CRITIC_SYSTEM = """You are a strict e-commerce visual quality judge.
Source reference images are the authority, not the generated candidate or its prompt.
Return ONLY a JSON object. If evidence is insufficient, use verdict=unknown."""

CRITIC_USER = """Score the GENERATED CANDIDATE on four dimensions, each a number 0-10:
1. background_cleanliness: appropriate uncluttered background, no text/watermark.
   A lifestyle scene need not have a white background.
2. product_fidelity: compare directly with the SOURCE REFERENCES: same product,
   color, silhouette, proportions, pattern, visible construction and surface texture.
   Do not reward plausible but invented backs, seams, closures or material details.
   A crop may show only source-supported details. If no reference is supplied or
   fidelity cannot be determined, use verdict=unknown, never accept.
3. aesthetic_appeal: lighting, composition and clarity without altering the product.
4. artifact_free: no broken geometry, garbled text or distorted anatomy/objects.
Return JSON: {"scores":{"background_cleanliness":N,"product_fidelity":N,"aesthetic_appeal":N,"artifact_free":N},"total":N,"verdict":"accept|retry|unknown","reason":"one short sentence"}
Use retry if total<26, any dimension<5, or a known product mismatch is visible.
The total must be the sum of all four scores (0-40)."""

COMPLIANCE_SYSTEM = (
    "You are a strict e-commerce listing compliance inspector. "
    "Inspect the generated candidate for prohibited visual elements."
)
COMPLIANCE_USER = (
    "Does this image contain text/words/letters, watermark, logo, promotional "
    "stickers, price tags, borders/frames/collage overlays or other promotional "
    "elements? An appropriate lifestyle setting or normally dressed person is "
    "not itself a violation. Answer exactly 'YES <short reason>' if a violation "
    "is visible, 'NO' if clean, or 'UNKNOWN' if you cannot determine this."
)


def validate_critique(critique):
    """Return normalized scores, or None for malformed data; never trust total."""
    if not isinstance(critique, dict):
        return None
    scores = critique.get("scores")
    if not isinstance(scores, dict) or set(scores) != set(SCORE_KEYS):
        return None
    for value in scores.values():
        if (type(value) not in (int, float) or not 0 <= value <= 10
                or not math.isfinite(value)):
            return None
    total = sum(scores.values())
    verdict = critique.get("verdict")
    if verdict not in ("accept", "retry", "unknown"):
        verdict = "unknown"
    if total < 26 or min(scores.values()) < 5 or critique.get('role_match') is False:
        verdict = "retry"
    reason = critique.get("reason")
    return {
        "scores": dict(scores), "total": total, "verdict": verdict,
        "reason": reason if isinstance(reason, str) else "",
    }


def _references(reference_urls):
    if isinstance(reference_urls, str):
        reference_urls = [reference_urls]
    return [u.strip() for u in (reference_urls or [])
            if isinstance(u, str) and u.strip().startswith(("https://", "http://"))][:5]


def _timeout(deadline):
    remaining = 90 if deadline is None else min(90, deadline - time.monotonic())
    if remaining <= 0:
        return None
    return (min(15, remaining), remaining)


def score_image_url(chat, image_url, label="image", reference_urls=None, deadline=None):
    """Compare a candidate URL with source URLs; unavailable checks return None.

    Malformed responses return an explicit retry report, not an unavailable check.
    Optional arguments preserve the existing URL-only call interface.
    """
    if not image_url:
        return None
    refs = _references(reference_urls)
    content = []
    for i, url in enumerate(refs, 1):
        content.extend([
            {"type": "text", "text": f"SOURCE REFERENCE {i} (authoritative product evidence):"},
            {"type": "image_url", "image_url": {"url": url}},
        ])
    role = ROLE_REQUIREMENTS.get(label)
    role_note = ('\nREQUIRED SLOT ROLE: ' + role +
                 '\nAlso return role_match as true, false or null. Wrong role MUST use verdict=retry, even if visually attractive.') if role else ''
    content.extend([
        {"type": "text", "text": "GENERATED CANDIDATE (evaluate this image, not the references):"},
        {"type": "image_url", "image_url": {"url": image_url}},
        {"type": "text", "text": CRITIC_USER + role_note},
    ])
    malformed = False
    for model in (CRITIC_MODEL_PRIMARY, CRITIC_MODEL_FALLBACK):
        timeout = _timeout(deadline)
        if timeout is None:
            break
        try:
            out = chat.chat(model, [
                {"role": "system", "content": CRITIC_SYSTEM},
                {"role": "user", "content": content},
            ], temperature=0.1, max_tokens=600, timeout=timeout)
            if deadline is not None and time.monotonic() >= deadline:
                break
            raw = extract_json_block(out)
            parsed = validate_critique(raw)
            if parsed is not None and role:
                parsed['role_match'] = raw.get('role_match')
                if raw.get('role_match') is not True and parsed['verdict'] == 'accept':
                    parsed['verdict'] = 'retry' if raw.get('role_match') is False else 'unknown'
                    parsed['reason'] = 'Required slot role not verified: ' + role
            if parsed is None:
                malformed = True
                log.warning("critic[%s] malformed scores from %s", label, model)
                continue
            if not refs and parsed["verdict"] == "accept":
                parsed["verdict"] = "unknown"
                parsed["reason"] = "Source references unavailable; product fidelity unverified."
            parsed["reference_checked"] = bool(refs)
            parsed["model"] = model
            log.info("critic[%s] via %s: total=%s verdict=%s",
                     label, model, parsed["total"], parsed["verdict"])
            return parsed
        except Exception as e:
            log.warning("critic failed for %s with %s: %s", label, model, str(e)[:150])
    if malformed:
        return {"verdict": "retry", "reason": "Malformed critic scores", "invalid": True}
    return None


def check_compliance(chat, image_url, label="image", deadline=None):
    """True = known violation, False = explicitly clean, None = unknown."""
    if not image_url:
        return None
    content = [
        {"type": "image_url", "image_url": {"url": image_url}},
        {"type": "text", "text": COMPLIANCE_USER},
    ]
    for model in (CRITIC_MODEL_PRIMARY, CRITIC_MODEL_FALLBACK):
        timeout = _timeout(deadline)
        if timeout is None:
            break
        try:
            out = chat.chat(model, [
                {"role": "system", "content": COMPLIANCE_SYSTEM},
                {"role": "user", "content": content},
            ], temperature=0.0, max_tokens=160, timeout=timeout)
            if deadline is not None and time.monotonic() >= deadline:
                break
            text = out.strip().upper() if isinstance(out, str) else ""
            if re.fullmatch(r"YES(?:[\s:,.!-].*)?", text):
                return True
            # Do not mistake 'NOT SURE', 'NO, there is a logo', etc. for clean.
            if text in ("NO", "NO."):
                return False
            log.warning("compliance[%s] ambiguous answer from %s", label, model)
        except Exception as e:
            log.warning("compliance failed for %s with %s: %s", label, model, str(e)[:150])
    return None


def pick_best_url(chat, image_urls, label="image", reference_urls=None, deadline=None):
    """Return only an accepted candidate, or None; unknown/retry cannot win."""
    report = []
    accepted = []
    for url in image_urls:
        if not url or _timeout(deadline) is None:
            continue
        score = score_image_url(chat, url, label=label,
                                reference_urls=reference_urls, deadline=deadline)
        validated = validate_critique(score)
        report.append({"url": url, "total": validated["total"] if validated else None,
                       "verdict": validated["verdict"] if validated else "unknown"})
        if validated and not should_retry(validated):
            accepted.append((validated["total"], url))
    return (max(accepted, key=lambda item: item[0])[1] if accepted else None), report


def should_retry(critique):
    """Unknown/malformed reports must never be interpreted as acceptance."""
    validated = validate_critique(critique)
    return validated is None or validated["verdict"] != "accept"
