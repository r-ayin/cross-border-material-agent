# -*- coding: utf-8 -*-
"""Deterministic strategy document: observations, not another model's guesses."""
import json
import logging
import os

from .runtime_policy import policy, redact

log = logging.getLogger('agent')

# Configuration inventory is not proof of models used in a particular run.
COMPONENT_INVENTORY = [
    {'role': 'text primary', 'model': 'qwen3.8-max'},
    {'role': 'category / text fallback', 'model': 'qwen3.7-max'},
    {'role': 'visual review', 'model': 'qwen-vl-max'},
    {'role': 'image candidates', 'model': 'qwen-image-3.0-pro / wan2.7-image-pro / wan2.7-image'},
    {'role': 'video candidates', 'model': 'wan2.7-i2v / happyhorse-1.1-r2v / happyhorse-1.1-t2v'},
]


def generate_strategy(ctx):
    product = ctx['product']
    budget = ctx['budget']
    images = ctx.get('image_quality') or {}
    copies = ctx.get('copy_quality') or {}
    video = ctx.get('video_meta') or {}
    observed_models = sorted({str(v.get('model')) for v in list(images.values()) + list(copies.values()) + [video]
                              if isinstance(v, dict) and v.get('model')})
    summary = {
        'source_product_id': product.get('offer_id'),
        'source_platform': product.get('platform'),
        'source_url': product.get('url'),
        'target_category': ctx.get('category_info') or {},
        'attribute_mapping': ctx.get('attr_map') or {},
        'style': (ctx.get('style_profile') or {}).get('style_name'),
        'reference_policy': 'original source URLs are authoritative; no invented multi-view anchor',
        'observed_media_and_copy_models': observed_models,
        'copy_quality': copies,
        'image_quality': images,
        'video_delivery': video,
        'degradation_events': ctx.get('degradation_events') or [],
        'elapsed_seconds': round(budget.elapsed(), 2),
        'remaining_seconds': round(budget.remaining(), 2),
        'request_accounting': policy().snapshot(),
    }
    content = (
        '# 一键出海：本次运行策略与验收记录\n\n'
        '## English Abstract\n'
        'A standard-library Python pipeline prepares three localized listings, six '
        'role-specific images and one product video. File existence, technical validity '
        'and publishable quality are separate states. Unknown checks remain unverified.\n\n'
        '## 事实与本地化\n'
        '商品源数据是事实边界。英、美式英语；韩、韩国韩语；葡、巴西葡语。'
        '保留真实SKU与来源，不虚构成分、尺寸、价格、洗护和物流承诺。'
        '没有实测数据时标记缺失，不把市场尺码习惯当作等码证明。\n\n'
        '## 图像职责与产品保真\n'
        '交付主图、卖点整体图、工艺特写、材质特写、生活场景、完整全景六个不同槽位。'
        '主图要求完整主体与白底；生活场景不套用主图的白底限制。'
        '来源URL始终是权威参照，生成图不能反过来证明原商品的结构。'
        '已知违规候选不作为合格交付；视觉检查不可用则明确待复核。\n\n'
        '## 视频完成度\n'
        '优先单次参考图驱动的完整视频，禁止把单个分镜冒充整片。'
        '目标时长不是实测时长；容器、视频轨道、实际尺寸和时长由本地解析核验。'
        '字幕旁挂文件不等于字幕已烧录，配乐指令不等于已生成或混音。'
        '分镜覆盖、动态形变、水印、音画质量仍需要真实生成与观看验收。\n\n'
        '## 预算与调用纪律\n'
        '先离线预检，再用已核实接口的小样测试，最后在授权后生成正式产物。'
        '默认禁网；配置密钥本身不会触发调用。请求共享截止时间、总次数和媒体次数上限。'
        '任务已受理后的轮询失败不会自动新建任务；避免未知状态重复计费。\n\n'
        '## 本次可观察证据\n'
        '以下仅记录实际收集到的状态；记录为空代表未知，不代表没有发生降级。\n\n'
        '```json\n' + redact(json.dumps(summary, ensure_ascii=False, indent=2)) + '\n```\n\n'
        '## 配置候选（不代表全部调用过）\n'
        '```json\n' + json.dumps(COMPONENT_INVENTORY, ensure_ascii=False, indent=2) + '\n```\n\n'
        '## 完成标准\n'
        '11个必需文件通过技术检查只是结构完成。发布就绪还需要三语事实复核、'
        '六图职责与保真检查、视频完整性和无水印检查；详见 quality_report.json。'
        '本文件由代码根据运行记录组装，没有额外调用文本模型。\n'
    )
    dest = os.path.join(ctx['output_dir'], 'strategy_document.md')
    with open(dest, 'w', encoding='utf-8') as f:
        f.write(content)
    log.info('strategy written from observed evidence (no additional model call)')
    return dest
