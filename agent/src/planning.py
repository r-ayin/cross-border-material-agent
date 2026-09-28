"""Pure offline creative plan. No keys, network calls or generated-asset claims."""
from urllib.parse import urlsplit, urlunsplit
import re

from .copy_gen import build_copy_prompt
from .image_gen import build_image_jobs
from .video_gen import build_shot_prompts, build_compressed_shot_prompts
from .category_map import collect_attr_table_leaves
from .creative_plan import build_film_plan


def _public_url(url):
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.hostname or '', parsed.path, '', ''))


def _safe(value):
    if isinstance(value, dict):
        return {key: _safe(item) for key, item in value.items() if key != 'source_file'}
    if isinstance(value, list):
        return [_safe(item) for item in value]
    if isinstance(value, str):
        return re.sub(r'https?://[^\s<>\"\x27]+', lambda m: _public_url(m.group()), value, flags=re.I)
    return value


def check_plan(plan):
    """Validate an exported browser/CLI plan without executing its contents."""
    errors, warnings = [], []
    if not isinstance(plan, dict):
        return {'valid': False, 'errors': ['plan must be a JSON object'], 'warnings': [], 'model_calls': 0}
    if plan.get('mode') != 'offline_plan' or plan.get('model_calls') != 0:
        errors.append('only zero-call offline plans are accepted')
    product = plan.get('product') or {}
    if not isinstance(product, dict) or not product.get('id') or not product.get('title'):
        errors.append('product id and title are required')
    slots = plan.get('slots')
    if not isinstance(slots, list):
        slots = []
        errors.append('slots must be an array')
    ids = []
    required = {f'product_description_{l}' for l in ('en', 'ko', 'pt')} | {'main_image', 'product_video', 'strategy_document'} | {f'detail_image_{i}' for i in range(1, 6)}
    for slot in slots:
        if not isinstance(slot, dict):
            errors.append('slot must be an object')
            continue
        sid = slot.get('id')
        if not isinstance(sid, str) or sid not in required:
            errors.append('unknown slot id')
            continue
        ids.append(sid)
        if not isinstance(slot.get('prompt'), str) or not slot['prompt'].strip():
            errors.append(sid + ': empty prompt')
        if slot.get('required') is not True:
            errors.append(sid + ': required must be true')
        if slot.get('kind') in ('image', 'video') and not slot.get('reference_urls'):
            warnings.append(sid + ': source references missing; generation is blocked until supplied')
    if len(ids) != len(set(ids)):
        errors.append('duplicate slot id')
    if set(ids) != required:
        warnings.append('not all 11 competition deliverables are planned')
    return {'valid': not errors, 'errors': errors, 'warnings': warnings,
            'competition_slots_complete': set(ids) == required and len(ids) == 11,
            'model_calls': 0, 'execution_authorized': False,
            'limitations': ['Structural preflight only; facts, model capabilities and content quality are not verified.']}


def build_plan(data, ctx):
    ctx = dict(ctx, product=_safe(ctx['product']))
    product = ctx['product']
    slots = [{'id': f'product_description_{lang}', 'kind': 'copy', 'language': lang,
              'required': True, 'prompt': build_copy_prompt(ctx, lang),
              'acceptance': ['source facts preserved', 'correct language', 'six sections', 'no invented measurements']}
             for lang in ('en', 'ko', 'pt')]
    for job in build_image_jobs(ctx):
        slots.append({'id': job['name'], 'kind': 'image', 'role': job['role'], 'required': True,
                      'prompt': job['prompt'], 'negative_prompt': job['negative_prompt'],
                      'reference_urls': [_public_url(u) for u in job['ref']],
                      'reference_note': '展示URL省略签名；运行时须从原始商品文件读取完整URL。',
                      'size': job['size'], 'acceptance': ['source fidelity', 'role coverage', 'no watermark/text', 'valid media'],
                      'planned_models': job['chain']})
    slots.append({'id': 'product_video', 'kind': 'video', 'required': True,
                  'prompt': 'Reference-driven complete product showcase. Use only verified model capabilities; do not substitute one shot for the full requested film.',
                  'storyboard_30s': build_shot_prompts(product),
                  'storyboard_15s': build_compressed_shot_prompts(product),
                  'film_blueprint': build_film_plan(product, seconds=30, profile=ctx.get('film_profile', 'studio'),
                                                    frames=ctx.get('frame_catalog'), capabilities=ctx.get('film_capabilities')),
                  'capability_status': 'requires explicit verified capabilities and approved keyframes',
                  'acceptance': ['playback', 'actual duration', 'product consistency', 'full agreed storyboard', 'no watermark'],
                  'note': '15/30秒为创作方案，不是赛规最低时长；字幕/音轨/配乐须分别验收。'})
    slots.append({'id': 'strategy_document', 'kind': 'strategy', 'required': True,
                  'prompt': '由实际运行记录生成策略说明；区分配置候选和实际调用、计划和交付、未知和通过。',
                  'generation': 'deterministic_stdlib', 'model_calls': 0})
    source_name = str(product.get('category_name') or '').strip()
    candidates = [leaf for leaf in collect_attr_table_leaves(data.get('attributes'))
                  if source_name and source_name in str(leaf.get('nameChinese') or leaf.get('categoryName') or '')]
    return _safe({'schema_version': 1, 'mode': 'offline_plan', 'model_calls': 0,
            'product': {'id': product.get('offer_id'), 'title': product.get('subject'),
                        'source_platform': product.get('platform'), 'source_url': product.get('url'),
                        'sku_count': len(product.get('skus') or []),
                        'source_image_count': len(product.get('images') or [])},
            'category_candidates': [{'id': v['categoryId'], 'name': v.get('nameChinese') or v.get('categoryName'),
                                     'status': 'lexical_candidate_not_semantic_verification'} for v in candidates],
            'style': ctx.get('style_profile', {}).get('style_name'),
            'slots': slots, 'checks': [
                {'id': 'slot_count', 'passed': len(slots) == 11, 'detail': '3文案+6图片+1视频+1策略'},
                {'id': 'references', 'passed': bool(product.get('images')), 'detail': '原始商品URL锁定，尚未读取图像'},
                {'id': 'sku_data', 'passed': bool(product.get('skus')), 'detail': '保留来源SKU，不猜尺码'},
                {'id': 'generation', 'passed': False, 'detail': '计划不是生成产物；零调用'}],
            'next_steps': ['核实低价服务协议和价格', '少量参考图生图与视频样片', '按同一验收表比较',
                           '冻结能力配置与提示词', '授权后仅执行一次千问正式生成'],
            'limitations': ['官方67分细项回执未提供，不能推算新分数。',
                            '图片与视频真实效果必须通过样片检验。',
                            '第三方低价接口仅用于独立研发测试，不进入赛内白名单执行路径。']})
