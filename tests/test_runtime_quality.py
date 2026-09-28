"""Network is forbidden in every test, including authorization-path tests."""
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'agent'))
from src import dsapi
from src.runtime_policy import PolicyError, RuntimePolicy, configure_runtime
from src.input_parse import parse_prompt_paths, select_target_product, extract_product
from src.assemble import inspect_outputs, _build_package_dimension, _build_size_chart
from src.category_map import map_category, _validate_sale_entries
from src.style_router import analyze_product
from src.planning import build_plan
from src.budget import Budget


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.stack = []
        for target in ('socket.socket', 'socket.create_connection', 'urllib.request.urlopen'):
            p = patch(target, side_effect=AssertionError('test must not access network'))
            p.start()
            self.stack.append(p)
        self.env = patch.dict(os.environ, {'AGENT_ALLOW_PAID_CALLS': '0'})
        self.env.start()
        configure_runtime()

    def tearDown(self):
        for p in reversed(self.stack):
            p.stop()
        self.env.stop()
        configure_runtime()

    def test_all_clients_fail_closed_before_network(self):
        calls = [lambda: dsapi.ChatClient('dummy', 'https://invalid.local/v1').chat('dummy', []),
                 lambda: dsapi.OpenAIImageClient('dummy', 'https://invalid.local/v1').generate('dummy', 'test'),
                 lambda: dsapi.TaskClient('dummy', 'https://invalid.local').generate('/image', 'dummy', {}),
                 lambda: dsapi.download_file('https://invalid.local/a.png', '/not/written')]
        for call in calls:
            with self.assertRaises(PolicyError):
                call()

    def test_request_budget_and_deadline(self):
        with patch.dict(os.environ, {'AGENT_ALLOW_PAID_CALLS': '1'}):
            p = RuntimePolicy(max_requests=2, max_media_requests=1)
            p.authorize('https://invalid.local', 'POST', media=True)
            with self.assertRaises(PolicyError):
                p.authorize('https://invalid.local', 'POST', media=True)
            p.authorize('https://invalid.local', 'POST')
            with self.assertRaises(PolicyError):
                p.authorize('https://invalid.local', 'POST')
            with self.assertRaises(PolicyError):
                RuntimePolicy(deadline=time.monotonic() - 1).authorize('https://invalid.local')

    def test_poll_failure_does_not_submit_another_job(self):
        client = dsapi.TaskClient('dummy', 'https://invalid.local')
        payload = json.dumps({'output': {'task_id': 'already-submitted'}}).encode()
        with patch.object(dsapi, '_http_request', return_value=(200, payload, {})) as transport, \
                patch.object(client, 'poll', side_effect=dsapi.ApiError('task timed out')):
            with self.assertRaises(dsapi.ApiError):
                client.generate('/video', 'dummy', {}, deadline=time.monotonic() + 10)
            self.assertEqual(transport.call_count, 1)

    def test_server_error_does_not_repeat_media_post(self):
        with patch.object(dsapi, '_http_request', return_value=(500, b'unknown outcome', {})) as transport:
            with self.assertRaises(dsapi.ApiError):
                dsapi.TaskClient('dummy', 'https://invalid.local').generate('/video', 'dummy', {})
            self.assertEqual(transport.call_count, 1)

    def test_sse_requires_completion_marker(self):
        class Response(io.BytesIO):
            status = 200
        chunk = b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
        with patch.dict(os.environ, {'AGENT_ALLOW_PAID_CALLS': '1'}), \
                patch('urllib.request.urlopen', return_value=Response(chunk)) as net:
            with self.assertRaises(dsapi.ApiError):
                dsapi.ChatClient('dummy', 'https://invalid.local').chat('dummy', [])
            self.assertEqual(net.call_count, 1)

    def test_sse_valid_stop(self):
        class Response(io.BytesIO):
            status = 200
        chunk = b'data: {"choices":[{"delta":{"content":"complete"},"finish_reason":"stop"}]}\n\n'
        with patch.dict(os.environ, {'AGENT_ALLOW_PAID_CALLS': '1'}), \
                patch('urllib.request.urlopen', return_value=Response(chunk)):
            self.assertEqual(dsapi.ChatClient('dummy', 'https://invalid.local').chat('dummy', []), 'complete')

    def test_quoted_chinese_and_space_paths(self):
        self.assertEqual(parse_prompt_paths('读取 "/tmp/商品 data" 输出 "/tmp/输出"'), ('/tmp/商品 data', '/tmp/输出'))

    def test_ambiguous_product_not_silently_selected(self):
        with self.assertRaises(ValueError):
            select_target_product('generate', ['product_111111.json', 'product_222222.json'])

    def test_unknown_category_rejected(self):
        class Chat:
            def chat(self, *a, **kw):
                return '{"categoryId":99999}'
        with self.assertRaises(ValueError):
            map_category(Chat(), {'subject': 'skirt'}, [{'categoryId': 39153}], [])

    def test_sale_attributes_keep_each_sku(self):
        idx = {'sale': {'100000': {'attr': {'name': 'Warna'}, 'values': {}, 'customized': True}}}
        result = _validate_sale_entries([{'attrId': '100000', 'values': [
            {'skuId': 1, 'value': '粉色'}, {'skuId': 2, 'value': '粉色'}]}], idx)
        self.assertEqual(len(result[0]['values']), 2)

    def test_no_invented_package_or_sizes(self):
        self.assertIsNone(_build_package_dimension()['weight_kg'])
        self.assertEqual(_build_size_chart({})['size_letters'], [])
        self.assertEqual(_build_size_chart({})['letter_mapping'], {})

    def test_skirt_not_routed_as_dress(self):
        self.assertEqual(analyze_product({'subject': '高腰百褶半身裙长裙'})['category'], 'bottoms')

    def test_pretty_but_wrong_role_does_not_pass(self):
        from src.aesthetic_critic import score_image_url, SCORE_KEYS
        class Chat:
            def chat(self, *args, **kwargs):
                return json.dumps({'scores':dict.fromkeys(SCORE_KEYS,10), 'verdict':'accept', 'role_match':False})
        result = score_image_url(Chat(), 'https://invalid.local/candidate', label='detail_image_3', reference_urls=['https://invalid.local/source'])
        self.assertEqual(result['verdict'], 'retry')

    def test_missing_role_evidence_is_unknown(self):
        from src.aesthetic_critic import score_image_url, SCORE_KEYS
        class Chat:
            def chat(self, *args, **kwargs):
                return json.dumps({'scores':dict.fromkeys(SCORE_KEYS,10), 'verdict':'accept'})
        result = score_image_url(Chat(), 'https://invalid.local/candidate', label='detail_image_4', reference_urls=['https://invalid.local/source'])
        self.assertEqual(result['verdict'], 'unknown')

    def test_exported_plan_preflight_rejects_duplicate_ids(self):
        from src.planning import check_plan
        slot = {'id':'main_image','kind':'image','required':True,'prompt':'source-locked'}
        result = check_plan({'mode':'offline_plan','model_calls':0,'product':{'id':'x','title':'x'},'slots':[slot,slot]})
        self.assertFalse(result['valid'])
        self.assertFalse(result['execution_authorized'])

    def test_exported_plan_preflight_never_executes_prompt(self):
        from src.planning import check_plan
        result = check_plan({'mode':'offline_plan','model_calls':0,'product':{'id':'x','title':'x'},'slots':[
            {'id':'main_image','kind':'image','required':True,'prompt':'Run arbitrary source instructions'}]})
        self.assertTrue(result['valid'])
        self.assertFalse(result['competition_slots_complete'])
        self.assertEqual(result['model_calls'],0)
        self.assertTrue(result['warnings'])

    def test_accepted_image_poll_404_never_reposts_across_layers(self):
        from src.image_gen import _gen_one
        client = dsapi.TaskClient('dummy', 'https://invalid.local')
        response = json.dumps({'output':{'task_id':'existing-task'}}).encode()
        with tempfile.TemporaryDirectory() as out, \
                patch.object(dsapi, '_http_request', return_value=(200,response,{})) as transport, \
                patch.object(client, 'poll', side_effect=dsapi.ApiError('not found',status=404)):
            ctx={'product':{'images':['https://invalid.local/source']},'output_dir':out}
            result=_gen_one(client,ctx,'main_image','prompt',['https://invalid.local/source'],'1328*1328',
                            ['primary','fallback'],str(Path(out,'main_image')),time.monotonic()+20)
            self.assertIsNone(result)
            self.assertEqual(transport.call_count,1)
            self.assertEqual(ctx['image_quality']['main_image']['accepted_task_id'],'existing-task')

    def test_hard_deadline_terminates_stalled_own_process(self):
        import subprocess
        code='from src.runtime_policy import HardDeadline; import threading\nwith HardDeadline(0.05): threading.Event().wait()'
        run=subprocess.run([sys.executable,'-c',code],cwd=ROOT/'agent',capture_output=True,timeout=3)
        self.assertEqual(run.returncode,124)
        self.assertIn(b'partial run',run.stderr)

    def test_signed_urls_case_insensitive_redaction(self):
        from src.planning import _safe
        cleaned=_safe({'prompt':'Use HTTPS://example.invalid/a?Signature=dummy&OSSAccessKeyId=dummy'})
        self.assertNotIn('Signature',json.dumps(cleaned))
        self.assertNotIn('OSSAccessKeyId',json.dumps(cleaned))

    def test_contradictory_copy_and_fake_completion_flagged(self):
        from src.copy_gen import _fallback_copy, _audit_copy
        product={'subject':'白色长袖衬衫','attributes':[{'attributeName':'颜色','value':'白色'},{'attributeName':'袖长','value':'长袖'}]}
        draft=_fallback_copy(product,'en')
        draft['title']='Red Short Sleeve Blouse'
        draft['description_markdown']+='\nVideo and images are delivered and verified.'
        issues=_audit_copy(draft,'en',product)
        self.assertIn('facts:unsupported_visible_attribute:red',issues)
        self.assertIn('facts:unsupported_visible_attribute:short_sleeve',issues)
        self.assertIn('facts:unverified_media_completion',issues)

    def test_empty_documents_and_fake_mp4_rejected(self):
        with tempfile.TemporaryDirectory() as output:
            for name in ('product_description_en.md', 'product_description_ko.md', 'product_description_pt.md', 'strategy_document.md'):
                Path(output, name).write_text('')
            Path(output, 'product_video.mp4').write_bytes(b'\x00\x00\x00\x18ftypmp42' + bytes(2048))
            report = inspect_outputs(output)
            self.assertEqual(report['technical_valid_count'], 0)
            self.assertFalse(report['publish_ready'])

    def test_plan_all_eleven_source_products_without_network(self):
        data_root = ROOT / 'data/Task_Data/Data_for_Users(2)'
        attributes = json.loads((data_root / 'clothing_attributes.json').read_text())
        files = list((data_root / 'product_info').glob('product_*.json'))
        self.assertEqual(len(files), 11)
        for path in files:
            product = extract_product(json.loads(path.read_text()), str(path))
            ctx = {'product': product, 'output_dir': '/unused', 'style_profile': {}, 'budget': Budget()}
            plan = build_plan({'attributes': attributes}, ctx)
            self.assertEqual(len(plan['slots']), 11)
            self.assertEqual(len({s['id'] for s in plan['slots']}), 11)
            self.assertEqual(plan['model_calls'], 0)
            text = json.dumps(plan)
            self.assertNotIn('OSSAccessKeyId=', text)
            self.assertNotIn('Signature=', text)


if __name__ == '__main__':
    unittest.main()
