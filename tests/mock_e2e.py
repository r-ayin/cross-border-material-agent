"""Hermetic orchestration test: valid mock containers are not publishable proof."""
import json
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'agent'))
sys.path.insert(0, str(ROOT / 'tests'))
from test_video_quality import mp4
from src.input_parse import extract_product
from src.copy_gen import _fallback_copy
from src.aesthetic_critic import SCORE_KEYS
import agent


def png():
    def chunk(tag, body):
        return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', zlib.crc32(tag + body) & 0xffffffff)
    raw = b''.join(b'\0' + b'\xff\xff\xff' * 1024 for _ in range(1024))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB',1024,1024,8,2,0,0,0)) + chunk(b'IDAT',zlib.compress(raw)) + chunk(b'IEND',b'')


def main():
    data = ROOT / 'data/Task_Data/Data_for_Users(2)'
    product = extract_product(json.loads((data / 'product_info/product_8822221153828.json').read_text()), 'mock-input')
    calls = []
    class Chat:
        def chat(self, model, messages, **kwargs):
            calls.append(('chat', model))
            text = messages[-1]['content']
            if isinstance(text, list):
                if 'Does this image' in text[-1].get('text', ''):
                    return 'NO'
                return json.dumps({'scores':dict.fromkeys(SCORE_KEYS,8),'verdict':'accept','reason':'mock only','role_match':True})
            if '候选叶子类目' in text:
                return json.dumps({'categoryId':39153,'reason':'mock selected supplied library member'})
            if '目标产品属性定义' in text:
                return json.dumps({'productAttributes':[],'saleAttributes':[],'unmatched':[]})
            match = re.search(r'Language code: (en|ko|pt)', text)
            return json.dumps(_fallback_copy(product, match.group(1) if match else 'en'),ensure_ascii=False)
    class Tasks:
        def generate(self, path, model, input_obj, parameters=None, **kwargs):
            calls.append(('generation',model))
            return {'results':[{'url':'https://mock.invalid/asset'}]}
    def download(url,dest_path,**kwargs):
        Path(dest_path).write_bytes(mp4(duration=5,audio=True) if str(dest_path).endswith('.mp4') else png())
        return os.path.getsize(dest_path)
    with tempfile.TemporaryDirectory(prefix='oneclick-hermetic-') as out, \
         patch.dict(os.environ, {'AGENT_ALLOW_PAID_CALLS':'1','DASHSCOPE_API_KEY':'offline-placeholder',
                                'DASHSCOPE_BASE_URL':'https://mock.invalid/api/v1','OPENAI_BASE_URL':'https://mock.invalid/v1'}), \
         patch('socket.socket',side_effect=AssertionError('network prohibited in mock E2E')), \
         patch('socket.create_connection',side_effect=AssertionError('network prohibited in mock E2E')), \
         patch('urllib.request.urlopen',side_effect=AssertionError('network prohibited in mock E2E')), \
         patch.object(agent,'ChatClient',return_value=Chat()), \
         patch.object(agent,'TaskClient',return_value=Tasks()), \
         patch.object(agent,'describe_product_vision',return_value=''), \
         patch('src.image_gen.download_file',side_effect=download), \
         patch('src.video_gen.download_file',side_effect=download):
        code=agent.run_pipeline(f'读取 "{data}" 商品8822221153828，保存到 "{out}"')
        report=json.loads(Path(out,'quality_report.json').read_text())
        assert report['technical_valid_count']==11, [(a['id'],a['checks']) for a in report['artifacts'] if not a['technical_valid']]
        assert report['publish_ready'] is False
        assert code==2, f'mock/review-required artifacts must not produce success; got {code}'
        assert len([x for x in calls if x[0]=='generation'])==7
        print(json.dumps({'mock_e2e':'passed','technical_valid':'11/11','publish_ready':False,
                          'expected_exit':code,'mock_media_calls':7,'actual_network_calls':0},ensure_ascii=False))


if __name__=='__main__':
    main()
