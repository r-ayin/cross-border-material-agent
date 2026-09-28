#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-click global: offline planning first, explicitly authorized generation second."""
import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from src.budget import Budget, setup_logging
from src.dsapi import ChatClient, OpenAIImageClient, TaskClient, get_env
from src.runtime_policy import HardDeadline, PolicyError, configure_runtime, policy, redact
from src.input_parse import load_input
from src.category_map import collect_attr_table_leaves, collect_tree_leaves, find_attr_leaf, map_attributes, map_category
from src.copy_gen import generate_copies
from src.image_gen import generate_images
from src.video_gen import generate_video
from src.strategy import generate_strategy
from src.assemble import build_listing_json, fix_asset_extensions, write_quality_report, inspect_outputs
from src.style_router import analyze_product, global_image_profile

log = logging.getLogger('agent')
AGENT_JSON = os.path.join(HERE, 'agent.json')
VISION_MODEL = 'qwen-vl-max'


def read_version():
    with open(AGENT_JSON, encoding='utf-8') as f:
        return json.load(f).get('version', '0.0.0')


def decide_mode(prompt, budget):
    return 'simple' if any(t in (prompt or '').lower() for t in ('简版', '简单模式', 'simple mode')) else 'professional'


def describe_product_vision(chat, product):
    images = (product.get('images') or [])[:2]
    if not images:
        return ''
    content = [{'type': 'image_url', 'image_url': {'url': u}} for u in images]
    content.append({'type': 'text', 'text':
                    'Describe only visible product geometry, color, pattern and composition in at most 60 English words. '
                    'Do not infer fiber composition, measurements, elasticity, quality or hidden construction. '
                    'This is an unverified visual observation, not a replacement for source facts.'})
    try:
        return chat.chat(VISION_MODEL, [{'role': 'user', 'content': content}],
                         temperature=0.1, max_tokens=300, timeout=(15, 60))
    except Exception as e:
        log.warning('visual observations unavailable: %s', redact(e))
        return ''


def _write_json(path, value):
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
    os.replace(path + '.tmp', path)


def run_pipeline(prompt, plan_only=False):
    if plan_only:
        return _run_pipeline(prompt, plan_only=True)
    with HardDeadline():
        return _run_pipeline(prompt, plan_only=False)


def _run_pipeline(prompt, plan_only=False):
    setup_logging()
    budget = Budget()
    configure_runtime(deadline=budget.start + budget.total - 45)
    data = load_input(prompt)
    product, output_dir = data['product'], data['output_dir']
    mode = decide_mode(prompt, budget)
    signals = analyze_product(product)
    ctx = {'product': product, 'output_dir': output_dir, 'budget': budget,
           'mode': mode, 'style_signals': signals,
           'style_profile': global_image_profile(product, mode, signals=signals)}
    if plan_only:
        from src.planning import build_plan
        plan = build_plan(data, ctx)
        _write_json(os.path.join(output_dir, 'generation_plan.json'), plan)
        print(f"offline plan: {len(plan['slots'])} required slots; model calls=0")
        return 0

    if os.environ.get('AGENT_ALLOW_PAID_CALLS') != '1':
        raise PolicyError('当前默认禁网，请使用 --plan-only；真实生成须另行授权 AGENT_ALLOW_PAID_CALLS=1')
    existing = [name for name in os.listdir(output_dir)
                if name.startswith(('main_image.', 'detail_image_', 'product_description_', 'product_video.', 'run_manifest.'))]
    if existing:
        raise ValueError('output directory contains previous artifacts; choose a new run directory to prevent stale success')
    api_key, dash_base, openai_base = get_env()
    if not all((api_key, dash_base, openai_base)):
        raise ValueError('DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL and OPENAI_BASE_URL are all required')
    chat, task_client = ChatClient(api_key, openai_base), TaskClient(api_key, dash_base)
    ctx.update(chat=chat, task_client=task_client, openai_image=OpenAIImageClient(api_key, openai_base))
    events = []

    def event(stage, status, **details):
        events.append({'stage': stage, 'status': status, 'elapsed_seconds': round(budget.elapsed(), 3), **details})
        _write_json(os.path.join(output_dir, 'run_manifest.json'),
                    {'product_id': product.get('offer_id'), 'mode': 'authorized_generation',
                     'events': events, 'requests': policy().snapshot()})

    event('input', 'complete')
    ctx['vision_brief'] = describe_product_vision(chat, product) if budget.enough(150) else ''
    leaves = collect_attr_table_leaves(data['attributes']) if data['attributes'] else []
    tree = collect_tree_leaves(data['categories']) if data['categories'] else []
    ctx['category_info'], leaves = map_category(chat, product, leaves, tree)
    leaf = find_attr_leaf(ctx['category_info'].get('categoryId'), leaves)
    ctx['attr_map'] = map_attributes(chat, product, leaf, budget) if leaf else {}
    event('mapping', 'complete', category_id=ctx['category_info'].get('categoryId'))

    # All media use authoritative source images. Video need not wait for a costly
    # generated anchor; the 3 image workers remain bounded inside generate_images.
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(fn, ctx): name for name, fn in
                (('copies', generate_copies), ('images', generate_images), ('video', generate_video))}
        for future in as_completed(jobs):
            name = jobs[future]
            try:
                result = future.result()
                if name == 'video':
                    ctx['video_meta'] = result or {}
                event(name, 'returned', note='returned does not mean quality accepted')
            except Exception as e:
                ctx.setdefault('degradation_events', []).append({'phase': name, 'event': 'failed', 'reason': redact(e)})
                event(name, 'failed', reason=redact(e))
    fix_asset_extensions(output_dir)
    generate_strategy(ctx)
    ctx['strategy_generated'] = True
    build_listing_json(ctx)
    report = write_quality_report(ctx)
    event('validation', 'accepted' if report['publish_ready'] else 'needs_review',
          technical_valid=report['technical_valid_count'], required=11, publish_ready=report['publish_ready'])
    log.info('technical validity=%d/11; publish_ready=%s', report['technical_valid_count'], report['publish_ready'])
    return 0 if report['publish_ready'] else (2 if report['structurally_complete'] else 1)


def main():
    parser = argparse.ArgumentParser(description='一键出海：离线规划、素材验收与授权生成')
    parser.add_argument('--prompt', default='')
    parser.add_argument('--version', action='store_true')
    parser.add_argument('--plan-only', action='store_true', help='只生成计划，不读取密钥或调用网络')
    parser.add_argument('--audit', metavar='OUTPUT_DIR', help='只读检查已有产物，JSON输出至stdout')
    parser.add_argument('--check-plan', metavar='JSON_FILE', help='离线检查浏览器导出的计划，不执行生成')
    args = parser.parse_args()
    if args.check_plan:
        from src.planning import check_plan
        try:
            if os.path.getsize(args.check_plan) > 1_000_000:
                raise ValueError('plan exceeds 1 MB')
            with open(args.check_plan, encoding='utf-8') as f:
                result = check_plan(json.load(f))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result['valid'] else 1
        except (OSError, ValueError) as e:
            print('plan rejected: ' + redact(e), file=sys.stderr)
            return 1
    if args.version:
        print(read_version())
        return 0
    if args.audit:
        print(json.dumps(inspect_outputs(args.audit), ensure_ascii=False, indent=2))
        return 0
    if not args.prompt:
        parser.print_help()
        return 2
    try:
        return run_pipeline(args.prompt, plan_only=args.plan_only)
    except Exception as e:
        print('agent stopped: ' + redact(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
