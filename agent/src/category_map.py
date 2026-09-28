# -*- coding: utf-8 -*-
"""Category and attribute mapping: source product -> AliExpress leaf category + attributes."""
import json
import logging
import re

from .dsapi import ChatClient, extract_json_block

log = logging.getLogger("agent")

MODEL_CAT = "qwen3.7-max"
MODEL_ATTR = "qwen3.7-max"

# Built-in color word dictionary for sale-attribute (Warna) localization.
COLOR_LOCALIZE = {
    "粉": "Pink",
    "黑": "Black",
    "白": "White",
    "红": "Red",
    "蓝": "Blue",
    "绿": "Green",
    "灰": "Gray",
    "紫": "Purple",
}


def localize_color_value(value):
    """Map Chinese color words inside a sale-attribute value to English.

    Only the color part is translated (e.g. 粉色半身裙 -> Pink); values that
    contain no known color word are returned unchanged.
    """
    if not value or not isinstance(value, str):
        return (value if value else "") or ""
    hits = [COLOR_LOCALIZE[c] for c in value if c in COLOR_LOCALIZE]
    if not hits:
        return value
    seen, out = [], []
    for w in hits:
        if w not in seen:
            seen.append(w)
            out.append(w)
    return " ".join(out)


def collect_attr_table_leaves(attributes):
    """66 leaves with attribute definitions: [{cid, categoryId, categoryName, path, categoryPath}]."""
    out = []
    for it in (attributes.get("categories") if isinstance(attributes, dict) else None) or []:
        leaf = {
            "categoryId": it.get("categoryId"),
            "categoryName": it.get("categoryName") or "",
            "nameChinese": it.get("nameChinese") or "",
            "categoryPath": it.get("categoryPath") or "",
            "path": it.get("path") or [],
            "categoryMetadata": it.get("categoryMetadata") or {},
        }
        out.append(leaf)
    return out


def collect_tree_leaves(categories, limit=4000):
    """All tree leaves (catId, name, categoryPath). Capped to avoid context overflow."""
    out = []

    def walk(nodes):
        for n in nodes or []:
            if n.get("isLeaf"):
                out.append((n.get("catId"), n.get("name"), n.get("categoryPath") or ""))
            else:
                walk(n.get("children"))

    roots = categories.get("categories") if isinstance(categories, dict) else None
    walk(roots)
    return out[:limit]


def map_category(chat, product, attr_leaves, tree_leaves):
    """Select the best AliExpress leaf category for the source product."""
    subject = product.get("subject") or ""
    src_cat = product.get("category_name") or ""
    src_attrs = [a.get("attributeNameTrans") or a.get("attributeName") or "" for a in product.get("attributes") or []]

    # candidate list: attribute-table leaves (with attr defs) + tree leaves
    candidate_lines = []
    seen = set()
    for leaf in attr_leaves:
        key = str(leaf.get("categoryId"))
        if key in seen:
            continue
        seen.add(key)
        candidate_lines.append(f"- categoryId={leaf.get('categoryId')}, name={leaf.get('nameChinese') or leaf.get('categoryName')}, path={leaf.get('categoryPath')}")

    sys_prompt = "你是跨境电商类目映射专家。根据源商品的标题、源类目和属性，从候选 AliExpress 叶子类目中选择最匹配的一个。只返回 JSON。"
    user_prompt = (
        "源商品标题: " + subject + "\n"
        "源平台类目: " + src_cat + "\n"
        "源属性: " + ", ".join(src_attrs) + "\n\n"
        "候选叶子类目（带属性定义）:\n" + "\n".join(candidate_lines) + "\n\n"
        "请选择最匹配的叶子类目。返回 JSON：{\"categoryId\": 数字, \"categoryName\": \"中文名\", \"categoryPath\": \"完整路径\", \"reason\": \"一句话理由\"}。"
    )

    content = chat.chat(MODEL_CAT, [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ], temperature=0.2, max_tokens=1200)
    parsed = extract_json_block(content)
    if not isinstance(parsed, dict):
        raise ValueError('category response must be an object')
    selected = find_attr_leaf(parsed.get('categoryId'), attr_leaves)
    if selected is None:
        raise ValueError('selected category is not in the supplied leaf library')
    # Names and paths come from the library, not a model-generated substitute.
    return {'categoryId': selected['categoryId'],
            'categoryName': selected.get('nameChinese') or selected.get('categoryName'),
            'categoryPath': selected.get('categoryPath'),
            'reason': str(parsed.get('reason') or ''),
            'validation': 'library_member'}, attr_leaves


def find_attr_leaf(category_id, attr_leaves):
    cid = str(category_id)
    for leaf in attr_leaves:
        if str(leaf.get("categoryId")) == cid:
            return leaf
    return None


def _map_attributes_legacy(chat, product, leaf, budget):
    """Legacy per-call mapping (fallback when the batch mapping fails)."""
    cm = (leaf or {}).get("categoryMetadata") or {}
    sale_attrs = cm.get("categorySaleAttrList") or []
    prod_attrs = cm.get("categoryProductAttrList") or []

    # compress attr defs to fit context: name + enum values
    def compact_prod(attrs_list, cap=60):
        items = []
        for a in attrs_list[:cap]:
            vals = []
            for v in (a.get("values") or [])[:25]:
                vals.append({"id": v.get("id"), "name": v.get("name"), "alias": v.get("valueNameAlias")})
            items.append({
                "attrId": a.get("attrId"),
                "name": a.get("name"),
                "alias": a.get("attributeNameAlias"),
                "values": vals,
            })
        return items

    def compact_sale(attrs_list):
        items = []
        for a in attrs_list:
            vals = []
            for v in (a.get("values") or [])[:30]:
                vals.append({"id": v.get("id"), "name": v.get("name"), "alias": v.get("valueNameAlias")})
            items.append({
                "attrId": a.get("attrId"),
                "name": a.get("name"),
                "alias": a.get("attributeNameAlias"),
                "values": vals,
            })
        return items

    src_attrs = product.get("attributes") or []
    src_skus = product.get("skus") or []

    sys_prompt = ("你是跨境电商属性映射专家。把源商品的中文属性和SKU映射到目标类目属性体系的枚举值。"
                  "严格忠于源数据：源数据没有的属性（如品牌、认证）绝不虚构，宁可留空。只返回JSON。")
    user_prompt = (
        "目标叶子类目: " + (leaf or {}).get("nameChinese", "") + "\n\n"
        "目标产品属性定义（含枚举值）:\n" + json.dumps(compact_prod(prod_attrs), ensure_ascii=False) + "\n\n"
        "目标销售属性定义（含枚举值）:\n" + json.dumps(compact_sale(sale_attrs), ensure_ascii=False) + "\n\n"
        "源产品属性:\n" + json.dumps(src_attrs[:20], ensure_ascii=False) + "\n\n"
        "源SKU销售属性:\n" + json.dumps(src_skus[:10], ensure_ascii=False)[:3000] + "\n\n"
        "请映射。返回JSON：{\n"
        "  \"productAttributes\": [{\"attrId\":\"\",\"name\":\"\",\"valueId\":\"\",\"valueName\":\"\"}],\n"
        "  \"saleAttributes\": [{\"attrId\":\"\",\"name\":\"\",\"values\": [{\"skuId\":\",\"value\":\"\"}]}],\n"
        "  \"unmatched\": [\"未能映射的源属性名\"]\n"
        "}"
    )

    content = chat.chat(MODEL_ATTR, [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ], temperature=0.2, max_tokens=4000)
    parsed = extract_json_block(content) or {}
    log.info("attribute mapping: %d product attrs, %d sale attrs",
             len(parsed.get("productAttributes") or []), len(parsed.get("saleAttributes") or []))
    return parsed


def _enum_index(leaf):
    """attrId -> {attr, customized, values:{id:value}} for strict validation."""
    cm = (leaf or {}).get("categoryMetadata") or {}
    idx = {"prod": {}, "sale": {}}
    for bucket, raw in (("prod", cm.get("categoryProductAttrList") or []),
                        ("sale", cm.get("categorySaleAttrList") or [])):
        for a in raw:
            attr_id = str(a.get("attrId"))
            values = {}
            for v in (a.get("values") or []):
                if v.get("id") is not None:
                    values[str(v.get("id"))] = v
            idx[bucket][attr_id] = {
                "attr": a,
                # strict enum validation applies whenever the library provides
                # values; free text is only accepted for attrs with no enum at all
                "customized": not values,
                "values": values,
            }
    return idx


def _attr_display_name(attr):
    return attr.get("name") or attr.get("attributeNameAlias") or ""


def _value_display_name(v):
    return v.get("name") or v.get("valueNameAlias") or ""


def _is_color_sale_attr(attr_id, name, alias):
    return (str(attr_id) == "100000"
            or str(name or "").strip().lower() in ("warna", "color", "colour", "颜色")
            or str(alias or "").strip() == "颜色")


def _validate_product_entries(entries, idx):
    """Strict enum validation: attrId/valueId must exist in the attribute library.

    Entries whose attrId belongs to the sale bucket are skipped here (they are
    collected by the caller and routed to the sale bucket). Returns deduped
    [{attrId, valueId, attrName, valueName}].
    """
    pool = idx["prod"]
    out, seen = [], set()
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        attr_id = str(e.get("attrId") or "").strip()
        val_id = str(e.get("valueId") or "").strip()
        attr_name = e.get("attrName") or e.get("name") or ""
        val_name = str(e.get("valueName") or e.get("value") or "").strip()
        if attr_id not in pool:
            if attr_id in idx["sale"]:
                continue
            resolved = _resolve_attr_id_by_name(attr_name, idx)
            if resolved is None:
                log.info("attr mapping dropped (unknown attrId %s)", attr_id)
                continue
            attr_id = resolved
        ad = pool[attr_id]
        if not ad["customized"]:
            v = ad["values"].get(val_id)
            if v is None and val_name:
                for vid, vv in ad["values"].items():
                    if (_alias_pair_match(val_name, str(vv.get("name") or ""))
                            or _alias_pair_match(val_name, str(vv.get("valueNameAlias") or ""))):
                        v, val_id = vv, vid
                        break
            if v is None:
                log.info("attr mapping dropped (invalid valueId %s for attr %s)", val_id, attr_id)
                continue
            val_name = _value_display_name(v)
        else:
            val_id = ""
            if not val_name:
                continue
        attr_name = attr_name or _attr_display_name(ad["attr"])
        key = (attr_id, val_id or val_name)
        if key in seen:
            continue
        seen.add(key)
        out.append({"attrId": attr_id, "valueId": val_id,
                    "attrName": str(attr_name), "valueName": str(val_name)})
    return out


def _validate_sale_entries(entries, idx):
    """Validate sale mappings; group into [{attrId, attrName, values:[{skuId,value}]}].

    attrIds must exist in the library. Free-text (customized) values are kept
    as-is; Warna (color) values are localized to English.
    """
    pool = idx["sale"]
    groups = {}

    def add(attr_id, sku_id, value):
        if not isinstance(value, str) or not value.strip():
            return
        definition = pool[attr_id]
        attr = definition['attr']
        if _is_color_sale_attr(attr_id, attr.get('name'), attr.get('attributeNameAlias')):
            value = localize_color_value(value)
        if definition['values']:
            allowed = {str(v.get(key) or '').strip().casefold()
                       for v in definition['values'].values() for key in ('name', 'valueNameAlias')}
            if value.strip().casefold() not in allowed:
                return
        g = groups.setdefault(attr_id, {"attrId": attr_id, "attrName": "", "values": []})
        if not g["attrName"]:
            g["attrName"] = _attr_display_name(attr)
        for item in g["values"]:
            if str(item.get('skuId')) == str(sku_id) and item.get('value') == value:
                return
        g["values"].append({"skuId": sku_id if sku_id is not None else "", "value": value})

    for e in entries or []:
        if not isinstance(e, dict):
            continue
        attr_id = str(e.get("attrId") or "").strip()
        if attr_id not in pool:
            continue
        if isinstance(e.get("values"), list):
            g = groups.setdefault(attr_id, {"attrId": attr_id,
                                            "attrName": e.get("name") or e.get("attrName") or "",
                                            "values": []})
            if not g["attrName"]:
                g["attrName"] = _attr_display_name(pool[attr_id]["attr"])
            for item in e["values"]:
                if isinstance(item, dict):
                    add(attr_id, item.get("skuId"), item.get("value") or item.get("valueName"))
        else:
            add(attr_id, e.get("skuId"), e.get("valueName") or e.get("value"))
    return [groups[k] for k in sorted(groups)]


def _batch_attr_user_prompt(product, leaf):
    """One prompt mapping ALL source attributes against the COMPLETE target enum list."""
    cm = (leaf or {}).get("categoryMetadata") or {}

    def compact(attrs):
        items = []
        for a in attrs:
            vals = []
            for v in (a.get("values") or []):
                vals.append({"id": v.get("id"), "name": v.get("name"),
                             "alias": v.get("valueNameAlias")})
            items.append({"attrId": a.get("attrId"), "name": a.get("name"),
                          "alias": a.get("attributeNameAlias"),
                          "isCustomized": bool(a.get("isCustomized")), "values": vals})
        return items

    sku_lines = []
    for s in (product.get("skus") or [])[:30]:
        sku_lines.append({"skuId": s.get("skuId"), "skuAttributes": s.get("skuAttributes")})
    prod_def = json.dumps(compact(cm.get("categoryProductAttrList") or []), ensure_ascii=False)
    sale_def = json.dumps(compact(cm.get("categorySaleAttrList") or []), ensure_ascii=False)
    src_attrs = json.dumps(product.get("attributes") or [], ensure_ascii=False)
    sku_block = json.dumps(sku_lines, ensure_ascii=False)[:4000]
    return (
        "目标叶子类目: " + str((leaf or {}).get("nameChinese") or "")
        + " (categoryId=" + str((leaf or {}).get("categoryId")) + ")\n\n"
        + "目标产品属性定义（完整枚举，严格从中选择 attrId/valueId/valueName）:\n"
        + prod_def + "\n\n"
        + "目标销售属性定义（isCustomized=true 表示自由填写、无枚举）:\n"
        + sale_def + "\n\n"
        + "源商品全部属性 (key+value):\n"
        + src_attrs + "\n\n"
        + "源SKU销售属性（尺码/颜色分布）:\n"
        + sku_block + "\n\n"
        + "请把源属性映射到目标类目枚举，返回 JSON（不要其他文字）：\n"
        + '{\n  "productAttributes": [{"attrId": "..", "valueId": "..", "attrName": "..", "valueName": ".."}],\n'
        + '  "saleAttributes": [{"attrId": "..", "attrName": "..", "values": [{"skuId": "..", "value": ".."}]}],\n'
        + '  "unmatched": ["未能映射的源属性名"]\n}\n'
        + "约束：attrId/valueId 必须真实存在于上面的目标属性定义；valueName 用枚举里的 name 或 alias；\n"
        + "源数据没有的属性绝不虚构；尺码/颜色等销售属性放入 saleAttributes（attrId 为销售属性 id）。"
    )

def _batch_map_attributes(chat, product, leaf):
    """One batch LLM call (qwen3.7-max) over all source attributes; strict-validated."""
    sys_prompt = ("你是跨境电商属性映射专家。把源商品的全部中文属性映射到目标类目属性体系的枚举值。"
                  "严格忠于源数据：源数据没有的属性绝不虚构；attrId/valueId 必须真实存在于给定的目标属性定义中。"
                  "只返回 JSON。")
    content = chat.chat(MODEL_ATTR, [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": _batch_attr_user_prompt(product, leaf)},
    ], temperature=0.2, max_tokens=8000)
    parsed = extract_json_block(content)
    if not parsed:
        raise ValueError("batch attribute mapping returned no JSON")
    if isinstance(parsed, list):
        parsed = {"productAttributes": parsed, "saleAttributes": [], "unmatched": []}
    idx = _enum_index(leaf)
    sale_ids = set(idx["sale"])
    product_entries = [e for e in (parsed.get("productAttributes") or [])
                       if isinstance(e, dict) and str(e.get("attrId") or "").strip() not in sale_ids]
    extra_sale = [e for e in (parsed.get("productAttributes") or [])
                  if isinstance(e, dict) and str(e.get("attrId") or "").strip() in sale_ids]
    prod = _validate_product_entries(product_entries, idx)
    sale = _validate_sale_entries((parsed.get("saleAttributes") or []) + extra_sale, idx)
    if not prod and not sale:
        raise ValueError("batch attribute mapping produced nothing valid")
    return {
        "productAttributes": prod,
        "saleAttributes": sale,
        "unmatched": parsed.get("unmatched") or [],
        "batch": True,
    }


ATTR_SYNONYMS = {"面料名称": "材质", "主面料成分2": "材质", "场景": "场合", "风格类型": "风格"}


def _norm_cn(text):
    t = (text or "").strip()
    for sep in ("(", "（"):
        t = t.split(sep)[0]
    for tail in ("面料", "材质", "纤维"):
        if t.endswith(tail) and len(t) > len(tail):
            t = t[: -len(tail)]
    return t.strip()


def _alias_pair_match(src_text, alias_text):
    s = _norm_cn(src_text)
    a = _norm_cn(alias_text)
    if not s or not a:
        return False
    if s == a:
        return True
    return s in a or a in s


def _resolve_attr_id_by_name(attr_name, idx):
    n = _norm_cn(ATTR_SYNONYMS.get(str(attr_name or "").strip(),
                                   str(attr_name or "").strip()))
    if not n:
        return None
    for aid, ad in idx["prod"].items():
        a = ad["attr"]
        for c in (str(a.get("name") or ""), str(a.get("attributeNameAlias") or "")):
            cn = _norm_cn(c)
            if cn and (cn == n or cn in n or n in cn):
                return aid
    return None


def _deterministic_alias_map(product, leaf):
    """Zero-LLM first pass: exact Chinese-alias matching (high precision).

    The attribute library ships Chinese aliases (attributeNameAlias /
    valueNameAlias). Source attribute names/values are matched against those
    aliases verbatim or by containment, so this pass never hallucinates and
    guarantees a coverage floor even when the LLM batch call fails.
    """
    cm = (leaf or {}).get("categoryMetadata") or {}
    src = product.get("attributes") or []

    def sname(x):
        return str(x.get("attributeName") or x.get("name") or "").strip()

    def sval(x):
        return str(x.get("attributeValue") or x.get("value") or "").strip()

    prod, seen = [], set()
    for attr in cm.get("categoryProductAttrList") or []:
        aalias = str(attr.get("attributeNameAlias") or "").strip()
        if not aalias:
            continue
        attr_id = str(attr.get("attrId"))
        for s in src:
            sn = ATTR_SYNONYMS.get(sname(s).strip(), sname(s))
            if not _alias_pair_match(sn, aalias):
                continue
            v = sval(s)
            if not v:
                continue
            for vv in attr.get("values") or []:
                vid = vv.get("id")
                if vid is None:
                    continue
                if (_alias_pair_match(v, str(vv.get("valueNameAlias") or ""))
                        or v == str(vv.get("name") or "")):
                    key = (attr_id, str(vid))
                    if key not in seen:
                        seen.add(key)
                        prod.append({"attrId": attr_id, "valueId": str(vid),
                                     "attrName": attr.get("name") or aalias,
                                     "valueName": vv.get("name") or vv.get("valueNameAlias")})
                    break
    return prod


def _merge_product_attrs(base_entries, extra_entries):
    have = {str(e.get("attrId")) for e in base_entries or []}
    merged = list(base_entries or [])
    for e in extra_entries or []:
        aid = str(e.get("attrId"))
        if aid and aid not in have:
            merged.append(e)
            have.add(aid)
    return merged


def map_attributes(chat, product, leaf, budget):
    """Map ALL source product attributes to the mapped leaf category's system.

    Pass 1 (deterministic): exact Chinese-alias matching, zero LLM, strict
    validated. Pass 2: one batch LLM call over the complete enum list (or the
    legacy per-call mapping when the batch fails) fills the remainder.
    Deterministic entries win on attrId conflicts. Sale-attribute color values
    are localized to English by the validation path.
    """
    if not leaf:
        return {}
    det_prod = _validate_product_entries(
        _deterministic_alias_map(product, leaf), _enum_index(leaf))
    log.info("attribute mapping (deterministic alias): %d product attrs", len(det_prod))
    rest = None
    try:
        result = _batch_map_attributes(chat, product, leaf)
        if result is not None:
            rest = result
            log.info("attribute mapping (batch): %d product attrs, %d sale attrs",
                     len(result.get("productAttributes") or []),
                     len(result.get("saleAttributes") or []))
    except Exception as e:
        log.warning("batch attribute mapping failed (%s), falling back to legacy", str(e)[:200])
    if rest is None:
        legacy = _map_attributes_legacy(chat, product, leaf, budget)
        rest = _normalize_legacy(legacy, leaf)
        log.info("attribute mapping (legacy): %d product attrs, %d sale attrs",
                 len(rest.get("productAttributes") or []),
                 len(rest.get("saleAttributes") or []))
    merged = dict(rest)
    merged["productAttributes"] = _merge_product_attrs(
        det_prod, rest.get("productAttributes"))
    log.info("attribute mapping (merged): %d product attrs, %d sale attrs",
             len(merged.get("productAttributes") or []),
             len(merged.get("saleAttributes") or []))
    return merged


def _normalize_legacy(result, leaf):
    """Normalize + strict-validate the legacy mapping output into the same shapes."""
    if not isinstance(result, dict):
        return {}
    idx = _enum_index(leaf)
    prod = _validate_product_entries(result.get("productAttributes") or [], idx)
    sale = _validate_sale_entries(result.get("saleAttributes") or [], idx)
    return {
        "productAttributes": prod,
        "saleAttributes": sale,
        "unmatched": result.get("unmatched") or [],
        "batch": False,
    }
