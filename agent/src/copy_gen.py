# -*- coding: utf-8 -*-
"""Evidence-first localized copy and an explicit, offline-testable quality gate.

Heuristics are deliberately conservative: a plausible translation is not proof of
measurements, care or shipping claims. Unverifiable drafts remain needs_review.
"""
import json
import logging
import os
import queue
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from .prompts import COPY_SYSTEM, COPY_USER_TEMPLATE, MARKET_GUIDANCE

log = logging.getLogger("agent")
COPY_MODEL_PRIMARY = "qwen3.8-max"
COPY_MODEL_FALLBACK = "qwen3.7-max"
LANGS = [("en", "English", "US", "en"),
         ("ko", "Korean", "KR", "ko"),
         ("pt", "Brazilian Portuguese", "BR", "pt")]
SECTION_ORDER = ["Key Features", "Product Information", "Size Chart",
                 "Source Information", "Image Guide", "Video"]
SECTION_HEADERS = {
    "en": SECTION_ORDER,
    "ko": ["주요 특징", "상품 정보", "사이즈 차트", "출처 정보", "이미지 가이드", "비디오"],
    "pt": ["Principais Características", "Informações do Produto", "Tabela de Tamanhos",
           "Informações da Origem", "Guia de Imagens", "Vídeo"],
}
# Only localized headings count; an English heading cannot satisfy a Korean section.
SECTION_ALIASES = {
    "en": [("key features", "key feature"), ("product information", "product info"),
           ("size chart", "size guide", "sizing"), ("source information", "source info"),
           ("image guide",), ("video",)],
    "ko": [("주요 특징", "주요특징", "핵심 특징"), ("상품 정보", "상품정보", "제품 정보"),
           ("사이즈 차트", "사이즈 가이드", "치수"), ("출처 정보", "원본 정보"),
           ("이미지 가이드", "이미지 안내"), ("비디오", "동영상")],
    "pt": [("principais características", "principais caracteristicas", "características principais"),
           ("informações do produto", "informacoes do produto", "informação do produto"),
           ("tabela de tamanhos", "guia de tamanhos", "tabela de medidas"),
           ("informações da origem", "informacoes da origem", "informações de origem"),
           ("guia de imagens", "guia de imagem"), ("vídeo", "video", "vídeo do produto")],
}
LOCAL = {
    "en": {
        "title": "Product details", "raw": "Original source data (untranslated)",
        "features": "Selling points require verification against the source data below.",
        "missing": "Not provided in source", "pending": "Pending source verification",
        "measured": "Measurements occur in the source data below; verify each SKU and dimension before publication.",
        "size": "Original size label", "measurement": "Measurement",
        "platform": "Source platform", "id": "Product ID", "url": "Source URL",
        "size_bullet": "Source size", "source_bullet": "Source",
        "images": "Image availability and depicted details require verification.",
        "video": "Video availability and depicted details require verification.",
        "keywords": "Search Keywords",
    },
    "ko": {
        "title": "상품 정보", "raw": "원본 출처 데이터 (번역하지 않음)",
        "features": "아래 원본 데이터를 기준으로 상품 특징을 확인해야 합니다.",
        "missing": "소스에 제공되지 않음", "pending": "원본 확인 필요",
        "measured": "아래 원본 데이터에 측정 정보가 있습니다. 게시 전에 각 SKU와 측정 항목을 확인해야 합니다.",
        "size": "원본 사이즈 표기", "measurement": "측정값",
        "platform": "출처 플랫폼", "id": "상품 ID", "url": "출처 URL",
        "size_bullet": "원본 사이즈", "source_bullet": "출처",
        "images": "이미지 제공 여부와 표시된 상품 정보를 확인해야 합니다.",
        "video": "동영상 제공 여부와 표시된 상품 정보를 확인해야 합니다.",
        "keywords": "검색 키워드",
    },
    "pt": {
        "title": "Informações do produto", "raw": "Dados originais da fonte (sem tradução)",
        "features": "Os destaques precisam ser verificados nos dados da fonte abaixo.",
        "missing": "Não informado na origem", "pending": "Verificação da fonte pendente",
        "measured": "Há medidas nos dados da fonte abaixo; verifique cada SKU e dimensão antes da publicação.",
        "size": "Tamanho original", "measurement": "Medida",
        "platform": "Plataforma de origem", "id": "ID do produto", "url": "URL de origem",
        "size_bullet": "Tamanho na fonte", "source_bullet": "Origem",
        "images": "A disponibilidade das imagens e os detalhes exibidos precisam de verificação.",
        "video": "A disponibilidade do vídeo e os detalhes exibidos precisam de verificação.",
        "keywords": "Palavras-chave",
    },
}
NO_MEASURE_TEXT = {lang: strings["missing"] for lang, strings in LOCAL.items()}
UNIT_PATTERN = r'(?:cm\b|mm\b|inches?\b|inch\b|센티미터|밀리미터|인치|厘米|毫米|英寸|cent[ií]metros?\b|centimeters?\b|″|")'
MEASURE_RE = re.compile(
    r'(?<![\w/])\d+(?:[.,]\d+)?(?:\s*[-–—~至]\s*\d+(?:[.,]\d+)?)?\s*'
    + UNIT_PATTERN + r'(?!\w)', re.I)
INCH_SPAN_RE = re.compile(r'\d+(?:\.\d+)?\s*[″"]\s*[-–—~至]\s*\d+(?:\.\d+)?\s*[″"]')
UNIT_RE = re.compile(UNIT_PATTERN, re.I)
URL_RE = re.compile(r'https?://[^\s<>"`]+')
NUMBER_RE = re.compile(r'(?<!\w)\d+(?:[.,]\d+)?(?!\w)')
IDENTITY_NAME_RE = re.compile(r'model|型号|型號|모델|modelo|货号|款号|(?:^|[ _])id$', re.I)
SIZE_NAME_RE = re.compile(r'size|尺码|尺寸|사이즈|tamanho', re.I)
JSON_FENCE_RE = re.compile(r'```(?:json)?\s*\n(.*?)\n```', re.S)


def _json(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


def _same_json(left, right):
    # Python equality conflates True/1 and 4.0/4; source types must survive too.
    return json.dumps(left, sort_keys=True, ensure_ascii=False) == json.dumps(right, sort_keys=True, ensure_ascii=False)


def _records(value):
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _leaves(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from _leaves(child)
    elif isinstance(value, list):
        for child in value:
            yield from _leaves(child)
    elif value is not None and not isinstance(value, bool):
        yield str(value)


def _attribute_pairs(product):
    attrs = list(_records(product.get("attributes")))
    for sku in _records(product.get("skus")):
        attrs.extend(_records(sku.get("skuAttributes")))
    for attr in attrs:
        # Preserve both original and translated evidence, not just valueTrans.
        for name_key, value_key in (("attributeName", "value"),
                                    ("attributeNameTrans", "valueTrans")):
            name = str(attr.get(name_key) or attr.get("attributeName") or "")
            value = attr.get(value_key)
            if value is not None:
                yield name, str(value)


def _identity_values(product):
    values = set()

    def visit(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if re.search(r'id$|^model|^url$', key, re.I) and isinstance(value, (str, int)):
                    values.add(str(value))
                visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)

    visit(product)
    for name, value in _attribute_pairs(product):
        if IDENTITY_NAME_RE.search(name):
            values.add(value)
    return {value for value in values if value}


def _mask_identifiers(text, product):
    """Protect entire URLs/identifiers, not all numbers or entire source lines."""
    tokens = list(_identity_values(product))
    tokens.extend(URL_RE.findall(text))
    if not tokens:
        return text, {}
    pattern = re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(s) for s in sorted(set(tokens), key=len, reverse=True)) + r')(?!\w)')
    saved = {}

    def hide(match):
        # Non-numeric placeholders cannot be mistaken for measurements.
        key = '\ufff0' + chr(0xE000 + len(saved)) + '\ufff1'
        saved[key] = match.group()
        return key

    return pattern.sub(hide, text), saved


def _restore(text, saved):
    for key, value in saved.items():
        text = text.replace(key, value)
    return text


def _evidence_texts(product):
    texts = [str(product.get(key) or "") for key in ("subject", "subject_trans", "description_html")]
    texts += [name + ': ' + value for name, value in _attribute_pairs(product)
              if not IDENTITY_NAME_RE.search(name)]
    texts += list(_leaves(product.get("measurements", {})))
    return [_mask_identifiers(re.sub(r'<[^>]*>', ' ', text), product)[0] for text in texts]


def _source_has_measurements(product):
    product = product or {}
    if (product.get("measurements_missing") is True or product.get("has_measurements") is False
            or product.get("measurements_provided") is False):
        return False
    # A boolean flag without actual data is not evidence. Header units + numeric
    # cells count as possible evidence, but never authorize arbitrary dimensions.
    return any(MEASURE_RE.search(text) or (UNIT_RE.search(text) and NUMBER_RE.search(text))
               for text in _evidence_texts(product))


def _original_sizes(product):
    result = []
    for sku in _records(product.get("skus")):
        for attr in _records(sku.get("skuAttributes")):
            name = str(attr.get("attributeName") or "") + ' ' + str(attr.get("attributeNameTrans") or "")
            if SIZE_NAME_RE.search(name):
                value = attr.get("value")
                if value is None:
                    value = attr.get("valueTrans")
                if value is not None and str(value) not in result:
                    result.append(str(value))
    return result


def _raw_inventory(product):
    # Keep all original facts (including model IDs and description measurements),
    # not merely a selected/truncated subset. Local loader paths are not facts.
    return {key: value for key, value in product.items() if key != 'source_file'}


def _raw_block(product, lang):
    return LOCAL[lang]["raw"] + '\n\n```json\n' + _json(_raw_inventory(product)) + '\n```'


def _size_body(product, lang):
    local = LOCAL[lang]
    measured = _source_has_measurements(product)
    note = local["measured"] if measured else local["missing"]
    rows = []
    for size in _original_sizes(product):
        # Complex labels remain intact in the raw inventory, not reformatted as measurements.
        if not re.fullmatch(r'[A-Za-z0-9+ /-]{1,40}', size):
            continue
        rows.append(f'| {size} | {local["pending"] if measured else local["missing"]} |')
    if not rows:
        return note
    return (note + f'\n\n| {local["size"]} | {local["measurement"]} |\n| --- | --- |\n'
            + '\n'.join(rows))


def _section_name(line, lang):
    heading = re.sub(r'^#{1,6}\s+', '', line.strip()).strip('* :').casefold()
    for name, aliases in zip(SECTION_ORDER, SECTION_ALIASES[lang]):
        if heading in aliases:
            return name
    return None


def _section_bodies(text, lang):
    bodies, current, fenced = {}, None, False
    for line in text.splitlines():
        if line.strip().startswith('```'):
            fenced = not fenced
        if not fenced and re.match(r'^#\s+', line):
            current = None  # The product title is not a second listing section.
            continue
        name = None if fenced else _section_name(line, lang)
        if name:
            current = name
            bodies.setdefault(name, []).append([])
        elif not fenced and re.match(r'^#{1,6}\s+', line):
            current = None
        elif current:
            bodies[current][-1].append(line)
    return bodies


def _missing_sections(content_text, lang_code):
    bodies = _section_bodies(content_text or '', lang_code)
    return [name for name in SECTION_ORDER if name not in bodies]


def _source_body(product, lang):
    local = LOCAL[lang]
    return '\n'.join(f'- {local[label]}: {product.get(key) if product.get(key) not in (None, "") else local["missing"]}'
                     for label, key in (("platform", "platform"), ("id", "offer_id"), ("url", "url")))


def _safe_section(name, product, lang):
    local = LOCAL[lang]
    return {
        "Key Features": lambda: local["features"],
        "Product Information": lambda: _raw_block(product, lang),
        "Size Chart": lambda: _size_body(product, lang),
        "Source Information": lambda: _source_body(product, lang),
        "Image Guide": lambda: local["images"],
        "Video": lambda: local["video"],
    }[name]()


def _ensure_sections(content_text, lang_code, product, missing):
    """Append truthful localized blocks; callers MUST keep the repair review flag."""
    blocks = [content_text.rstrip()]
    for name, header in zip(SECTION_ORDER, SECTION_HEADERS[lang_code]):
        if name in missing:
            blocks.append(f'## {header}\n{_safe_section(name, product, lang_code)}')
    return '\n\n'.join(blocks)


def _sanitize_size_data(content_text, lang_code, product):
    """Sanitize tables as a unit, including bare numbers under a cm header.

    Unrelated identifiers/URLs and exact source JSON are opaque. Even with source
    measurements, a generated table is not proof of a SKU/dimension relationship.
    """
    product = product or {}
    raw_blocks = {}

    def protect_source(match):
        try:
            value = json.loads(match.group(1))
            if any(_same_json(value, allowed) for allowed in
                   [_raw_inventory(product), product.get('skus', []), product.get('attributes', [])]):
                key = '\ufff2' + chr(0xE000 + len(raw_blocks)) + '\ufff3'
                raw_blocks[key] = match.group()
                return key
        except ValueError:
            pass
        return match.group()

    text = JSON_FENCE_RE.sub(protect_source, content_text or '')
    text, saved = _mask_identifiers(text, product)
    marker = LOCAL[lang_code]["pending"] if _source_has_measurements(product) else NO_MEASURE_TEXT[lang_code]
    source_tokens = {m.group().casefold() for value in _evidence_texts(product) for m in MEASURE_RE.finditer(value)}
    if not _source_has_measurements(product):
        source_tokens = set()
    lines, result, index, in_size = text.splitlines(), [], 0, False
    while index < len(lines):
        line = lines[index]
        section = _section_name(line, lang_code)
        if section or re.match(r'^#{1,6}\s+', line):
            in_size = section == "Size Chart"
        if re.search(r'<table\b', line, re.I):
            table = []
            while index < len(lines):
                table.append(lines[index])
                index += 1
                if re.search(r'</table\s*>', table[-1], re.I):
                    break
            joined = '\n'.join(table)
            if in_size or UNIT_RE.search(joined):
                result.append(_size_body(product, lang_code))
                result.extend(key for key in saved if key in joined)
            else:
                result.append(joined)
            continue
        if '|' in line:
            table = []
            while index < len(lines) and '|' in lines[index]:
                table.append(lines[index])
                index += 1
            joined = '\n'.join(table)
            safe_table = '\n'.join(row for row in _size_body(product, lang_code).splitlines() if '|' in row)
            if _restore(joined, saved) == safe_table:
                result.append(joined)
            elif in_size or UNIT_RE.search(joined):
                result.append(_size_body(product, lang_code))
                # If an ID/URL was embedded in the rejected table, retain it verbatim.
                result.extend(key for key in saved if key in joined)
            else:
                result.append(joined)
            continue
        line = INCH_SPAN_RE.sub(lambda m: m.group() if m.group().casefold() in source_tokens else marker, line)
        line = MEASURE_RE.sub(lambda m: m.group() if m.group().casefold() in source_tokens else marker, line)
        result.append(line)
        index += 1
    return _restore(_restore('\n'.join(result), saved), raw_blocks)


def build_copy_prompt(ctx, lang_code):
    """Return a deterministic user prompt without I/O, mutation or model calls."""
    if lang_code not in LOCAL:
        raise ValueError(f'Unsupported copy language: {lang_code!r}; expected en, ko or pt')
    product = ctx.get("product") or {}
    lang = next(item for item in LANGS if item[0] == lang_code)
    note = ("Possible measurement evidence exists. Repeat only explicitly sourced SKU/dimension/value/unit relationships; no conversions. Unverified relationships require review."
            if _source_has_measurements(product) else
            f'No measured values are evidenced. All measurement cells, including bare numbers under unit headers, must say "{NO_MEASURE_TEXT[lang_code]}". No fabricated numeric sizes.')
    return COPY_USER_TEMPLATE.format(
        lang_code=lang_code, lang_name=lang[1], market_name=lang[2],
        source_json=_json(product),
        mapping_json=_json({"category_info": ctx.get("category_info") or {}, "attr_map": ctx.get("attr_map") or {}}),
        market_guidance=MARKET_GUIDANCE[lang_code], size_chart_note=note,
        section_headers='; '.join(SECTION_HEADERS[lang_code]))


def validate_copy_schema(candidate):
    """Return reason codes; never coerce malformed model fields into valid copy."""
    if not isinstance(candidate, dict):
        return ["schema:object_required"]
    issues = []
    keys = {"title", "bullet_points", "description_markdown", "search_keywords"}
    if set(candidate) != keys:
        issues.append("schema:fields")
    for key, maximum in (("title", 128), ("description_markdown", None)):
        value = candidate.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(f'schema:{key}:nonempty_string')
        elif maximum and not 1 <= len(value) <= maximum:
            issues.append(f'schema:{key}:length')
    for key, minimum, maximum, width in (("bullet_points", 5, 7, 60), ("search_keywords", 8, 12, None)):
        value = candidate.get(key)
        if not isinstance(value, list):
            issues.append(f'schema:{key}:list_required')
            continue
        if len(value) < minimum:
            issues.append(f'insufficient_facts:{key}')
        if len(value) > maximum:
            issues.append(f'schema:{key}:count')
        for item in value:
            if not isinstance(item, str) or not item.strip():
                issues.append(f'schema:{key}:item_type')
            elif width and len(item) > width:
                issues.append(f'schema:{key}:item_length')
        strings = [item.strip().casefold() for item in value if isinstance(item, str)]
        if len(set(strings)) != len(strings):
            issues.append(f'schema:{key}:duplicates')
    return list(dict.fromkeys(issues))


def _build_listing_md(parsed, lang_code, product):
    title, desc = parsed["title"], parsed["description_markdown"]
    parts = [] if desc.lstrip().startswith('# ' + title + '\n') else ['# ' + title]
    bullets = parsed["bullet_points"]
    if bullets:
        if "Key Features" in _missing_sections(desc, lang_code):
            parts.append('## ' + SECTION_HEADERS[lang_code][0])
        parts.append('\n'.join('- ' + point for point in bullets))
    parts.append(desc)
    if parsed["search_keywords"]:
        parts += ['## ' + LOCAL[lang_code]["keywords"], ', '.join(parsed["search_keywords"])]
    return '\n\n'.join(parts)


MATERIALS = {
    "cotton": r'\bcotton\b|\balgod[aã]o\b|면(?:\b|\s)|棉',
    "polyester": r'\bpolyester\b|\bpoli[eé]ster\b|폴리에스테르|涤纶|聚酯',
    "silk": r'\bsilk\b|\bseda\b|실크|真丝|蚕丝',
    "linen": r'\blinen\b|\blinho\b|리넨|린넨|亚麻',
    "wool": r'\bwool\b|\blã\b|울\b|羊毛',
    "nylon": r'\bnylon\b|\bn[aá]ilon\b|나일론|锦纶|尼龙',
    "elastane": r'\belastane\b|\bspandex\b|\belastano\b|스판|氨纶',
    "leather": r'\bleather\b|\bcouro\b|가죽|皮革',
    "viscose": r'\bviscose\b|\brayon\b|비스코스|레이온|粘胶|人造丝',
    "bamboo": r'\bbamboo\b|\bbambu\b|대나무|竹纤维',
    "acrylic": r'\bacrylic\b|\bacr[ií]lico\b|아크릴|腈纶',
    "modal": r'\bmodal\b|모달|莫代尔',
    "cashmere": r'\bcashmere\b|\bcaxemira\b|캐시미어|羊绒',
}
CLAIMS = {
    "composition": r'%|\bmaterial\b|\bfabri[ck]\b|\bfib(?:er|re)\b|\bcomposition\b|composi[çc][aã]o|tecido|소재|혼용|성분|面料|成分',
    "care": r'wash|tumble|bleach|iron(?:ing)?|dry.clean|lav(?:ar|agem)|passar|alvej|secag|세탁|표백|다림|건조|洗涤|熨烫',
    "logistics": r'shipping|delivery|customs|dispatch|free.returns|packag|parcel|weight|frete|entrega|alf[aâ]ndega|embalagem|peso|배송|관세|포장|무게|包邮|物流|包装|重量',
    "certification": r'\bCE\b|\bFDA\b|\bISO\b|certif|인증|认证',
    "performance": r'breathab|waterproof|hypoallergenic|organic|antibacter|guarantee|best.quality|respir[aá]vel|imperme[aá]vel|garantia|통기|방수|항균|최고|보장|透气|防水',
    "season": r'\bsummer\b|\bwinter\b|\bspring\b|\bautumn\b|ver[aã]o|inverno|clima|여름|겨울|春季|夏季|冬季',
    "currency": r'\$|\bUSD\b|\bKRW\b|\bBRL\b|dollars?|달러|d[oó]lares',
}
SIZE_EQUIVALENCE_RE = re.compile(r'\b(?:XS|S|M|L|XL|XXL)\s*(?:=|/|→|:|\()\s*(?:55|66|77|P|G|GG)\b', re.I)


def _norm(text):
    return re.sub(r'\s+', ' ', text).strip(' -*|').casefold()


def _checked_prose(text, product):
    """Only an exactly matching source JSON block may bypass language/claim checks."""
    issues = []
    allowed = [_raw_inventory(product), product.get("skus", []), product.get("attributes", [])]

    def strip_source(match):
        try:
            if any(_same_json(json.loads(match.group(1)), value) for value in allowed):
                return ''
        except (ValueError, TypeError):
            pass
        issues.append("facts:unverified_quoted_data")
        return match.group(1)

    prose = JSON_FENCE_RE.sub(strip_source, text)
    for lang in LOCAL:
        prose = prose.replace(_source_body(product, lang), '')
        if product.get('platform'):
            prose = prose.replace(f'{LOCAL[lang]["source_bullet"]}: {product["platform"]}', '')
    prose, _ = _mask_identifiers(prose, product)
    return prose, issues


def _language_issues(text, lang):
    issues = []
    if re.search(r'[\u4e00-\u9fff]', text) or (lang != 'ko' and re.search(r'[가-힣]', text)):
        issues.append("language:mixed_script")
    # These checks run on each field/body, not just the localized headings.
    neutral = {'sku', 'id', 'url', 'xs', 's', 'm', 'l', 'xl', 'xxl', 'xxxl', 'p', 'g', 'gg', 'cm', 'mm'}
    words = [word for word in re.findall(r"[A-Za-zÀ-ÿ]+", text.casefold()) if word not in neutral]
    en = {"the", "this", "with", "your", "product", "features", "available", "soft", "shirt", "dress", "source", "information"}
    pt = {"produto", "com", "para", "uma", "sua", "tamanho", "tecido", "vestido", "camisa", "origem", "informações", "disponível"}
    english = sum(word in en for word in words)
    portuguese = sum(word in pt for word in words)
    if lang == 'ko':
        if (words and not re.search(r'[가-힣]', text)) or english >= 2 or portuguese >= 2:
            issues.append("language:expected_ko_or_mixed")
    elif lang == 'pt' and english >= 2:
        issues.append("language:english_in_pt")
    elif lang == 'en' and portuguese >= 2:
        issues.append("language:portuguese_in_en")
    # Latin-script identification cannot be proved by stopwords alone.
    elif lang == 'pt' and len(words) >= 5 and portuguese == 0 and not re.search(r'[ãõçáéíóúâêô]', text, re.I):
        issues.append("language:pt_unverified")
    return issues


def _audit_copy(parsed, lang, product):
    issues = validate_copy_schema(parsed)
    if any(issue.startswith('schema:') for issue in issues):
        return issues
    text = _build_listing_md(parsed, lang, product)
    bodies = _section_bodies(text, lang)
    for name in SECTION_ORDER:
        if name not in bodies:
            issues.append('sections:missing:' + name)
            continue
        if len(bodies[name]) != 1:
            issues.append('sections:duplicate:' + name)
        for body in bodies[name]:
            if not re.search(r'[\w가-힣]', '\n'.join(body)):
                issues.append('sections:empty:' + name)
    source_section = '\n'.join(line for body in bodies.get('Source Information', []) for line in body)
    for key in ('platform', 'offer_id', 'url'):
        value = product.get(key)
        if value in (None, ''):
            continue
        if key == 'url':
            found = str(value) in URL_RE.findall(source_section)
        else:
            found = re.search(r'(?<![\w./?-])' + re.escape(str(value)) + r'(?![\w./?-])', source_section)
        if not found:
            issues.append('facts:source_identity_missing:' + key)
    for identifier in _identity_values(product):
        # JSON quotes/table separators are delimiters; a longer ID is not a match.
        if not re.search(r'(?<![\w./?-])' + re.escape(identifier) + r'(?![\w./?-])', text):
            issues.append('facts:source_identifier_missing')
    # Exact original SKU block is the verifiable completeness contract.
    sku_blocks = []
    for match in JSON_FENCE_RE.finditer(text):
        try:
            sku_blocks.append(json.loads(match.group(1)))
        except ValueError:
            pass
    if product.get('skus') and not any(_same_json(block, product['skus']) or _same_json(block, _raw_inventory(product)) for block in sku_blocks):
        issues.append('facts:raw_sku_integrity')
    size_section = '\n'.join(line for body in bodies.get('Size Chart', []) for line in body)
    if _source_has_measurements(product) and any(LOCAL[lang][key] in size_section for key in ('pending', 'measured')):
        issues.append('facts:measurement_relation_pending_review')
    source_urls = {url for leaf in _leaves(product) for url in URL_RE.findall(leaf)}
    if any(url not in source_urls for url in URL_RE.findall(text)):
        issues.append('facts:unknown_url')
    prose, quote_issues = _checked_prose(text, product)
    issues.extend(quote_issues)
    # Remove known localized notices; arbitrary negation is NOT an exemption.
    for notice in LOCAL[lang].values():
        prose = prose.replace(notice, '')
    issues.extend(_language_issues(prose, lang))
    fields = [parsed['title'], '\n'.join(parsed['bullet_points']), ', '.join(parsed['search_keywords'])]
    fields += ['\n'.join(body) for groups in bodies.values() for body in groups]
    for field in fields:
        field, _ = _checked_prose(field, product)
        for notice in LOCAL[lang].values():
            field = field.replace(notice, '')
        issues.extend(_language_issues(field, lang))
    evidence = '\n'.join(_evidence_texts(product))
    visible_attributes = {
        'red': r'\bred\b|vermelh[oa]|빨간|레드|红色',
        'white': r'\bwhite\b|branc[oa]|화이트|흰색|白色',
        'black': r'\bblack\b|pret[oa]|블랙|검정|黑色',
        'pink': r'\bpink\b|\brosa\b|핑크|분홍|粉色',
        'blue': r'\bblue\b|\bazul\b|블루|파란|蓝色',
        'long_sleeve': r'long[- ]sleeve|mangas? longas?|긴팔|长袖',
        'short_sleeve': r'short[- ]sleeve|mangas? curtas?|반팔|短袖',
    }
    for attribute, pattern in visible_attributes.items():
        if re.search(pattern, prose, re.I) and not re.search(pattern, evidence, re.I):
            issues.append('facts:unsupported_visible_attribute:' + attribute)
    if re.search(r'(?:images?|video|assets?).{0,45}(?:verified|delivered|ready|completed|generated)|'
                 r'(?:이미지|영상).{0,25}(?:완료|검증)|(?:imagens?|vídeo).{0,35}(?:verificad|entregue|pront)', prose, re.I):
        issues.append('facts:unverified_media_completion')
    for material, pattern in MATERIALS.items():
        if not re.search(pattern, prose, re.I):
            continue
        if not re.search(pattern, evidence, re.I):
            issues.append('facts:unsupported_material:' + material)
        elif any(re.search(pattern, line, re.I)
                 and re.search(r'\b(?:no|not|without|sem|não|nao)\b|非|不含|不是|无|아님|없음', line, re.I)
                 for line in evidence.splitlines()):
            issues.append('facts:material_evidence_pending_review:' + material)
    for line in prose.splitlines():
        if line.startswith('#'):
            # Titles/keywords are also claims, so only known section labels are skipped.
            if any(_section_name(line, code) for code in LOCAL) or line.lstrip('# ').strip() == LOCAL[lang]['keywords']:
                continue
        normalized = _norm(line.lstrip('#'))
        if not normalized:
            continue
        exact = normalized in _norm(evidence)
        for claim, pattern in CLAIMS.items():
            if re.search(pattern, line, re.I) and not exact:
                issues.append('facts:unverified_' + claim)
    if MEASURE_RE.search(prose) or any('|' in line and UNIT_RE.search(line) for line in prose.splitlines()):
        issues.append('facts:measurement_relation_pending_review' if _source_has_measurements(product)
                      else 'facts:unsupported_measurements')
    if SIZE_EQUIVALENCE_RE.search(prose):
        issues.append('facts:size_equivalence_pending_review')
    dimension = r'\b(?:bust|waist|hips?|length|chest|busto|cintura|quadril|comprimento)\b|가슴|허리|기장|胸围|腰围'
    if any(re.search(dimension, line, re.I) and (NUMBER_RE.search(line) or '|' in line or '\ufff0' in line)
           for line in prose.splitlines()):
        issues.append('facts:dimension_pending_review')
    for match in re.finditer(r'(?:\bsize\b|\btamanho\b|사이즈)\s*[:=]?\s*(XS|XXL|XL|S|M|L|P|GG|G|\d+)\b', prose, re.I):
        if match.group(1) not in _original_sizes(product):
            issues.append('facts:unsupported_size_label:' + match.group(1))
    if _sanitize_size_data(text, lang, product) != text:
        issues.append('facts:size_data_repair_required')
    # IDs do not license matching numbers in dimensions, percentages or prices.
    evidence_numbers = set(NUMBER_RE.findall(evidence))
    for number in NUMBER_RE.findall(prose):
        if number not in evidence_numbers and number not in _original_sizes(product):
            issues.append('facts:unsupported_number:' + number)
    return list(dict.fromkeys(issues))


def _fallback_copy(product, lang):
    local = LOCAL[lang]
    bullets = []
    platform = product.get('platform')
    if platform and re.fullmatch(r'[A-Za-z0-9 ._-]+', str(platform)):
        bullets.append(f'{local["source_bullet"]}: {platform}')
    for size in _original_sizes(product):
        if re.fullmatch(r'[A-Za-z0-9+ /-]{1,20}', size):
            bullets.append(f'{local["size_bullet"]}: {size}')
    bullets = [bullet for bullet in bullets if len(bullet) <= 60][:7]
    description = '\n\n'.join(f'## {header}\n{_safe_section(name, product, lang)}'
                               for name, header in zip(SECTION_ORDER, SECTION_HEADERS[lang]))
    return {"title": local['title'], "bullet_points": bullets,
            "description_markdown": description, "search_keywords": []}


def _remaining(ctx, deadline):
    remaining = max(0.0, deadline - time.monotonic())
    budget = ctx.get('budget')
    if budget is not None:
        remaining = min(remaining, max(0.0, float(budget.remaining())))
    return remaining


def _chat_bounded(chat, model, messages, timeout):
    """Bound our wait even if a transport ignores timeout/internal retries.

    Python cannot terminate an in-flight client call. The daemon owns no context
    or output files, so a late reply cannot publish or overwrite a fallback.
    """
    result = queue.Queue(maxsize=1)

    def invoke():
        try:
            result.put((chat.chat(model, messages, temperature=0.2, max_tokens=8000, timeout=timeout), None))
        except Exception as exc:
            result.put((None, exc))

    threading.Thread(target=invoke, daemon=True, name='copy-chat').start()
    try:
        value, error = result.get(timeout=timeout)
    except queue.Empty as exc:
        raise TimeoutError('copy deadline exhausted') from exc
    if error is not None:
        raise error
    return value


def _parse_candidate(content):
    # Do not extract an inner object from a malformed top-level array or prose.
    if not isinstance(content, str):
        raise ValueError('model response must be JSON text')

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON field')
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError('non-JSON numeric constant: ' + value)

    return json.loads(content, object_pairs_hook=unique_object, parse_constant=reject_constant)


def generate_copies(ctx):
    """Generate files and ctx['copy_quality']; at most two chat calls per language."""
    product = ctx.get('product') or {}
    output_dir = ctx['output_dir']
    deadline = time.monotonic() + 600.0
    if ctx.get('budget') is not None:
        deadline = time.monotonic() + min(600.0, max(0.0, float(ctx['budget'].remaining())))

    def gen_one(lang):
        prompt = build_copy_prompt(ctx, lang)
        candidate, best, best_issues, history = None, None, [], []
        attempts, model, model_fallback = 0, COPY_MODEL_PRIMARY, False
        stopped = []
        for attempt in range(2):
            remaining = _remaining(ctx, deadline)
            if remaining <= 0.05:
                stopped.append('budget:exhausted')
                break
            messages = [{'role': 'system', 'content': COPY_SYSTEM}, {'role': 'user', 'content': prompt}]
            if attempt:
                messages[-1]['content'] += '\nSTRUCTURED REPAIR REQUEST:\n' + _json({
                    'issues': history[-1]['issues'], 'action': 'Return the complete corrected JSON. Do not pad missing facts.'})
            attempts += 1
            model_fallback = model_fallback or model != COPY_MODEL_PRIMARY
            try:
                response = _chat_bounded(ctx['chat'], model, messages, remaining)
                if _remaining(ctx, deadline) <= 0:
                    raise TimeoutError('copy deadline exhausted')
                candidate = _parse_candidate(response)
                issues = _audit_copy(candidate, lang, product)
                if not any(issue.startswith('schema:') for issue in issues):
                    if best is None or len(issues) < len(best_issues):
                        best, best_issues = candidate, issues
                history.append({'attempt': attempts, 'model': model, 'issues': issues})
                if not issues:
                    break
            except TimeoutError:
                stopped.append('budget:exhausted')
                history.append({'attempt': attempts, 'model': model, 'issues': ['budget:exhausted']})
                break
            except (ValueError, TypeError) as exc:
                history.append({'attempt': attempts, 'model': model, 'issues': ['schema:invalid_json:' + type(exc).__name__]})
            except Exception as exc:
                history.append({'attempt': attempts, 'model': model, 'issues': ['generation:error:' + type(exc).__name__]})
                model = COPY_MODEL_FALLBACK
        reasons = list(best_issues) + stopped
        fallback = best is None or any(issue.startswith(('facts:', 'language:', 'sections:empty:', 'sections:duplicate:')) for issue in best_issues)
        if fallback:
            reasons.extend(issue for item in history for issue in item['issues'])
            reasons.append('fallback:source_only_template')
            best = _fallback_copy(product, lang)
        if model_fallback:
            reasons.append('fallback:model')
        text = _build_listing_md(best, lang, product)
        missing = _missing_sections(text, lang)
        if missing:
            text = _ensure_sections(text, lang, product, missing)
            reasons.extend('repair:section:' + section for section in missing)
        sanitized = _sanitize_size_data(text, lang, product)
        if sanitized != text:
            reasons.append('repair:size_data')
        # Audit final body as well; repairs must never turn a fallback into a pass.
        final_copy = dict(best, description_markdown=sanitized, bullet_points=[], search_keywords=[])
        final_issues = _audit_copy(final_copy, lang, product)
        reasons.extend(issue for issue in final_issues if not issue.startswith('insufficient_facts:'))
        reasons.extend(validate_copy_schema(best))
        reasons = list(dict.fromkeys(reasons))
        mechanical_passed = not reasons
        reasons.append('review:semantic_facts_and_native_language_pending')
        quality = {'status': 'needs_review', 'checks_status': 'passed' if mechanical_passed else 'needs_review',
                   'semantic_review': 'pending', 'reasons': reasons,
                   'model': model, 'attempts': attempts, 'fallback': fallback or model_fallback,
                   'history': history, 'language': lang,
                   'validation_scope': 'schema, section bodies, source identity/SKUs, conservative claim and language heuristics'}
        return lang, sanitized, quality

    results = {}
    quality_by_lang = ctx.setdefault('copy_quality', {})
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(gen_one, lang[0]) for lang in LANGS]
        for future in futures:
            lang, text, quality = future.result()
            dest = os.path.join(output_dir, f'product_description_{lang}.md')
            with open(dest, 'w', encoding='utf-8') as handle:
                handle.write(text)
            results[lang] = dest
            quality_by_lang[lang] = quality
            if quality['status'] != 'passed':
                ctx.setdefault('degradation_events', []).append({
                    'phase': 'copy', 'lang': lang, 'event': 'copy_needs_review', 'reasons': quality['reasons']})
            log.info('copy written: %s (%s)', dest, quality['status'])
    with open(os.path.join(output_dir, 'copy_quality.json'), 'w', encoding='utf-8') as handle:
        json.dump(quality_by_lang, handle, ensure_ascii=False, indent=2)
    return results
