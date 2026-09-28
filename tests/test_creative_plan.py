"""Offline regression for evidence, keyframe contracts and frame-exact edits."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'agent'))
from src.creative_plan import (allocate_frames, build_film_plan, caption_options, fact_ledger,
                               compile_edit, format_timeline_subtitles, image_brief, validate_frame)
spec = importlib.util.spec_from_file_location('film_finish', ROOT/'tools/film_finish.py')
finish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(finish)

PRODUCT = {'offer_id': '8822221153828', 'subject': '高腰粉色百褶半身裙',
           'images': ['https://source.invalid/a.jpg'], 'attributes': [
               {'attributeName': '工艺', 'value': '百褶'}, {'attributeName': '面料名称', 'value': '涤纶'},
               {'attributeName': '颜色', 'value': '粉色'}, {'attributeName': '弹力', 'value': '无弹'},
               {'attributeName': '裙长', 'value': '长裙'}]}
CAPS = {'verified': True, 'supports_reference': True, 'supports_last_frame': True, 'durations': [5, 6, 12]}


def catalog():
    plan = build_film_plan(PRODUCT)
    return [{'id':'frame-'+s['id'], 'product_id':PRODUCT['offer_id'], 'approved':True,
             'fidelity_verified':True, 'technical_valid':True, 'origin':'generated',
             'source_ids':['source:0'], 'role':s['role'], 'framing':s['framing'],
             'presentation':s['presentation'], 'subject_identity':'pink-skirt-01',
             'scene_id':'studio-01'} for s in plan['shots']]


def clips(plan):
    return {s['id']:{'path':'/fixture/'+s['id']+'.mp4','fps':plan['fps'],
                    'normalized_frames':s['output_frames']+12,'in_frame':6,
                    'technical_valid':True,'fidelity_verified':True,'role_verified':True,
                    'borders_verified':True,'source_fingerprint':plan['source_fingerprint'],
                    'render_fingerprint':plan['render_fingerprint']}
            for s in plan['shots']}


class CreativeTests(unittest.TestCase):
    def setUp(self):
        for target in ('socket.socket', 'socket.create_connection', 'urllib.request.urlopen'):
            p = patch(target, side_effect=AssertionError('no network in planning'))
            p.start();self.addCleanup(p.stop)

    def test_thirty_seconds_exactly_720_frames(self):
        self.assertEqual(allocate_frames(), [96,120,264,120,120])
        for seconds in (10,15,27.3,30,60):
            self.assertEqual(sum(allocate_frames(seconds)), round(seconds*24))

    def test_bad_duration_and_fps(self):
        for value in (float('nan'),-1,0,100,True,'30'):
            with self.assertRaises(ValueError): allocate_frames(value)
        for value in (0,61,True,23.976):
            with self.assertRaises(ValueError): allocate_frames(30,value)

    def test_pure_deterministic_plan(self):
        before=copy.deepcopy(PRODUCT)
        a=build_film_plan(PRODUCT);b=build_film_plan(PRODUCT)
        self.assertEqual(a,b);self.assertEqual(PRODUCT,before)
        self.assertFalse(a['execution_authorized']);self.assertEqual(a['model_calls'],0)

    def test_missing_frames_block_all_submissions(self):
        p=build_film_plan(PRODUCT,capabilities=CAPS)
        self.assertTrue(all(s['status']=='blocked' for s in p['shots']))

    def test_verified_matching_frames_are_ready(self):
        p=build_film_plan(PRODUCT,frames=catalog(),capabilities=CAPS)
        self.assertTrue(all(s['status']=='ready' for s in p['shots']))
        self.assertEqual([s['request_seconds'] for s in p['shots']],[5,5,12,5,5])

    def test_full_body_named_detail_is_not_macro(self):
        frames=catalog();frames[0].update(framing='full',presentation='worn')
        p=build_film_plan(PRODUCT,frames=frames,capabilities=CAPS)
        self.assertEqual(p['shots'][0]['status'],'blocked')

    def test_wrong_product_frame_blocked(self):
        frames=catalog();frames[2]['product_id']='another'
        self.assertEqual(build_film_plan(PRODUCT,frames=frames,capabilities=CAPS)['shots'][2]['status'],'blocked')

    def test_unverified_role_does_not_pass(self):
        frames=catalog();frames[1]['approved']=False
        self.assertEqual(build_film_plan(PRODUCT,frames=frames,capabilities=CAPS)['shots'][1]['status'],'blocked')

    def test_fabricated_provenance_rejected(self):
        frames=catalog();frames[0]['source_ids']=['not-a-source']
        self.assertEqual(build_film_plan(PRODUCT,frames=frames,capabilities=CAPS)['shots'][0]['status'],'blocked')

    def test_no_forced_morph_between_different_scenes(self):
        frames=catalog();last=dict(frames[2],id='last',scene_id='different',continuity_verified=True)
        p=build_film_plan(PRODUCT,frames=frames+[last],capabilities=CAPS)
        self.assertIsNone(p['shots'][2]['last_frame_id'])
        self.assertEqual(p['shots'][2]['transition_after'],'cut')

    def test_same_scene_verified_last_frame_allowed(self):
        frames=catalog();last=dict(frames[2],id='last',continuity_verified=True)
        p=build_film_plan(PRODUCT,frames=frames+[last],capabilities=CAPS)
        self.assertEqual(p['shots'][2]['last_frame_id'],'last')

    def test_unknown_capabilities_not_assumed(self):
        p=build_film_plan(PRODUCT,frames=catalog(),capabilities=dict(CAPS,verified=False))
        self.assertTrue(all(s['status']=='blocked' for s in p['shots']))

    def test_competition_never_assumes_ffmpeg(self):
        p=build_film_plan(PRODUCT,frames=catalog(),capabilities=CAPS,profile='competition')
        self.assertTrue(all(s['status']=='blocked' for s in p['shots']))

    def test_duplicate_frame_ids_rejected(self):
        f=catalog()
        with self.assertRaises(ValueError): build_film_plan(PRODUCT,frames=f+[f[0]])

    def test_no_softness_or_qc_claim_in_subtitles(self):
        captions=caption_options(fact_ledger(PRODUCT))
        text=' '.join(c['texts']['en'] for c in captions)
        self.assertNotIn('Soft polyester',text)
        self.assertNotIn('checked',text)
        self.assertNotIn('ankle',text)
        self.assertTrue(all(c['evidence_ids'] for c in captions))

    def test_unknown_material_not_guessed(self):
        p=dict(PRODUCT,attributes=[])
        self.assertFalse(any(c['id']=='material' for c in caption_options(fact_ledger(p))))

    def test_six_distinct_image_role_contracts(self):
        from src.creative_plan import IMAGE_ROLES
        briefs=[image_brief(r) for r in IMAGE_ROLES]
        self.assertEqual(len({b['prompt'] for b in briefs}),6)
        self.assertIn('not a full garment',briefs[2]['composition'])
        self.assertEqual(briefs[3]['framing'],'macro')

    def test_edit_frame_ranges_and_caption_gaps(self):
        p=build_film_plan(PRODUCT);e=compile_edit(p,clips(p))
        self.assertTrue(e['ready']);self.assertEqual(e['output_frames'],720)
        for cue in e['captions']:
            shot=next(s for s in p['shots'] if s['id']==cue['shot_id'])
            self.assertGreaterEqual(cue['start_frame'],shot['start_frame'])
            self.assertLessEqual(cue['end_frame'],shot['end_frame'])
        self.assertTrue(format_timeline_subtitles(e,vtt=True).startswith('WEBVTT'))
        self.assertIn('00:00:29,750',format_timeline_subtitles(e))

    def test_short_shot_not_looped_to_hit_thirty_seconds(self):
        p=build_film_plan(PRODUCT);c=clips(p);c['product']['normalized_frames']=30
        e=compile_edit(p,c);self.assertFalse(e['ready'])
        with self.assertRaises(ValueError):format_timeline_subtitles(e)

    def test_missing_or_reused_clip_rejected(self):
        p=build_film_plan(PRODUCT);c=clips(p);del c['proof']
        self.assertFalse(compile_edit(p,c)['ready'])
        c=clips(p);c['cta']['path']=c['hook']['path']
        self.assertFalse(compile_edit(p,c)['ready'])

    def test_changed_source_invalidates_review(self):
        p=build_film_plan(PRODUCT);c=clips(p);c['cta']['source_fingerprint']='old'
        self.assertFalse(compile_edit(p,c)['ready'])

    def test_edge_panel_issue_blocks_finish(self):
        p=build_film_plan(PRODUCT);c=clips(p);c['product']['borders_verified']=False
        self.assertFalse(compile_edit(p,c)['ready'])

    def test_untrusted_timeline_rejected(self):
        p=build_film_plan(PRODUCT);p['shots'][1]['start_frame']+=1
        with self.assertRaises(ValueError):compile_edit(p,clips(p))

    def test_all_languages_caption_frames_match(self):
        p=build_film_plan(PRODUCT)
        edits=[compile_edit(p,clips(p),language=l) for l in ('en','ko','pt')]
        self.assertTrue(all(e['ready'] for e in edits))
        for e in edits:self.assertEqual(e['duration_seconds'],30)

    def test_finish_command_uses_frame_trims_not_stream_copy(self):
        p=build_film_plan(PRODUCT);e=compile_edit(p,clips(p));cmd=finish.command(e,'out.mp4')
        self.assertIn('-frames:v',cmd);self.assertIn('720',cmd)
        self.assertNotIn('copy',cmd);self.assertNotIn('-shortest',cmd)
        graph=cmd[cmd.index('-filter_complex')+1]
        self.assertIn('trim=start_frame=',graph);self.assertNotIn('drawbox',graph)

    def test_subtitle_path_cannot_inject_filter(self):
        p=build_film_plan(PRODUCT);e=compile_edit(p,clips(p))
        with self.assertRaises(ValueError):finish.command(e,'out.mp4',burn_subtitles='a;movie=other')


if __name__=='__main__':unittest.main()
