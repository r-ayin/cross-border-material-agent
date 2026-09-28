# -*- coding: utf-8 -*-
"""Artifact assembly with separate technical-validity and publication gates."""
import hashlib
import json
import logging
import os
import re
import struct

from .category_map import localize_color_value
from .media_probe import inspect_video

log = logging.getLogger('agent')
EXPECTED = {
    'copies': [f'product_description_{lang}.md' for lang in ('en', 'ko', 'pt')],
    'main': ['main_image.png'],
    'details': [f'detail_image_{i}.png' for i in range(1, 6)],
    'video': ['product_video.mp4'], 'strategy': ['strategy_document.md'],
}


def _extract_english_copy_title(output_dir):
    try:
        with open(os.path.join(output_dir, 'product_description_en.md'), encoding='utf-8') as f:
            return next((line[2:].strip() for line in f if line.startswith('# ')), None)
    except (OSError, UnicodeError):
        return None


def _extract_size_letters(product):
    sizes = []
    attributes = list(product.get('attributes') or [])
    for sku in product.get('skus') or []:
        attributes.extend(sku.get('skuAttributes') or [])
    for a in attributes:
        name = str(a.get('attributeNameTrans') or a.get('attributeName') or '').lower()
        if any(word in name for word in ('尺码', '尺寸', 'size', 'saiz', 'tamanho')):
            value = str(a.get('valueTrans') or a.get('value') or '').strip()
            if value and value not in sizes:
                sizes.append(value)
    return sizes


def _build_size_chart(product):
    # A letter label is not a measurement or proof of cross-market equivalence.
    return {'provided': False, 'size_letters': _extract_size_letters(product),
            'measurements': [], 'letter_mapping': {},
            'note': '仅保留来源尺码标签；未从原文或图片核实实测值，不推断国际等码。'}


def _build_package_dimension():
    return {'length_cm': None, 'width_cm': None, 'height_cm': None,
            'weight_kg': None, 'estimated': False, 'status': 'not_provided'}


def _localize_sale_attributes(sale_attrs):
    out = []
    for sa in sale_attrs or []:
        item = dict(sa)
        name = str(sa.get('name') or sa.get('attrName') or '').lower()
        is_color = str(sa.get('attrId')) == '100000' or name in ('warna', 'color', 'colour', '颜色')
        item['values'] = [dict(v, value=localize_color_value(v.get('value')) if is_color else v.get('value'))
                          for v in sa.get('values') or [] if isinstance(v, dict)]
        out.append(item)
    return out


def read_png_size(path):
    try:
        with open(path, 'rb') as f:
            header = f.read(33)
        if len(header) == 33 and header[:8] == b'\x89PNG\r\n\x1a\n' and header[12:16] == b'IHDR':
            return struct.unpack('>II', header[16:24])
    except (OSError, struct.error):
        pass
    return None, None


def read_jpeg_size(path):
    try:
        with open(path, 'rb') as f:
            data = f.read(512 * 1024)
        if not data.startswith(b'\xff\xd8'):
            return None, None
        pos = 2
        while pos + 4 <= len(data):
            if data[pos] != 255:
                return None, None
            marker = data[pos + 1]
            if marker == 255:
                pos += 1
                continue
            if marker in (0xD9, 0xDA):
                break
            length = struct.unpack_from('>H', data, pos + 2)[0]
            if length < 2:
                break
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                height, width = struct.unpack_from('>HH', data, pos + 5)
                return width, height
            pos += 2 + length
    except (OSError, struct.error):
        pass
    return None, None


def image_dimensions(path):
    width, height = read_png_size(path)
    return (width, height) if width and height else read_jpeg_size(path)


def _find_asset(output_dir, base, exts):
    return next((f'{base}.{ext}' for ext in exts
                 if os.path.isfile(os.path.join(output_dir, f'{base}.{ext}'))), None)


def build_listing_json(ctx):
    product, output_dir = ctx['product'], ctx['output_dir']
    attr_map = ctx.get('attr_map') or {}
    title = _extract_english_copy_title(output_dir)
    listing = {
        'product': {'platform': product.get('platform'), 'offer_id': product.get('offer_id'),
                    'url': product.get('url'), 'title_source': product.get('subject'),
                    'title': title, 'title_localized': title},
        'category': ctx.get('category_info') or {},
        'product_attributes': attr_map.get('productAttributes') or [],
        'sale_attributes': _localize_sale_attributes(attr_map.get('saleAttributes') or []),
        'skus': [{'skuId': s.get('skuId'), 'stock': s.get('amountOnSale'),
                  'attributes': [{'name': a.get('attributeNameTrans') or a.get('attributeName'),
                                  'value': a.get('valueTrans') or a.get('value')}
                                 for a in s.get('skuAttributes') or []]}
                 for s in product.get('skus') or []],
        'assets': {'main_image': _find_asset(output_dir, 'main_image', ('png', 'jpeg', 'jpg')),
                   'detail_images': [_find_asset(output_dir, f'detail_image_{i}', ('png', 'jpeg', 'jpg')) for i in range(1, 6)],
                   'video': _find_asset(output_dir, 'product_video', ('mp4',))},
        'size_chart': _build_size_chart(product), 'package_dimension': _build_package_dimension(),
        'quality_report': 'quality_report.json',
    }
    path = os.path.join(output_dir, 'listing.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(listing, f, ensure_ascii=False, indent=2)
    return path


def fix_asset_extensions(output_dir):
    """Fix references only. Never recolor product pixels during assembly."""
    actual = {base: _find_asset(output_dir, base, ('png', 'jpeg', 'jpg'))
              for base in ['main_image'] + [f'detail_image_{i}' for i in range(1, 6)]}
    for filename in EXPECTED['copies']:
        path = os.path.join(output_dir, filename)
        if not os.path.isfile(path):
            continue
        with open(path, encoding='utf-8') as f:
            text = f.read()
        for base, name in actual.items():
            if name:
                text = re.sub(re.escape(base) + r'\.(?:png|jpe?g)\b', name, text, flags=re.I)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)


def inspect_outputs(output_dir, ctx=None):
    """Read-only validation. No model calls or modification of historical files."""
    from .copy_gen import _missing_sections
    from .image_gen import _inspect_image
    ctx = ctx or {}
    artifacts = []
    definitions = [(f'product_description_{lang}', 'copy', f'product_description_{lang}.md', lang)
                   for lang in ('en', 'ko', 'pt')]
    definitions += [(base, 'image', _find_asset(output_dir, base, ('png', 'jpeg', 'jpg')), None)
                    for base in ['main_image'] + [f'detail_image_{i}' for i in range(1, 6)]]
    definitions += [('product_video', 'video', 'product_video.mp4', None),
                    ('strategy_document', 'strategy', 'strategy_document.md', None)]
    for slot, kind, filename, lang in definitions:
        record = {'id': slot, 'kind': kind, 'file': filename, 'technical_valid': False,
                  'status': 'missing', 'checks': [], 'bytes': 0}
        path = os.path.join(output_dir, filename) if filename else None
        if path and os.path.isfile(path):
            size = os.path.getsize(path)
            record['bytes'] = size
            errors = []
            try:
                if kind in ('copy', 'strategy'):
                    if not 0 < size < 1_000_000:
                        raise ValueError('text must be nonempty and smaller than 1 MB')
                    with open(path, encoding='utf-8') as f:
                        text = f.read()
                    if not text.strip() or '\x00' in text:
                        errors.append('empty or binary text')
                    if kind == 'copy':
                        missing = _missing_sections(text, lang)
                        if missing:
                            errors.append('missing sections: ' + ', '.join(missing))
                        headings = re.findall(r'^# (.+)$', text, re.M)
                        if not headings or len(headings[0]) > 128:
                            errors.append('missing or oversized title')
                elif kind == 'image':
                    if size > 5_000_000:
                        errors.append('image exceeds 5 MB')
                    inspection = _inspect_image(path)
                    width, height = image_dimensions(path)
                    record.update(width=width, height=height, inspection=inspection)
                    minimum = 800 if slot == 'main_image' else 261
                    if not width or not height or min(width, height) < minimum:
                        errors.append('image dimensions below required minimum')
                else:
                    inspection = inspect_video(path)
                    record['inspection'] = inspection
                    if not inspection['valid']:
                        errors.extend(inspection['errors'])
                record['technical_valid'] = not errors
                record['status'] = 'needs_review' if not errors else 'invalid'
                record['checks'] = errors or ['local structure checks passed; semantic quality not certified']
                digest = hashlib.sha256()
                with open(path, 'rb') as f:
                    for chunk in iter(lambda: f.read(256 * 1024), b''):
                        digest.update(chunk)
                record['sha256'] = digest.hexdigest()
            except (OSError, ValueError, UnicodeError) as e:
                record['checks'] = [str(e)]
                record['status'] = 'invalid'
        if kind == 'copy':
            quality = (ctx.get('copy_quality') or {}).get(lang) or {}
        elif kind == 'image':
            quality = (ctx.get('image_quality') or {}).get(slot) or {}
        elif kind == 'video':
            quality = ctx.get('video_meta') or {}
        else:
            quality = {'status': 'accepted'} if ctx.get('strategy_generated') else {}
        record['generation_quality'] = quality
        qstatus = quality.get('status') or quality.get('artifact_status')
        if qstatus in ('failed', 'rejected', 'invalid', 'partial', 'planned_only', 'blocked_capability'):
            record['status'] = qstatus
        elif record['technical_valid'] and qstatus in ('accepted', 'passed', 'complete'):
            record['status'] = 'accepted'
        artifacts.append(record)
    technical = sum(item['technical_valid'] for item in artifacts)
    return {'schema_version': 1, 'artifacts': artifacts, 'technical_valid_count': technical,
            'required_count': 11, 'structurally_complete': technical == 11,
            'publish_ready': all(item['status'] == 'accepted' for item in artifacts),
            'official_score': None,
            'limitations': ['This local report is not the official A1–A7 evaluation.',
                            'No visual model or paid generation is called by this validator.']}


def write_quality_report(ctx):
    report = inspect_outputs(ctx['output_dir'], ctx)
    path = os.path.join(ctx['output_dir'], 'quality_report.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def validate_outputs(output_dir):
    report = inspect_outputs(output_dir)
    issues = [f"{a['id']}: {', '.join(a['checks'])}" for a in report['artifacts'] if not a['technical_valid']]
    return report['technical_valid_count'], report['required_count'], issues
