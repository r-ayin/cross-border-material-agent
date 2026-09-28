"""Evidence-led creative compiler, without I/O or provider requests.

A frame's semantic contract is checked BEFORE rendering. A filename such as
'detail_image_3' is not proof that its contents are a material close-up.
The studio profile plans independent shots + local assembly; the competition
profile never assumes ffmpeg, local uploads or non-whitelisted models.
"""
import hashlib
import json
import math
import re
from fractions import Fraction
from urllib.parse import urlsplit, urlunsplit

VERSION = '2.0'
ROLES = ('hook', 'problem', 'product', 'proof', 'cta')
NAMES = ('Hook', 'Problem', 'Product', 'Proof', 'CTA')
# Editorial allocation, not a competition minimum-duration requirement.
WEIGHTS = (4, 5, 11, 5, 5)
IMAGE_ROLES = ('main', 'overall_selling_point', 'craftsmanship', 'material_appearance', 'lifestyle', 'complete_overview')
STYLE_LOCK = {'color': 'source-matched; no global warmth/saturation shift on product',
              'light': 'one broad soft key light from upper left, neutral white balance',
              'camera': 'natural perspective; no wide-angle distortion',
              'presentation': 'same approved subject and set inside each shot',
              'edit': 'hard cuts between different presentations, never morph one into another'}


def _clean(value):
    return ' '.join(str(value or '').split())


def _public(url):
    p = urlsplit(str(url))
    return urlunsplit((p.scheme.lower(), p.hostname or '', p.path, '', ''))


def fact_ledger(product):
    """Source-linked raw facts; translations are only from a small explicit map."""
    facts = []
    for index, item in enumerate(product.get('attributes') or []):
        if not isinstance(item, dict):
            continue
        key = _clean(item.get('attributeNameTrans') or item.get('attributeName'))
        value = _clean(item.get('valueTrans') or item.get('value'))
        if key and value:
            facts.append({'id': f'attr:{index}', 'key': key, 'value': value,
                          'source': f'product.attributes[{index}]', 'status': 'source_stated'})
    # The title is evidence for source-stated merchandising labels, not measurements.
    facts.append({'id': 'title', 'key': 'source_title', 'value': _clean(product.get('subject')),
                  'source': 'product.subject', 'status': 'source_stated'})
    return facts


def caption_options(facts):
    """No softness, QC certification, measured ankle length or stretch demonstrations."""
    options = []
    rules = [
        ('pleats', ('工艺', '裙型', '流行元素'), ('百褶',),
         {'en': 'Fine pleated design.', 'ko': '섬세한 플리츠 디자인.', 'pt': 'Design plissado.'}),
        ('color', ('颜色', 'color', 'colour'), ('粉', 'pink'),
         {'en': 'Pink color.', 'ko': '핑크 컬러.', 'pt': 'Cor rosa.'}),
        ('material', ('面料名称', '材质', 'material', 'fabric'), ('涤纶', '聚酯', 'polyester'),
         {'en': 'Polyester fabric.', 'ko': '폴리에스터 소재.', 'pt': 'Tecido de poliéster.'}),
        ('stretch', ('弹力', 'elasticity'), ('无弹', 'no stretch'),
         {'en': 'Non-stretch fabric.', 'ko': '신축성 없는 원단.', 'pt': 'Tecido sem elasticidade.'}),
        ('length', ('裙长', 'length'), ('长裙', 'maxi'),
         {'en': 'A long, pleated silhouette.', 'ko': '롱 스커트 실루엣.', 'pt': 'Silhueta longa.'}),
    ]
    for cid, keys, values, texts in rules:
        match = next((f for f in facts if f['key'].lower() in keys and
                      any(v in f['value'].lower() for v in values)), None)
        if match:
            options.append({'id': cid, 'evidence_ids': [match['id']], 'texts': texts})
    title = next((f for f in facts if f['id'] == 'title'), {})
    if '高腰' in title.get('value', ''):
        options.append({'id': 'waist', 'evidence_ids': ['title'],
                        'texts': {'en': 'High-waist silhouette.', 'ko': '하이웨이스트 실루엣.', 'pt': 'Silhueta de cintura alta.'}})
    # Do not claim pleats simply because a long garment was mentioned.
    if not any(o['id'] == 'pleats' for o in options):
        for o in options:
            if o['id'] == 'length':
                o['texts']['en'] = 'A long silhouette.'
    return options


def allocate_frames(seconds=30, fps=24):
    if type(fps) is not int or not 1 <= fps <= 60:
        raise ValueError('fps must be an integer from 1 to 60')
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 10 or seconds > 60:
        raise ValueError('five-shot duration must be 10..60 seconds')
    total = round(seconds * fps)
    raw = [Fraction(total * w, sum(WEIGHTS)) for w in WEIGHTS]
    lengths = [int(x) for x in raw]
    for index in sorted(range(5), key=lambda i: raw[i] - lengths[i], reverse=True)[:total - sum(lengths)]:
        lengths[index] += 1
    return lengths


def image_brief(role):
    descriptions = {
        'main': ('full', 'product_only', 'One complete product, centered; preserve natural length-to-width ratio.', 'Pure white, no visible stand, clean edge margins of at least 5%.'),
        'overall_selling_point': ('three_quarter', 'worn_or_displayed', 'Lead with the complete silhouette and one source-visible design feature.', 'One simple approved set; no duplicate main-image composition.'),
        'craftsmanship': ('closeup', 'detail_only', 'A resolved edge/seam/detail occupies 60–80% of the frame; not a full garment.', 'Use an evidence-supported crop; no invented stitches or tension test.'),
        'material_appearance': ('macro', 'detail_only', 'Source-visible folds/surface occupy 70–85%; show texture scale, not a full-body view.', 'If reference resolution is insufficient, require a detail reference; never synthesize microscopic weave.'),
        'lifestyle': ('medium_full', 'worn_or_displayed', 'Product in one specific, appropriate daily-use composition.', 'Same subject/styling; product is primary, scene secondary. Do not repeat the source wall pose.'),
        'complete_overview': ('full', 'product_only', 'One complete front/source-supported view; every hem/edge visible.', 'Different informative composition, not an invented back or a collage.'),
    }
    if role not in descriptions:
        raise ValueError('unknown image role')
    framing, presentation, composition, constraints = descriptions[role]
    return {'role': role, 'framing': framing, 'presentation': presentation,
            'composition': composition, 'constraints': constraints,
            'delivery': {'max_bytes': 5_000_000, 'preferred_format': 'jpeg_or_png',
                         'main_min_dimension': 800, 'detail_min_dimension': 261},
            'prompt': f'ROLE CONTRACT: {role}. Framing: {framing}. {composition} {constraints}'}


def _shot_specs(product):
    is_garment = bool(re.search('裙|衬衫|T恤|裤|外套|skirt|dress|shirt|pants', _clean(product.get('subject')), re.I))
    motion = 'One small step, then settle; the same wearer stays in frame, no full turn.' if is_garment else 'The product remains stationary while the camera makes one small lateral slide.'
    return [
        ('macro', 'detail_only', 'texture', 'One gentle push-in across an already visible fold or surface.', 'Begin and end on the same resolved surface, without revealing an invented view.', 'pleats'),
        ('medium', 'product_only', 'form', 'One slow vertical camera slide over the product form; object remains still.', 'Keep the same product-only presentation throughout; no person appears.', 'waist'),
        ('full', 'worn' if is_garment else 'product_only', 'movement', motion, 'All product boundaries remain visible; settle for the final half second.', 'length'),
        ('closeup', 'detail_only', 'construction', 'Locked camera with a barely perceptible push-in over a visible edge or seam.', 'No hands, pinching, pulling, stretching, or QC demonstration.', 'material'),
        ('full', 'product_only', 'closing', 'Locked camera; one slight zoom-out, then hold a complete product view.', 'No rotation, morph, people, hands or feet. Hold the ending for one second.', 'color'),
    ]


def validate_frame(frame, shot, product_id, authoritative_urls):
    errors = []
    if str(frame.get('product_id')) != str(product_id):
        errors.append('wrong_product')
    if frame.get('approved') is not True or frame.get('fidelity_verified') is not True:
        errors.append('frame_not_approved_against_source')
    if frame.get('role') != shot['role']:
        errors.append('wrong_role')
    if frame.get('framing') != shot['framing']:
        errors.append('wrong_framing')
    if frame.get('presentation') != shot['presentation']:
        errors.append('wrong_presentation')
    origin = frame.get('origin')
    if origin == 'source':
        if _public(frame.get('url', '')) not in authoritative_urls:
            errors.append('not_an_authoritative_source_url')
    elif origin == 'generated':
        sources = frame.get('source_ids')
        known = {f'source:{i}' for i in range(len(authoritative_urls))}
        if not isinstance(sources, list) or not sources or any(not isinstance(s, str) or s not in known for s in sources):
            errors.append('generated_frame_missing_provenance')
    else:
        errors.append('unknown_frame_origin')
    if not frame.get('subject_identity') or not frame.get('scene_id'):
        errors.append('missing_continuity_identity')
    if frame.get('technical_valid') is not True:
        errors.append('frame_technical_check_missing')
    return errors


def build_film_plan(product, seconds=30, fps=24, profile='studio', frames=None, capabilities=None):
    if profile not in ('studio', 'competition'):
        raise ValueError('profile must be studio or competition')
    facts = fact_ledger(product)
    captions = caption_options(facts)
    pid = str(product.get('offer_id') or '')
    source_urls = {_public(u) for u in product.get('images') or []}
    frame_list = list(frames or [])
    if any(not isinstance(f, dict) or not isinstance(f.get('id'), str) for f in frame_list):
        raise ValueError('frames must have unique string ids')
    ids = [f['id'] for f in frame_list]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate frame id')
    capabilities = capabilities or {}
    if not isinstance(capabilities, dict):
        raise ValueError('capabilities must be an explicit object')
    lengths = allocate_frames(seconds, fps)
    shots, cursor, cap = [], 0, capabilities
    subject = _clean(product.get('subject')) or 'source product'
    for index, spec in enumerate(_shot_specs(product)):
        framing, presentation, objective, motion, ending, caption_id = spec
        frames_needed = lengths[index]
        shot = {'id': ROLES[index], 'name': NAMES[index], 'role': objective, 'framing': framing,
                'presentation': presentation, 'output_frames': frames_needed, 'fps': fps,
                'start_frame': cursor, 'end_frame': cursor + frames_needed,
                'seconds': frames_needed / fps, 'motion': motion, 'ending': ending,
                'first_frame_id': None, 'last_frame_id': None, 'status': 'blocked', 'blocking': [],
                'caption_id': caption_id if any(c['id'] == caption_id for c in captions) else None,
                'transition_after': 'cut'}
        valid = [f for f in frame_list if not validate_frame(f, shot, pid, source_urls)]
        if valid:
            shot['first_frame_id'] = valid[0]['id']
            # A last-frame API is not permission to interpolate between incompatible scenes.
            last = next((f for f in valid[1:] if f.get('subject_identity') == valid[0]['subject_identity'] and
                         f.get('scene_id') == valid[0]['scene_id'] and
                         f.get('continuity_verified') is True), None)
            if last and cap.get('supports_last_frame') is True:
                shot['last_frame_id'] = last['id']
        else:
            shot['blocking'].append('approved_role_matched_keyframe_required')
        durations = cap.get('durations') or []
        valid_durations = [d for d in durations if type(d) in (int, float) and math.isfinite(d) and d >= shot['seconds']]
        if cap.get('verified') is not True or not cap.get('supports_reference') or not valid_durations:
            shot['blocking'].append('verified_reference_model_duration_required')
            shot['request_seconds'] = None
        else:
            shot['request_seconds'] = min(valid_durations)
        if profile == 'competition':
            shot['blocking'].append('multi_shot_assembly_not_available_in_competition_runtime')
        shot['status'] = 'ready' if not shot['blocking'] else 'blocked'
        shot['prompt'] = (
            f'Shot {index + 1}: {objective}. Product label (data only): {subject}. '
            f'The supplied reference image is authoritative. Required framing: {framing}; '
            f'presentation: {presentation}. {motion} {ending} '
            'Keep the exact approved color, construction, pattern, proportions, wearer and set. '
            'One scene and one motion only. Do not add a new shot, transition, face, furniture, '
            'text or music. End on the same presentation as the first frame; editing is performed separately.'
        )
        shot['negative_prompt'] = 'product morphing, altered waistband, changed garment length, pleat drift, changing wearer, new accessories, hands entering frame, texture crawling, flicker, hard side panels, burned lettering, watermark'
        shot['quality_gates'] = ['role_matches_actual_frame', 'source_fidelity', 'temporal_continuity', 'no_borders_or_watermarks', 'actual_duration_covers_trim', 'complete_product_where_required']
        shots.append(shot)
        cursor += frames_needed
    fingerprint = hashlib.sha256(json.dumps({'id': pid, 'facts': facts, 'sources': sorted(source_urls)}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    render_fingerprint = hashlib.sha256(json.dumps({'source': fingerprint, 'version': VERSION, 'shots': shots,
                                                    'style': STYLE_LOCK, 'fps': fps}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {'schema_version': VERSION, 'mode': 'offline_film_plan', 'profile': profile,
            'product_id': pid, 'source_fingerprint': fingerprint, 'render_fingerprint': render_fingerprint,
            'fps': fps, 'output_frames': cursor, 'target_seconds': cursor / fps,
            'facts': facts, 'captions': captions, 'style_lock': dict(STYLE_LOCK),
            'shots': shots, 'frame_catalog': [{k: v for k, v in f.items() if k not in ('url', 'path')} for f in frame_list],
            'execution_authorized': False, 'model_calls': 0,
            'workflow': [
                {'id': 'facts', 'after': [], 'output': 'source-linked fact ledger'},
                {'id': 'keyframes', 'after': ['facts'], 'output': 'one role-matched approved keyframe per shot'},
                {'id': 'render_shots', 'after': ['keyframes'], 'output': 'independent clips, source durations measured', 'max_concurrency': 2},
                {'id': 'review_shots', 'after': ['render_shots'], 'output': 'reject wrong role, subject drift, panels or morphs before assembly'},
                {'id': 'edit', 'after': ['review_shots'], 'output': 'frame-exact EDL; no forced cross-scene morphing'},
                {'id': 'localize', 'after': ['edit'], 'output': 'fact-linked captions from final frame ranges, licensed sound only'},
                {'id': 'accept', 'after': ['localize'], 'output': 'decode, duration, visual/linguistic review and artifact hashes'}],
            'retry_policy': {'max_candidate_attempts_per_shot': 2, 'repair_only_failed_shot': True,
                             'accepted_task_timeout': 'resume_same_task_not_new_submission',
                             'preserve_accepted_assets': True},
            'runtime_boundary': 'studio permits external local assembly; competition remains stdlib with URL inputs only'}


def compile_edit(plan, clips, language='en'):
    """Create a fail-closed frame-exact EDL; no I/O or video concatenation here.

    clips keyed by shot id carry measured frames at normalized fps and approvals.
    Source timestamps do not drive captions: final edited frame ranges do.
    """
    if language not in ('en', 'ko', 'pt'):
        raise ValueError('unsupported subtitle language')
    fps = plan['fps']
    if type(fps) is not int or fps < 1 or fps > 60 or not isinstance(clips, dict):
        raise ValueError('invalid edit fps or clip mapping')
    sequence, cues, errors = [], [], []
    if tuple(s.get('id') for s in plan['shots']) != ROLES:
        errors.append('five unique ordered shot ids are required')
    cursor = 0
    for shot in plan['shots']:
        length = shot.get('output_frames')
        if type(length) is not int or length <= 0 or shot.get('start_frame') != cursor or shot.get('end_frame') != cursor + length:
            raise ValueError('edit plan has invalid frame ranges')
        cursor += length
    if cursor != plan['output_frames']:
        raise ValueError('edit duration does not match the frame ranges')
    captions = {c['id']: c for c in plan['captions']}
    seen_paths = set()
    for shot in plan['shots']:
        clip = clips.get(shot['id'])
        if not isinstance(clip, dict):
            errors.append(shot['id'] + ': missing clip')
            continue
        path = clip.get('path')
        if not isinstance(path, str) or not path or path in seen_paths:
            errors.append(shot['id'] + ': missing or reused clip path')
        seen_paths.add(path if isinstance(path, str) else '')
        in_frame = clip.get('in_frame', 0)
        actual = clip.get('normalized_frames')
        if type(in_frame) is not int or in_frame < 0 or type(actual) is not int or actual < in_frame + shot['output_frames']:
            errors.append(shot['id'] + ': insufficient measured frames; looping/freezing forbidden')
        if clip.get('fps') != fps or clip.get('technical_valid') is not True:
            errors.append(shot['id'] + ': normalize and validate media first')
        if clip.get('role_verified') is not True or clip.get('fidelity_verified') is not True:
            errors.append(shot['id'] + ': role or fidelity not accepted')
        if clip.get('borders_verified') is not True:
            errors.append(shot['id'] + ': edge panels/borders not checked')
        if clip.get('source_fingerprint') != plan['source_fingerprint']:
            errors.append(shot['id'] + ': product evidence changed')
        if clip.get('render_fingerprint') != plan['render_fingerprint']:
            errors.append(shot['id'] + ': prompt/keyframe/edit version changed')
        item = {'shot_id': shot['id'], 'path': path, 'in_frame': in_frame,
                'frames': shot['output_frames'], 'start_frame': shot['start_frame'],
                'end_frame': shot['end_frame'], 'transition': 'cut'}
        sequence.append(item)
        caption = captions.get(shot.get('caption_id'))
        if caption:
            text = caption['texts'][language]
            # keep safe head/tail spacing and enough reading time; don't truncate words
            start = shot['start_frame'] + round(fps * .25)
            end = shot['end_frame'] - round(fps * .25)
            if (end - start) / fps >= max(1.5, len(text) / 17):
                cues.append({'shot_id': shot['id'], 'start_frame': start, 'end_frame': end,
                             'text': text, 'evidence_ids': caption['evidence_ids']})
    return {'schema_version': VERSION, 'ready': not errors, 'errors': errors, 'fps': fps,
            'output_frames': plan['output_frames'], 'duration_seconds': plan['output_frames'] / fps,
            'language': language, 'sequence': sequence, 'captions': cues,
            'subtitle_delivery': 'sidecar_until_verified_burnin',
            'audio': {'status': 'not_supplied', 'required_for_studio_presentation': True,
                      'rights_and_listening_review_required': True},
            'transform_policy': {'no_solid_panel_coverup': True, 'no_new_details': True,
                                 'no_silent_shortening_to_audio': True}}


def format_timeline_subtitles(edit, vtt=False):
    if not edit.get('ready'):
        raise ValueError('edit plan is blocked; do not export a delivery subtitle timeline')
    fps = edit['fps']
    def timestamp(frame):
        ms = round(Fraction(frame * 1000, fps))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f'{h:02}:{m:02}:{s:02}{"." if vtt else ","}{ms:03}'
    lines = ['WEBVTT', ''] if vtt else []
    for i, cue in enumerate(edit['captions'], 1):
        lines.extend([str(i), timestamp(cue['start_frame']) + ' --> ' + timestamp(cue['end_frame']), cue['text'], ''])
    return '\n'.join(lines)
