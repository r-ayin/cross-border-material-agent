#!/usr/bin/env python3
"""通用化 15s 人物短视频生成管线（包装已审计 generate_once.py，sha 锁定）。
阶段: init -> image -> [人工/agent 目检门禁] -> approve -> video -> poll -> download -> qa -> deliver
纪律: 每次运行需 --authorize 文本留痕; 失败不自动重提; 签名URL永不打印; 状态组装全在磁盘。"""
import argparse, hashlib, json, os, pathlib, shutil, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / 'build'
VENDOR = ROOT / 'scripts' / 'vendor' / 'generate_once.py'
TEMPLATES = ROOT / 'docs' / 'prompt-templates-v5.json'
AUDITED_SHA = '6319361572dcdd8ee7eb5ca02a669fc8580716c6ea8f699f496c77aa6e8b01ed'
SCENE_CONSISTENCY = {
    'bedroom': 'the sunlit bedroom background remains stable and unchanged, softly blurred behind her',
    'cafe': 'the cozy cafe interior background remains stable and unchanged, softly blurred behind her',
    'street': 'the city sidewalk background with blurred pedestrians and traffic remains stable and unchanged',
}

def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)

def die(msg):
    print('PIPELINE_ERROR: ' + msg, file=sys.stderr); sys.exit(2)

def load_json(p): return json.loads(pathlib.Path(p).read_text())

def run_dir(args):
    import re as _re
    if not _re.fullmatch(r'[A-Za-z0-9_.-]+', args.run or ''): die('--run 名字符集非法（防命令注入）')
    return BUILD / args.run

def gen(args, stage, allow=()):
    d = run_dir(args)
    got = hashlib.sha256((d / 'generate_once.py').read_bytes()).hexdigest()
    if got != AUDITED_SHA: die('run 目录 generate_once.py sha 漂移: ' + got)
    r = sh(f'cd {d} && python3 generate_once.py {stage} --output . --release execution-release.json', timeout=1500)
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode not in (0, 2, 3) + tuple(allow): die(f'stage {stage} rc={r.returncode}')
    return r.returncode

def cmd_init(a):
    tpl = load_json(TEMPLATES)
    tid = {'T01': 'T01-fullbody-groove', 'T02': 'T02-walk-interactive', 'T03': 'T03-inplace-fallback'}.get(a.template, a.template)
    tier = next((t for t in tpl['tiers'] if t['id'] == tid), None) or die('模板不存在: ' + a.template)
    kf = (tpl.get('keyframe_prompts') or {}).get(a.scene)
    if not kf: die(f'scene {a.scene} 无已定版首帧 prompt（keyframe_prompts 缺失）')
    vp = tier['video_prompt_en']
    for scene, sentence in SCENE_CONSISTENCY.items():
        if scene != a.scene and sentence in vp: vp = vp.replace(sentence, SCENE_CONSISTENCY[a.scene])
    name = a.run or f"pipeline-{a.template}-{a.scene}-{time.strftime('%Y%m%d-%H%M')}"
    import re as _re
    if not _re.fullmatch(r'[A-Za-z0-9_.-]+', name): die('run 名字符集非法（防命令注入）')
    d = BUILD / name
    if d.exists(): die('run dir 已存在: ' + name)
    d.mkdir(parents=True)
    shutil.copy(VENDOR, d / 'generate_once.py')
    got = hashlib.sha256((d / 'generate_once.py').read_bytes()).hexdigest()
    if got != AUDITED_SHA: die('generate_once.py sha 不匹配，禁止运行: ' + got)
    release = {
        'release_version': '1.0', 'scope': f'generalized pipeline {a.template}/{a.scene}',
        'selected_variant': a.template, 'user_authorization': a.authorize,
        'provider_host': 'token-plan.cn-beijing.maas.aliyuncs.com', 'max_generation_posts': 2,
        'image_authorized': True, 'video_authorized': True, 'keyframe_review': 'pending',
        'keyframe_review_record': None, 'automatic_resubmission': False,
        'automatic_model_fallback': False, 'new_music_generation': False,
        'purchase_or_upgrade_authorized': False,
        'budget_basis': '最多1次wan2.7-image-pro+1次happyhorse-1.1-i2v; 失败不自动重提',
        'audit_basis': {'script_sha256': AUDITED_SHA, 'templates_source': str(TEMPLATES.relative_to(ROOT)),
                        'spec_source': 'docs/video-motion-prompt-spec.md', 'scene': a.scene,
                        'main_review': '首帧=keyframe_prompts[' + a.scene + ']; 视频=' + a.template + ' + 场景一致性句'},
        'documentation': ['https://help.aliyun.com/zh/model-studio/text-to-video-prompt'],
        'keyframe_prompt_en': kf, 'video_prompt_en': vp,
    }
    (d / 'execution-release.json').write_text(json.dumps(release, ensure_ascii=False, indent=2) + '\n')
    (d / 'private-task-state.json').write_text('{\n  "posts": 0\n}\n')
    print('INIT_OK run=' + name)

def cmd_image(a):
    rc = gen(a, 'image')
    if rc != 0: die('image 阶段失败，不重提（纪律）')
    gen(a, 'download')
    d = run_dir(a)
    if not (d / 'character_keyframe.png').exists(): die('关键帧文件缺失，download 可能静默失败')
    print('GATE: 目检 ' + str(d / 'character_keyframe.png'))
    print('验收七项: 手机直出感/动作中/背景使用痕迹/普通窗光/偏心或裁切/匀净微光泽肌/保留一个不完美; 另查: 鞋入画/无相机器材穿帮/饰品<=2件/商品保真(裙色/褶/腰band与源商品一致)')
    print('通过后执行: video_pipeline.py approve --run ' + a.run + ' --review-note "<目检结论>"')

def cmd_approve(a):
    d = run_dir(a)
    rel_p, st_p = d / 'execution-release.json', d / 'private-task-state.json'
    rel, st = load_json(rel_p), load_json(st_p)
    if rel.get('keyframe_review') == 'accepted': die('已 approved，禁止重复')
    art = (st.get('image') or {}).get('artifact') or {}
    kf = d / 'character_keyframe.png'
    if not kf.exists(): die('关键帧文件缺失，禁止 approve')
    real_sha = hashlib.sha256(kf.read_bytes()).hexdigest()
    if art.get('sha256') and art['sha256'] != real_sha: die('state sha 与磁盘文件不一致')
    rel['keyframe_review'] = 'accepted'
    rel['keyframe_review_record'] = {'file': 'character_keyframe.png', 'sha256': real_sha,
        'bytes': art.get('bytes'), 'reviewed_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'visual_review': a.review_note, 'adjustments': a.adjustments or '无'}
    rel_p.write_text(json.dumps(rel, ensure_ascii=False, indent=2) + '\n')
    print('APPROVED run=' + a.run)

def cmd_video(a):
    d = run_dir(a)
    if load_json(d / 'execution-release.json').get('keyframe_review') != 'accepted': die('未过目检门禁')
    rc = gen(a, 'video')
    if rc != 0: die('video 提交失败，不重提（纪律）')

def cmd_poll(a):
    rc = gen(a, 'poll', allow=(1,))
    if rc == 1:  # 一过性 SSL EOF 已知模式：允许续跑一次（无新 POST）
        print('poll 中断(已知一过性 SSL EOF 模式)，续跑一次（无新 POST）')
        rc = gen(a, 'poll', allow=(1,))
    if rc != 0: die('poll 失败')

def cmd_download(a):
    gen(a, 'download')

def cmd_qa(a):
    d = run_dir(a); v = d / 'product_video_raw.mp4'
    if not v.exists(): die('无成片')
    p = sh(f"ffprobe -v error -show_entries stream=codec_type,width,height,nb_frames -show_entries format=duration -of json {v}")
    m = json.loads(p.stdout)
    vs = next(s for s in m['streams'] if s['codec_type'] == 'video')
    ok = vs['width'] == 1080 and vs['height'] == 1920 and int(vs.get('nb_frames', 0)) >= 360 and float(m['format']['duration']) >= 15
    (d / 'qa').mkdir(exist_ok=True)
    for t in (2, 6, 10, 14):
        sh(f"ffmpeg -nostdin -v error -y -ss {t} -i {v} -frames:v 1 {d/'qa'/f'f{t}.png'}")
    print('QA_PROBE_OK' if ok else 'QA_PROBE_FAIL', json.dumps(vs))
    print('目检 qa/f2,f6,f10,f14: 三拍齐/裙摆因果链/手指/脚底/脸漂移/裙褶闪烁/背景扭曲/结尾定格')
    if not ok: die('规格不符')

def cmd_deliver(a):
    d = run_dir(a); v = d / 'product_video_raw.mp4'
    if a.dingtalk:
        key = 'pipeline-' + a.run
        self_user = os.environ.get('DINGTALK_SELF_USER')
        if not self_user: die('--dingtalk 需环境变量 DINGTALK_SELF_USER（收件人=用户本人单聊，不入仓库）')
        r = sh(f"cd {d} && dws chat +messages-send --as user --user {self_user} --msg-type video --file product_video_raw.mp4 --idempotency-key {key} --yes --format json")
        print('DINGTALK:', r.stdout.strip()[:200])
        try:
            tid = (json.loads(r.stdout).get('sendReceipt') or {}).get('openTaskId')
            if tid:
                q = sh("dws chat +messages-query-send-status --open-task-id '" + tid + "' --format json")
                print('DINGTALK_STATUS:', q.stdout.strip()[:200])
        except Exception:
            print('DINGTALK_STATUS: parse-skip')
    if a.web:
        tgt = ROOT / 'frontend' / 'assets' / ('run-' + time.strftime('%Y%m%d'))
        tgt.mkdir(parents=True, exist_ok=True)
        shutil.copy(v, tgt / f'product_video_{a.run}.mp4')
        kf = d / 'character_keyframe.png'
        if kf.exists(): shutil.copy(kf, tgt / f'character_keyframe_{a.run}.png')
        print('WEB_ASSETS:', tgt)
    if a.mac:
        tgt = '/mnt/mac/Downloads/pitch-deliveries/' + a.run
        r = sh(f'mkdir -p {tgt} && timeout 120 cp {v} {tgt}/ && timeout 60 cp {d/"character_keyframe.png"} {tgt}/ 2>/dev/null; echo MAC_RC=$?')
        if 'MAC_RC=0' not in r.stdout:
            mt = os.environ.get('MAC_SSH_TARGET')
            if not mt: print('MAC_SCP_SKIP: 需环境变量 MAC_SSH_TARGET'); return
            r2 = sh(f'ssh {mt} "mkdir -p ~/Downloads/pitch-deliveries/{a.run}" && scp -q {v} {d/"character_keyframe.png"} {mt}:Downloads/pitch-deliveries/{a.run}/')
            print('MAC_VIA_SCP')
        else:
            print('MAC_VIA_MOUNT', tgt)

def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest='cmd', required=True)
    i = sp.add_parser('init'); i.add_argument('--template', required=True); i.add_argument('--scene', required=True, choices=['bedroom','cafe','street']); i.add_argument('--authorize', required=True); i.add_argument('--run'); i.set_defaults(fn=cmd_init)
    for name, fn in (('image', cmd_image), ('video', cmd_video), ('poll', cmd_poll), ('download', cmd_download), ('qa', cmd_qa)):
        s = sp.add_parser(name); s.add_argument('--run', required=True); s.set_defaults(fn=fn)
    ap = sp.add_parser('approve'); ap.add_argument('--run', required=True); ap.add_argument('--review-note', required=True); ap.add_argument('--adjustments'); ap.set_defaults(fn=cmd_approve)
    dl = sp.add_parser('deliver'); dl.add_argument('--run', required=True); dl.add_argument('--dingtalk', action='store_true'); dl.add_argument('--web', action='store_true'); dl.add_argument('--mac', action='store_true'); dl.set_defaults(fn=cmd_deliver)
    a = p.parse_args()
    a.fn(a)

if __name__ == '__main__':
    main()
