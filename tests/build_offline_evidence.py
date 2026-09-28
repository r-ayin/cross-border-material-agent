"""Rebuild auditable local evidence; never call a model or modify historical assets."""
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'agent'))
from src.input_parse import extract_product
from src.planning import build_plan
from src.style_router import analyze_product, global_image_profile
from src.assemble import inspect_outputs

OBSERVATIONS = {
    'main_image': ['主图原图目检：浅灰白背景，带模特上衣与鞋；不能以文件存在等同白底和商品独占合格。',
                   '来源：frontend/assets/main_image.png；与真实商品原图保真尚未独立比对。'],
    'detail_image_1': ['目检为整裙展示，可承担整体卖点图；腰头和裙长与其他图片不完全一致，保真待源图比较。'],
    'detail_image_2': ['应为工艺特写，实际为整裙悬挂图。工艺槽位未完成。'],
    'detail_image_3': ['应为材质特写，实际为整裙展示图。材质槽位未完成。'],
    'detail_image_4': ['应为生活场景，实际为纯背景整裙展示图。场景槽位未完成。'],
    'detail_image_5': ['整裙全景可读，但与其他详情图重复度高，需检查来源一致性。'],
    'product_video': ['ffprobe：H.264 1920×1080，123帧；视频轨道5.125秒，AAC音轨5.16秒，容器5.16秒。',
                      'ffmpeg逐秒抽帧成功，右下角可见Happy Horse水印。不得通过去水印冒充可发布素材，需供应商授权的无水印输出。',
                      '只是一段短片，未交付所设计的完整多镜头结构；赛规本身没有15/30秒最低时长。',
                      '有音轨不等于配乐授权、听感或音画同步已通过。'],
    'product_description_en': ['旧文案重复标题；图像扩展名写为.jpeg而文件实际为.png。',
                              '含有标签洗护指引等未经源数据证实的推断；新版须按真实字段复核。'],
    'product_description_ko': ['旧文案52–55行编造腰围66/71/76/81cm、臀围86/91/96/101cm及55/66/77/88韩码关系。',
                              '商品结构化来源只有S/M/L/XL，没有对应实测值。还存在英文章节标题、重复标题及图片扩展名错误。'],
    'product_description_pt': ['把S/M/L/XL直接等同P/M/G/GG，缺少品牌实测依据；旧文案重复标题、图片扩展名错误。'],
    'strategy_document': ['旧策略45–61行宣称SDXL、ControlNet、IP-Adapter、Runway、Kling；实际本项目未使用这些组件。',
                          '把属性未映射当成源数据缺失，并声称安全的“透气”表述；与源事实和实际流程不一致。'],
}


def main():
    assets = ROOT / 'frontend/assets'
    data = ROOT / 'data/Task_Data/Data_for_Users(2)'
    source = data / 'product_info/product_8822221153828.json'
    product = extract_product(json.loads(source.read_text()), str(source))
    signals = analyze_product(product)
    ctx = {'product': product, 'output_dir': '/planned-output', 'style_profile': global_image_profile(product, 'professional', signals)}
    with patch('socket.socket', side_effect=AssertionError('offline evidence must not use network')), \
            patch('socket.create_connection', side_effect=AssertionError('offline evidence must not use network')), \
            patch('urllib.request.urlopen', side_effect=AssertionError('offline evidence must not use network')):
        plan = build_plan({'attributes': json.loads((data / 'clothing_attributes.json').read_text())}, ctx)
        audit = inspect_outputs(str(assets))
    audit.update(generated_date='2026-09-22', mode='offline_historical_audit', model_calls=0,
                 baseline_score={'value': 67, 'source': 'user_report', 'verified': False},
                 updated_official_score=None,
                 archive_review={'jsonl_records_scanned': 24762, 'parse_errors': 0, 'research_documents': 8,
                                 'scope': '历史会话全量流式扫描、规则和研究阅读；不是每条工具原文逐字人工阅读。'},
                 official_weights={'A1_content_compliance':25,'A2_specification':20,'A3_mapping':18,
                                   'A4_localization':15,'A5_factuality':10,'A6_image_usability':7,'A7_video_usability':5},
                 expert_weights={'experience':15,'image':30,'video':20,'strategy':35},
                 provider_test={'host':'api.lk888.ai','status':'blocked_by_enterprise_domain_policy',
                                'generation_requests':0,'token_plan_requests':0})
    for item in audit['artifacts']:
        item['checks'].extend(OBSERVATIONS.get(item['id'], []))
        item['status'] = '需返工' if item['id'] not in ('detail_image_1','detail_image_5') else '需源图保真复核'
        item['evidence_type'] = 'local_structure_and_manual_observation'
    audit['publish_ready'] = False
    audit['limitations'].extend(['没有官方67分分项回执，不能把本地检查当官方重新评分。',
                                '尚未调用低价模型；新提示词没有真实生成质量证据。'])
    for name, obj in (('preflight-plan.json', plan), ('audit-report.json', audit)):
        (assets / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'plan_slots':len(plan['slots']), 'audited_artifacts':len(audit['artifacts']),
                      'technical_valid':audit['technical_valid_count'], 'publish_ready':False,'model_calls':0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
