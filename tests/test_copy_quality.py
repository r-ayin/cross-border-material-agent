# -*- coding: utf-8 -*-
"""Offline copy quality regressions. No sockets, credentials or real model calls."""
import copy
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'agent'))
from src import copy_gen as cg
from src import prompts


def product_fixture():
    return {
        'platform': '1688', 'offer_id': 'ID-666-4-36cm',
        'url': 'https://source.invalid/items/666-4-36cm?model=28inch',
        'subject': 'White cotton shirt with collar, long sleeves and plain design',
        'attributes': [
            {'attributeName': 'Color', 'value': 'White'},
            {'attributeName': 'Material', 'value': 'Cotton'},
            {'attributeName': 'Model', 'value': 'MODEL-88cm-4'},
        ],
        'skus': [{'skuId': 'SKU-4-666-36cm', 'amountOnSale': 4,
                  'skuAttributes': [{'attributeName': 'Size', 'value': 'S', 'valueTrans': 'S'},
                                    {'attributeName': 'Color', 'value': 'White'}]}],
        'sale_info': {'price': '4.66', 'currency': 'CNY'},
    }


def valid_copy(product, lang):
    item = cg._fallback_copy(product, lang)
    values = {
        'en': ('White cotton shirt',
               ['White shirt', 'Cotton', 'Collar', 'Long sleeves', 'Plain design'],
               ['white shirt', 'cotton shirt', 'shirt', 'collar shirt', 'long sleeve shirt', 'plain shirt', 'white cotton', 'collared shirt']),
        'ko': ('흰색 면 셔츠',
               ['흰색 셔츠', '면', '카라', '긴 소매', '무지 디자인'],
               ['흰색 셔츠', '면 셔츠', '셔츠', '카라 셔츠', '긴 소매 셔츠', '무지 셔츠', '흰색 면', '카라']),
        'pt': ('Camisa branca de algodão',
               ['Camisa branca', 'Algodão', 'Gola', 'Mangas longas', 'Desenho liso'],
               ['camisa branca', 'camisa de algodão', 'camisa', 'camisa com gola', 'camisa de manga longa', 'camisa lisa', 'algodão branco', 'gola']),
    }
    item['title'], item['bullet_points'], item['search_keywords'] = values[lang]
    return item


class FakeChat:
    def __init__(self, responder):
        self.responder = responder
        self.calls = []
        self.lock = threading.Lock()

    def chat(self, model, messages, temperature=0.7, max_tokens=8000, timeout=None):
        prompt = messages[-1]['content']
        lang = next(code for code in cg.LOCAL if f'Language code: {code};' in prompt)
        with self.lock:
            attempt = 1 + sum(call['lang'] == lang for call in self.calls)
            self.calls.append({'lang': lang, 'attempt': attempt, 'model': model,
                               'messages': messages, 'timeout': timeout})
        value = self.responder(lang, attempt)
        if isinstance(value, Exception):
            raise value
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


class ClockBudget:
    def __init__(self, seconds):
        self.deadline = time.monotonic() + seconds

    def remaining(self):
        return max(0.0, self.deadline - time.monotonic())


class OfflineCopyTests(unittest.TestCase):
    def setUp(self):
        def forbidden(*args, **kwargs):
            raise AssertionError('network and real model calls are forbidden in offline tests')
        for target in ('socket.socket', 'socket.create_connection', 'socket.getaddrinfo',
                       'src.dsapi.ChatClient.chat', 'src.dsapi.get_env'):
            blocker = patch(target, side_effect=forbidden)
            blocker.start()
            self.addCleanup(blocker.stop)
        self.temp = tempfile.TemporaryDirectory(prefix='copy-quality-offline-')
        self.addCleanup(self.temp.cleanup)
        self.product = product_fixture()

    def run_copies(self, responder, product=None, budget=None):
        chat = FakeChat(responder)
        ctx = {'product': self.product if product is None else product,
               'chat': chat, 'output_dir': self.temp.name}
        if budget is not None:
            ctx['budget'] = budget
        paths = cg.generate_copies(ctx)
        self.assertEqual(set(paths), {'en', 'ko', 'pt'})
        report = json.loads((Path(self.temp.name) / 'copy_quality.json').read_text(encoding='utf-8'))
        self.assertEqual(ctx['copy_quality'], report)
        for lang in cg.LOCAL:
            self.assertLessEqual(sum(call['lang'] == lang for call in chat.calls), 2)
        return ctx, chat, {lang: Path(path).read_text(encoding='utf-8') for lang, path in paths.items()}

    def test_socket_is_forbidden(self):
        with self.assertRaises(AssertionError):
            socket.socket()
        with self.assertRaises(AssertionError):
            socket.getaddrinfo('source.invalid', 443)

    def test_prompt_is_pure_complete_and_market_specific(self):
        product = copy.deepcopy(self.product)
        product['skus'] *= 31
        product['attributes'] += [{'attributeName': 'Extra', 'value': 'purple 666 4'}] * 30
        ctx = {'product': product, 'attr_map': {'guessed_material': 'silk'}}
        before = copy.deepcopy(ctx)
        for lang, market, language in [('en', 'US', 'English'), ('ko', 'KR', 'Korean'), ('pt', 'BR', 'Brazilian Portuguese')]:
            prompt = cg.build_copy_prompt(ctx, lang)
            self.assertEqual(prompt, cg.build_copy_prompt(ctx, lang))
            payload = prompt.split('<source_product_json>\n')[1].split('\n</source_product_json>')[0]
            self.assertEqual(json.loads(payload), product)
            self.assertIn(market, prompt)
            self.assertIn(language, prompt)
            self.assertIn('NOT additional factual evidence', prompt)
            self.assertIn(product['url'], prompt)
        self.assertEqual(ctx, before)
        with self.assertRaises(ValueError):
            cg.build_copy_prompt(ctx, 'fr')

    def test_prompts_do_not_invent_market_or_media_facts(self):
        guidance = ' '.join(prompts.MARKET_GUIDANCE.values()).lower()
        for forbidden in ['avoid number', 'avoid purple', '55/66/77', 'prices are in usd', 'warm climate', 'seasonal']:
            self.assertNotIn(forbidden, guidance)
        for forbidden in ['indoor scene', 'outdoor scene', 'colored background', 'textured background']:
            self.assertNotIn(forbidden, prompts.IMAGE_NEGATIVE_PROMPT)
        for forbidden in ['four views', 'full back view', 'clean grid']:
            self.assertNotIn(forbidden, prompts.ANCHOR_PROMPT.lower())
        self.assertIn('single product-only', prompts.ANCHOR_PROMPT)
        self.assertIn('no model', prompts.ANCHOR_PROMPT.lower())
        self.assertIn('currency as USD', prompts.COPY_SYSTEM)

    def test_schema_rejects_nonobjects_and_wrong_types(self):
        for value in [None, [], [valid_copy(self.product, 'en')], 'text', 42, True]:
            with self.subTest(value=value):
                self.assertIn('schema:object_required', cg.validate_copy_schema(value))
        for field, value in [('title', []), ('title', 123), ('description_markdown', {}),
                             ('bullet_points', 'text'), ('bullet_points', [None] * 5),
                             ('search_keywords', {}), ('search_keywords', [8] * 8)]:
            candidate = valid_copy(self.product, 'en')
            candidate[field] = value
            self.assertTrue(any(issue.startswith('schema:') for issue in cg.validate_copy_schema(candidate)))

    def test_schema_length_counts_and_empty_description(self):
        for field, value in [('title', ''), ('title', 'a' * 129), ('description_markdown', '  '),
                             ('bullet_points', ['a' * 61] + [str(i) for i in range(4)],),
                             ('bullet_points', [str(i) for i in range(8)]),
                             ('search_keywords', [str(i) for i in range(13)])]:
            candidate = valid_copy(self.product, 'en')
            candidate[field] = value
            self.assertTrue(any(issue.startswith('schema:') for issue in cg.validate_copy_schema(candidate)), (field, value))
        for title in ['x', 'x' * 128]:
            candidate = valid_copy(self.product, 'en')
            candidate['title'] = title
            self.assertEqual(cg.validate_copy_schema(candidate), [])

    def test_strict_json_rejects_inner_object_duplicate_keys_and_nan(self):
        for content in ['bad json', '{"title": "x", "title": "y"}', '{"title": NaN}',
                        'prefix {"title": "x"}', '```json\n{}\n```']:
            with self.subTest(content=content), self.assertRaises(ValueError):
                cg._parse_candidate(content)
        array = cg._parse_candidate('[{"title":"not a listing object"}]')
        self.assertIn('schema:object_required', cg.validate_copy_schema(array))

    def test_malformed_llm_json_falls_back_with_two_calls(self):
        bad = {'en': '[]', 'ko': '{"title": [], "bullet_points": null}', 'pt': 'not json'}
        ctx, chat, texts = self.run_copies(lambda lang, attempt: bad[lang])
        self.assertEqual(len(chat.calls), 6)
        for lang, quality in ctx['copy_quality'].items():
            self.assertEqual(quality['status'], 'needs_review')
            self.assertTrue(quality['fallback'])
            self.assertEqual(quality['attempts'], 2)
            self.assertFalse(cg._missing_sections(texts[lang], lang))
        self.assertTrue(all('STRUCTURED REPAIR REQUEST' in call['messages'][-1]['content']
                            for call in chat.calls if call['attempt'] == 2))

    def test_long_title_retry_fixes_without_third_call(self):
        def responder(lang, attempt):
            candidate = valid_copy(self.product, lang)
            if attempt == 1:
                candidate['title'] = 'x' * 129
            return candidate
        ctx, chat, _ = self.run_copies(responder)
        self.assertEqual(len(chat.calls), 6)
        for quality in ctx['copy_quality'].values():
            self.assertEqual(quality['checks_status'], 'passed', quality)
            self.assertEqual(quality['status'], 'needs_review')
            self.assertFalse(quality['fallback'])
            self.assertIn('schema:title:length', quality['history'][0]['issues'])

    def test_clean_localized_copy_can_pass(self):
        for lang in cg.LOCAL:
            issues = cg._audit_copy(valid_copy(self.product, lang), lang, self.product)
            self.assertEqual(issues, [], (lang, issues))
        ctx, chat, _ = self.run_copies(lambda lang, attempt: valid_copy(self.product, lang))
        self.assertEqual(len(chat.calls), 3)
        self.assertTrue(all(q['checks_status'] == 'passed' for q in ctx['copy_quality'].values()), ctx['copy_quality'])
        self.assertTrue(all(q['status'] == 'needs_review' for q in ctx['copy_quality'].values()))

    def test_no_measurement_header_bare_numbers_removed_as_whole_table(self):
        for lang in cg.LOCAL:
            text = ('## ' + cg.SECTION_HEADERS[lang][2]
                    + '\n| Size | Bust (cm) | Waist |\n| --- | --- | --- |\n| S | 88 | 66 |\n| M | 92 | 70 |')
            cleaned = cg._sanitize_size_data(text, lang, self.product)
            for number in ['88', '66', '92', '70']:
                self.assertNotIn(number, cleaned)
            self.assertIn('| S |', cleaned)
            self.assertNotIn('| M |', cleaned)
            self.assertIn(cg.NO_MEASURE_TEXT[lang], cleaned)
            self.assertEqual(cleaned, cg._sanitize_size_data(cleaned, lang, self.product))

    def test_measurement_flags_and_model_numbers_are_not_evidence(self):
        self.assertFalse(cg._source_has_measurements(self.product))
        self.assertFalse(cg._source_has_measurements({'measurements_provided': True}))
        product = {'attributes': [{'attributeName': 'Length (cm)', 'value': '62'}]}
        self.assertTrue(cg._source_has_measurements(product))
        product['measurements_missing'] = True
        self.assertFalse(cg._source_has_measurements(product))

    def test_one_source_measurement_does_not_license_others(self):
        product = copy.deepcopy(self.product)
        product['attributes'].append({'attributeName': 'Sleeve length', 'value': '62 cm'})
        cleaned = cg._sanitize_size_data('Sleeve 62 cm; waist 90 cm; length 40 inches.', 'en', product)
        self.assertIn('62 cm', cleaned)
        self.assertNotIn('90 cm', cleaned)
        self.assertNotIn('40 inches', cleaned)
        candidate = valid_copy(product, 'en')
        candidate['description_markdown'] += '\nWaist 62 cm.'
        issues = cg._audit_copy(candidate, 'en', product)
        self.assertIn('facts:measurement_relation_pending_review', issues)
        self.assertIn('facts:dimension_pending_review', issues)

    def test_ids_urls_models_and_numeric_source_sizes_survive(self):
        product = copy.deepcopy(self.product)
        product['skus'][0]['skuAttributes'][0]['value'] = '55'
        tokens = [product['offer_id'], product['url'], product['skus'][0]['skuId'], 'MODEL-88cm-4']
        text = '\n'.join(tokens) + '\nInvented: 89cm and 28"-30".'
        cleaned = cg._sanitize_size_data(text, 'en', product)
        for token in tokens:
            self.assertIn(token, cleaned)
        self.assertNotIn('89cm', cleaned)
        self.assertNotIn('28"-30"', cleaned)
        table = cg._sanitize_size_data('## Size Chart\n| Model | cm |\n| --- | --- |\n| MODEL-88cm-4 | 99 |', 'en', product)
        self.assertIn('MODEL-88cm-4', table)
        self.assertIn('| 55 |', table)

    def test_three_language_fallback_preserves_real_facts(self):
        product = copy.deepcopy(self.product)
        product['subject'] = '紫色衬衫，原始信息'
        product['attributes'].append({'attributeName': '颜色', 'value': '紫色'})
        ctx, _, texts = self.run_copies(lambda lang, attempt: RuntimeError('offline failure'), product)
        for lang, text in texts.items():
            self.assertTrue(text.startswith('# ' + cg.LOCAL[lang]['title']))
            self.assertIn(product['subject'], text)
            self.assertIn(product['url'], text)
            self.assertIn(product['offer_id'], text)
            self.assertIn('SKU-4-666-36cm', text)
            self.assertIn('MODEL-88cm-4', text)
            self.assertIn(cg.LOCAL[lang]['raw'], text)
            self.assertNotIn('No key features were provided', text)
            self.assertNotIn('product_video.mp4', text)
            self.assertEqual(ctx['copy_quality'][lang]['status'], 'needs_review')
            if lang != 'en':
                self.assertNotIn('## Key Features', text)
                self.assertNotIn('Not provided in source', text)
        self.assertIn('紫色', texts['en'])

    def test_sparse_facts_do_not_pad_bullets_or_keywords(self):
        product = {'platform': '1688', 'offer_id': '4', 'url': 'https://source.invalid/4',
                   'subject': 'Shirt', 'attributes': [], 'skus': []}
        for lang in cg.LOCAL:
            fallback = cg._fallback_copy(product, lang)
            self.assertEqual(len(fallback['bullet_points']), 1)
            self.assertEqual(fallback['search_keywords'], [])
        ctx, _, _ = self.run_copies(lambda lang, attempt: cg._fallback_copy(product, lang), product)
        for quality in ctx['copy_quality'].values():
            self.assertEqual(quality['status'], 'needs_review')
            self.assertIn('insufficient_facts:bullet_points', quality['reasons'])

    def test_fewer_bullets_are_kept_and_reviewed_not_invented(self):
        def responder(lang, attempt):
            candidate = valid_copy(self.product, lang)
            candidate['bullet_points'] = candidate['bullet_points'][:2]
            return candidate
        ctx, _, texts = self.run_copies(responder)
        for lang in cg.LOCAL:
            self.assertEqual(ctx['copy_quality'][lang]['status'], 'needs_review')
            self.assertIn('insufficient_facts:bullet_points', ctx['copy_quality'][lang]['reasons'])
            self.assertFalse(ctx['copy_quality'][lang]['fallback'])
            third = valid_copy(self.product, lang)['bullet_points'][2]
            self.assertNotIn('- ' + third + '\n', texts[lang])

    def test_sections_require_exact_headings_and_nonempty_bodies(self):
        candidate = valid_copy(self.product, 'en')
        candidate['description_markdown'] = '\n'.join('## ' + header for header in cg.SECTION_HEADERS['en'])
        self.assertTrue(any(issue.startswith('sections:empty:') for issue in cg._audit_copy(candidate, 'en', self.product)))
        self.assertIn('Size Chart', cg._missing_sections('## Size Charting\nnot a section', 'en'))
        self.assertIn('Product Information', cg._missing_sections('## Product Information\nEnglish body', 'ko'))
        text = cg._ensure_sections('', 'pt', self.product, cg.SECTION_ORDER)
        self.assertIn('Informações do Produto', text)
        self.assertIn('White', text)
        self.assertNotIn('Product information was not provided', text)

    def test_missing_section_repair_never_becomes_passed(self):
        def responder(lang, attempt):
            candidate = valid_copy(self.product, lang)
            header = cg.SECTION_HEADERS[lang][-1]
            candidate['description_markdown'] = candidate['description_markdown'].split('## ' + header)[0].rstrip()
            return candidate
        ctx, chat, texts = self.run_copies(responder)
        self.assertEqual(len(chat.calls), 6)
        for lang in cg.LOCAL:
            self.assertEqual(ctx['copy_quality'][lang]['status'], 'needs_review')
            self.assertFalse(cg._missing_sections(texts[lang], lang))

    def test_language_mixing_is_checked_in_body_not_only_title(self):
        for lang in ('ko', 'pt'):
            candidate = valid_copy(self.product, lang)
            candidate['description_markdown'] += '\n## ' + cg.SECTION_HEADERS[lang][1] + '\nThis product is available with your shirt.'
            issues = cg._audit_copy(candidate, lang, self.product)
            self.assertTrue(any(issue.startswith('language:') for issue in issues), issues)
        candidate = valid_copy(self.product, 'en')
        candidate['bullet_points'][0] = '여름 옷'
        self.assertIn('language:mixed_script', cg._audit_copy(candidate, 'en', self.product))

    def test_unverified_material_care_logistics_and_certification_flags(self):
        cases = [
            ('Silk shirt', 'unsupported_material:silk'),
            ('Machine wash cold.', 'unverified_care'),
            ('Package weight: 0.25 kg. Free shipping in 3 days.', 'unverified_logistics'),
            ('CE certified.', 'unverified_certification'),
            ('100% cotton.', 'unverified_composition'),
            ('R$ 4.66', 'unverified_currency'),
            ('S = 55; S = P.', 'size_equivalence_pending_review'),
        ]
        for claim, expected in cases:
            candidate = valid_copy(self.product, 'en')
            candidate['description_markdown'] += '\n' + claim
            issues = cg._audit_copy(candidate, 'en', self.product)
            self.assertTrue(any(expected in issue for issue in issues), (claim, issues))

    def test_translated_unsupported_claims_are_flagged(self):
        for lang, claim in [('ko', '실크 소재. 세탁 가능. 무료 배송. 포장 무게 300 g.'),
                            ('pt', 'Seda. Lavagem fácil. Frete grátis. Peso da embalagem: 300 g.')]:
            candidate = valid_copy(self.product, lang)
            candidate['description_markdown'] += '\n' + claim
            issues = cg._audit_copy(candidate, lang, self.product)
            for expected in ['unsupported_material:silk', 'unverified_care', 'unverified_logistics']:
                self.assertTrue(any(expected in issue for issue in issues), (lang, issues))

    def test_unsafe_generated_claims_are_removed_but_recorded(self):
        def responder(lang, attempt):
            candidate = valid_copy(self.product, lang)
            candidate['description_markdown'] += '\nFree shipping. Package weight: 9 kg. Silk.'
            return candidate
        ctx, _, texts = self.run_copies(responder)
        for lang in cg.LOCAL:
            self.assertNotIn('9 kg', texts[lang])
            self.assertNotIn('Free shipping', texts[lang])
            self.assertEqual(ctx['copy_quality'][lang]['status'], 'needs_review')
            self.assertTrue(any('unverified_logistics' in issue for issue in ctx['copy_quality'][lang]['reasons']))

    def test_unverified_json_cannot_hide_hallucinations(self):
        candidate = valid_copy(self.product, 'en')
        candidate['description_markdown'] += '\n```json\n{"material":"silk", "waist":"999 cm"}\n```'
        issues = cg._audit_copy(candidate, 'en', self.product)
        self.assertIn('facts:unverified_quoted_data', issues)
        self.assertIn('facts:unsupported_material:silk', issues)

    def test_raw_sku_omission_and_new_url_are_reviewed(self):
        candidate = valid_copy(self.product, 'en')
        candidate['description_markdown'] = candidate['description_markdown'].replace(cg._json(cg._raw_inventory(self.product)), '{}')
        candidate['description_markdown'] += '\nhttps://unknown.invalid/product'
        issues = cg._audit_copy(candidate, 'en', self.product)
        self.assertIn('facts:raw_sku_integrity', issues)
        self.assertIn('facts:unknown_url', issues)

    def test_expired_budget_uses_no_model_calls(self):
        ctx, chat, _ = self.run_copies(lambda lang, attempt: self.fail('must not call'), budget=ClockBudget(0))
        self.assertEqual(chat.calls, [])
        for quality in ctx['copy_quality'].values():
            self.assertEqual(quality['attempts'], 0)
            self.assertIn('budget:exhausted', quality['reasons'])
            self.assertEqual(quality['status'], 'needs_review')

    def test_budget_bounds_wait_and_late_reply_cannot_overwrite(self):
        release = threading.Event()
        finished = threading.Event()
        counter, lock = [], threading.Lock()

        def responder(lang, attempt):
            release.wait(timeout=2)
            with lock:
                counter.append(lang)
                if len(counter) == 3:
                    finished.set()
            return valid_copy(self.product, lang)

        start = time.monotonic()
        try:
            ctx, chat, texts = self.run_copies(responder, budget=ClockBudget(0.15))
            self.assertLess(time.monotonic() - start, 1.5)
            self.assertEqual(len(chat.calls), 3)
            self.assertTrue(all(0 < call['timeout'] <= 0.15 for call in chat.calls))
            self.assertTrue(all(q['status'] == 'needs_review' for q in ctx['copy_quality'].values()))
        finally:
            release.set()
        self.assertTrue(finished.wait(timeout=1))
        for lang, text in texts.items():
            self.assertEqual((Path(self.temp.name) / f'product_description_{lang}.md').read_text(encoding='utf-8'), text)

    def test_transport_fallback_is_always_review_required(self):
        ctx, chat, _ = self.run_copies(lambda lang, attempt: RuntimeError('transport') if attempt == 1 else valid_copy(self.product, lang))
        self.assertEqual(len(chat.calls), 6)
        for quality in ctx['copy_quality'].values():
            self.assertEqual(quality['status'], 'needs_review')
            self.assertIn('fallback:model', quality['reasons'])

    def test_html_and_fenced_size_tables_cannot_hide_bare_numbers(self):
        tables = ['<table><tr><th>Size</th><th>cm</th></tr><tr><td>S</td><td>89</td></tr></table>',
                  '```markdown\n| Size | cm |\n| --- | --- |\n| S | 89 |\n```']
        for table in tables:
            cleaned = cg._sanitize_size_data('## Size Chart\n' + table, 'en', self.product)
            self.assertNotIn('89', cleaned)
            self.assertIn('| S |', cleaned)
            candidate = valid_copy(self.product, 'en')
            candidate['description_markdown'] += '\n' + table
            self.assertIn('facts:size_data_repair_required', cg._audit_copy(candidate, 'en', self.product))

    def test_measured_source_and_top_level_model_are_preserved_in_fallback(self):
        product = copy.deepcopy(self.product)
        product['model_number'] = 'XYZ-100cm'
        product['description_html'] = '<table><tr><th>Length (cm)</th><td>62</td></tr></table>'
        ctx, _, texts = self.run_copies(lambda lang, attempt: 'null', product)
        for lang, text in texts.items():
            self.assertIn('XYZ-100cm', text)
            self.assertIn(product['description_html'], text)
            self.assertIn(cg.LOCAL[lang]['measured'], text)
            self.assertEqual(ctx['copy_quality'][lang]['status'], 'needs_review')

    def test_source_id_prefix_is_not_identity_preservation(self):
        product = copy.deepcopy(self.product)
        product['offer_id'] = '123'
        candidate = valid_copy(product, 'en')
        candidate['description_markdown'] = candidate['description_markdown'].replace('Product ID: 123', 'Product ID: 123-456')
        self.assertIn('facts:source_identity_missing:offer_id', cg._audit_copy(candidate, 'en', product))

    def test_matching_id_cannot_license_a_measurement_claim(self):
        product = copy.deepcopy(self.product)
        product['offer_id'] = '36'
        candidate = valid_copy(product, 'en')
        candidate['description_markdown'] += '\nWaist: 36 cm.'
        self.assertIn('facts:dimension_pending_review', cg._audit_copy(candidate, 'en', product))

    def test_language_check_also_covers_unrecognized_sections(self):
        for lang in ('ko', 'pt'):
            candidate = valid_copy(self.product, lang)
            candidate['description_markdown'] += '\n## Other\nThis product is available with your shirt.'
            self.assertTrue(any(issue.startswith('language:') for issue in cg._audit_copy(candidate, lang, self.product)))

    def test_negated_material_evidence_does_not_authorize_positive_claim(self):
        product = copy.deepcopy(self.product)
        product['subject'] = 'Shirt, not cotton'
        product['attributes'][1]['value'] = 'Not cotton'
        candidate = valid_copy(product, 'en')
        self.assertIn('facts:material_evidence_pending_review:cotton', cg._audit_copy(candidate, 'en', product))

    def test_raw_sku_types_are_not_silently_coerced(self):
        candidate = valid_copy(self.product, 'en')
        candidate['description_markdown'] = candidate['description_markdown'].replace('"amountOnSale": 4', '"amountOnSale": 4.0')
        issues = cg._audit_copy(candidate, 'en', self.product)
        self.assertIn('facts:raw_sku_integrity', issues)
        self.assertIn('facts:unverified_quoted_data', issues)

    def test_pending_measured_size_chart_never_passes(self):
        product = copy.deepcopy(self.product)
        product['measurements'] = {'sleeve': '62 cm'}
        for lang in cg.LOCAL:
            candidate = valid_copy(product, lang)
            self.assertIn('facts:measurement_relation_pending_review', cg._audit_copy(candidate, lang, product))


if __name__ == '__main__':
    unittest.main()
