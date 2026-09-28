# -*- coding: utf-8 -*-
"""StyleRouter: market x category x emotion x scene -> StyleProfile.

Deterministic rule-based routing with five style families. The profile injects
aesthetic modifiers into image prompts, copy tone, and detail-image themes.

Style families:
  minimal-studio    clean white studio (simple-track default, AE main-image safe)
  kr-emotional      Korean sensibility: soft natural light, muted film tones
  us-clean-bold     US clean/bold: bright, high-clarity lifestyle
  br-warm-vibrant   Brazilian warmth: golden light, warm vibrant scenes
  premium-editorial high-end editorial studio (elegant/business positioning)
"""
import logging

log = logging.getLogger("agent")

# ---------- detection rules (Chinese source data) ----------

EMOTION_RULES = [
    ("elegant", ["气质", "优雅", "名媛", "轻熟", "高级感", "法式", "赫本"]),
    ("business", ["通勤", "职业", "西装", "正装", "办公", "商务"]),
    ("sweet", ["甜美", "少女", "可爱", "减龄", "软糯", "公主", "学院风"]),
    ("sporty", ["运动", "街头", "嘻哈", "oversize", "宽松卫衣", "港风"]),
    ("cozy", ["慵懒", "居家", "柔软", "针织", "舒适", "保暖"]),
    ("sexy", ["性感", "修身", "紧身", "吊带", "露背", "包臀"]),
]

CATEGORY_RULES = [
    ("bottoms", ["半身裙", "短裙", "百褶裙", "裤", "牛仔", "阔腿"]),
    ("dresses", ["连衣裙", "吊带裙", "衬衫裙"]),
    ("tops", ["衬衫", "衬衣", "T恤", "卫衣", "毛衣", "针织", "开衫", "马甲", "背心", "打底", "雪纺", "上衣", "Polo"]),
    ("outerwear", ["外套", "大衣", "风衣", "羽绒", "夹克", "棉服"]),
    ("shoes", ["鞋", "靴", "凉鞋", "拖鞋"]),
    ("underwear", ["内衣", "文胸", "睡衣", "家居服"]),
    ("accessories", ["包", "帽", "围巾", "腰带", "袜"]),
]

SCENE_RULES = [
    ("commute", ["通勤", "办公", "职场", "上班"]),
    ("date", ["约会", "名媛", "宴会", "聚会"]),
    ("outdoor", ["户外", "旅游", "旅行", "沙滩", "海边", "防晒", "出游", "度假"]),
    ("party", ["派对", "节日", "年会", "婚礼", "晚礼"]),
    ("home", ["居家", "睡衣", "室内", "宅家"]),
    ("daily", ["日常", "休闲", "百搭", "四季", "春秋", "夏季", "冬季"]),
]


def _match(rules, text):
    low = text.lower()
    for label, kws in rules:
        for kw in kws:
            if kw.lower() in low:
                return label, kw
    return None, None


def analyze_product(product):
    """Extract routing signals from source product data."""
    title = product.get("subject") or ""
    attr_text = " ".join(
        (a.get("valueTrans") or a.get("value") or "") + " " + (a.get("attributeNameTrans") or "")
        for a in (product.get("attributes") or [])
    )
    text = title + " " + attr_text

    emotion, emo_kw = _match(EMOTION_RULES, text)
    category, cat_kw = _match(CATEGORY_RULES, text)
    scene, scene_kw = _match(SCENE_RULES, text)
    result = {
        "emotion": emotion or "casual",
        "category": category or "tops",
        "scene": scene or "daily",
        "keywords": {"emotion": emo_kw, "category": cat_kw, "scene": scene_kw},
    }
    log.info("style signals: %s", result)
    return result


# ---------- style profiles ----------

PROFILES = {
    "minimal-studio": {
        "image_modifiers": (
            "Minimalist studio aesthetic: pure white seamless background, soft even softbox lighting, "
            "gentle natural shadow under the product, centered composition with balanced negative space, "
            "crisp focus, true-to-life colors, premium catalog look."
        ),
        "detail_palette": "neutral whites and light grays",
        "copy_accent": "clean, precise, confidence-through-simplicity",
    },
    "kr-emotional": {
        "image_modifiers": (
            "Korean sensibility aesthetic: soft diffused natural window light, low-saturation muted pastel "
            "film tones, gentle grain, airy atmosphere, delicate feminine mood, editorial Korean fashion "
            "magazine look, warm ivory and beige palette."
        ),
        "detail_palette": "muted ivory, beige, soft pink film tones",
        "copy_accent": "warm sensory atmosphere, delicate fabric descriptions, soft polite tone",
    },
    "us-clean-bold": {
        "image_modifiers": (
            "American clean e-commerce aesthetic: bright crisp lighting, high clarity, confident modern "
            "composition, clean urban or bright lifestyle backdrop, saturated but natural colors, "
            "body-positive inclusive styling."
        ),
        "detail_palette": "bright neutrals with confident accent colors",
        "copy_accent": "benefit-led, energetic, action-oriented",
    },
    "br-warm-vibrant": {
        "image_modifiers": (
            "Brazilian warm aesthetic: golden-hour sunlight, warm vibrant tones, joyful lively atmosphere, "
            "natural outdoor or sun-lit indoor scene, relaxed friendly mood, rich warm color palette."
        ),
        "detail_palette": "warm golden, terracotta and lively accents",
        "copy_accent": "warm, enthusiastic, close and friendly",
    },
    "premium-editorial": {
        "image_modifiers": (
            "Premium editorial aesthetic: dramatic refined studio lighting with soft rim light, luxurious "
            "minimal staging, sophisticated neutral palette with deep accents, high-fashion magazine "
            "composition, elegant negative space."
        ),
        "detail_palette": "deep neutrals, champagne and charcoal accents",
        "copy_accent": "refined, sophisticated, quietly confident",
    },
}

MARKET_BASE = {"en": "us-clean-bold", "ko": "kr-emotional", "pt": "br-warm-vibrant"}

# emotion overrides applied on top of the market base style
EMOTION_OVERRIDES = {
    "elegant": "premium-editorial",
    "business": "premium-editorial",
}

# detail-image themed order per style (5 slots)
DETAIL_THEMES = {
    "minimal-studio": [
        "hero composition highlighting the core selling point on a clean background",
        "macro close-up of craftsmanship: stitching, waistband or pattern",
        "macro close-up of fabric texture and material quality",
        "flat-lay composition showing the full silhouette and proportions",
        "multi-angle neutral studio display",
    ],
    "kr-emotional": [
        "atmospheric shot with soft window light, dreamy Korean mood",
        "delicate detail close-up with shallow depth of field",
        "fabric texture macro in soft natural light",
        "lifestyle scene in a cozy cafe or sunlit street, editorial Korean style",
        "airy full-body composition with gentle film tones",
    ],
    "us-clean-bold": [
        "dynamic hero composition with bright confident lighting",
        "craftsmanship close-up with crisp detail",
        "fabric quality macro, bright and clean",
        "urban lifestyle scene with diverse inclusive styling",
        "clean multi-angle catalog display",
    ],
    "br-warm-vibrant": [
        "vibrant hero composition in golden light",
        "craftsmanship close-up with warm tones",
        "fabric texture macro in sunlight",
        "joyful outdoor lifestyle scene with warm atmosphere",
        "sun-lit full display showing drape and movement",
    ],
    "premium-editorial": [
        "editorial hero with dramatic refined lighting",
        "luxury detail close-up with rim light",
        "material texture macro, sophisticated staging",
        "high-fashion editorial scene with elegant posing",
        "gallery-style multi-angle presentation",
    ],
}


def route_style(product, market_lang, mode, signals=None):
    """Build the StyleProfile for one market language.

    mode: "professional" -> market/emotion routed; "simple" -> minimal-studio.
    """
    if signals is None:
        signals = analyze_product(product)

    if mode == "simple":
        name = "minimal-studio"
    else:
        base = MARKET_BASE.get(market_lang, "minimal-studio")
        name = EMOTION_OVERRIDES.get(signals["emotion"], base)

    profile = PROFILES[name]
    return {
        "name": name,
        "mode": mode,
        "market_lang": market_lang,
        "signals": signals,
        "image_modifiers": profile["image_modifiers"],
        "palette": profile["detail_palette"],
        "copy_accent": profile["copy_accent"],
        "detail_themes": DETAIL_THEMES[name],
    }


def global_image_profile(product, mode, signals=None):
    """Style profile for assets shared across markets (main image, video).

    Main image must stay white/clean per AE spec; the routed style only
    refines lighting/composition quality while the white background is kept.
    """
    if signals is None:
        signals = analyze_product(product)
    if mode == "simple":
        style_name = "minimal-studio"
    else:
        style_name = EMOTION_OVERRIDES.get(signals["emotion"], "kr-emotional")
    profile = PROFILES[style_name]
    return {
        "style_name": style_name,
        "image_modifiers": profile["image_modifiers"],
        "palette": profile["detail_palette"],
        "copy_accent": profile["copy_accent"],
        "detail_themes": DETAIL_THEMES[style_name],
        "lighting_refinement": (
            "soft diffused studio light with gentle depth, delicate shadows, "
            "premium catalog lighting quality"
        ),
        "signals": signals,
    }
