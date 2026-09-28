#!/usr/bin/env python3
"""One authorized image + one authorized video. No retries, no model fallback.
Run on the existing dsh VM. Credentials never enter output files.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HOST = 'token-plan.cn-beijing.maas.aliyuncs.com'
BASE = 'https://' + HOST + '/api/v1'
ENV_FILE = Path('/home/ubuntu/coding/跨境比赛项目/session-archive-backup/scripts/ds-test.env')
PRODUCT_FILE = Path('/home/ubuntu/coding/cross-border-material-agent/data/Task_Data/Data_for_Users(2)/product_info/product_8822221153828.json')


def safe(text):
    text = re.sub(r'sk-[A-Za-z0-9._-]+', '[REDACTED]', str(text))
    return re.sub(r'(https?://[^\s?]+)\?[^\s]+', r'\1?[QUERY_REMOVED]', text)


def load_key():
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip().removeprefix('export ')
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            parsed = shlex.split(v)
            env[k.strip()] = parsed[0] if parsed else ''
    if urllib.parse.urlsplit(env.get('DASHSCOPE_BASE_URL', '')).hostname != HOST:
        raise ValueError('unexpected configured provider; stopped')
    key = env.get('DASHSCOPE_API_KEY', '')
    if not key:
        raise ValueError('no API credential configured')
    return key


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('provider redirect refused to protect Authorization')


def write_json(path, obj):
    tmp = path.with_suffix(path.suffix + '.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def provider(path, key, payload=None, asynchronous=False):
    headers = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}
    if asynchronous:
        headers['X-DashScope-Async'] = 'enable'
    req = urllib.request.Request(BASE + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers, method='POST' if payload is not None else 'GET')
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=180 if payload is not None else 30) as response:
            raw = response.read(2_000_000)
            return response.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = exc.read(10000).decode('utf-8', 'replace')
        try:
            obj = json.loads(body)
        except ValueError:
            obj = {'message': safe(body[:500])}
        return exc.code, obj


def extract_url(obj):
    out = obj.get('output') or {}
    if out.get('video_url'):
        return out['video_url']
    for item in out.get('results') or []:
        if item.get('url'):
            return item['url']
    for choice in out.get('choices') or []:
        for item in (choice.get('message') or {}).get('content') or []:
            if isinstance(item, dict):
                for key in ('image', 'video', 'url'):
                    if item.get(key):
                        return item[key]
    return None


def download(url, target, max_bytes):
    if urllib.parse.urlsplit(url).scheme != 'https':
        raise ValueError('artifact must be HTTPS')
    total = 0
    temp = target.with_suffix(target.suffix + '.part')
    with urllib.request.urlopen(url, timeout=60) as response, temp.open('wb') as f:
        while True:
            chunk = response.read(256 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError('artifact exceeds download cap')
            f.write(chunk)
    if not total:
        raise ValueError('empty artifact')
    os.replace(temp, target)
    return {'file': target.name, 'bytes': total, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}


def response_summary(obj):
    out = obj.get('output') or {}
    return {'request_id': obj.get('request_id'), 'code': obj.get('code'),
            'message': safe(obj.get('message') or out.get('message') or ''),
            'task_id': out.get('task_id'), 'task_status': out.get('task_status'),
            'usage': obj.get('usage')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['image', 'video', 'poll', 'download'])
    parser.add_argument('--output', required=True)
    parser.add_argument('--release', required=True)
    args = parser.parse_args()
    root = Path(args.output)
    if not root.is_dir():
        raise ValueError('output directory must already exist')
    release = json.loads(Path(args.release).read_text())
    if release.get('provider_host') != HOST or release.get('max_generation_posts') != 2:
        raise ValueError('release does not match fixed provider/budget')
    key = load_key()
    state_file = root/'private-task-state.json'
    state = json.loads(state_file.read_text()) if state_file.exists() else {'posts': 0}
    if args.stage in ('image', 'video'):
        if state.get(args.stage):
            raise ValueError('stage already attempted; do not resubmit even after failure')
        if state['posts'] >= 2:
            raise ValueError('generation request ceiling reached')
        if args.stage == 'image':
            if release.get('image_authorized') is not True:
                raise ValueError('image stage not released')
            product = json.loads(PRODUCT_FILE.read_text())['ret']['result']['result']
            refs = product['productImage']['images'][:2]
            payload = {'model': 'wan2.7-image-pro', 'input': {'messages': [{'role': 'user', 'content':
                [{'image': url} for url in refs] + [{'text': release['keyframe_prompt_en']}]}]},
                'parameters': {'size': '1080*1920', 'n': 1, 'watermark': False}}
            endpoint = '/services/aigc/multimodal-generation/generation'
        else:
            if release.get('video_authorized') is not True or release.get('keyframe_review') != 'accepted':
                raise ValueError('keyframe must be visually reviewed before video submission')
            image = state.get('image') or {}
            if not image.get('artifact_url') or image.get('status') != 'downloaded':
                raise ValueError('approved image URL unavailable')
            payload = {'model': 'happyhorse-1.1-i2v', 'input': {
                'prompt': release['video_prompt_en'],
                'media': [{'type': 'first_frame', 'url': image['artifact_url']}]},
                'parameters': {'duration': 15, 'resolution': '1080P', 'watermark': False}}
            endpoint = '/services/aigc/video-generation/video-synthesis'
        state['posts'] += 1
        state[args.stage] = {'status': 'submission_started', 'model': payload['model'],
                              'submitted_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                              'prompt_sha256': hashlib.sha256(json.dumps(payload['input'],sort_keys=True).encode()).hexdigest()}
        write_json(state_file, state)
        status, obj = provider(endpoint, key, payload, asynchronous=args.stage == 'video')
        record = state[args.stage]
        record.update(http_status=status, response=response_summary(obj))
        record['task_id'] = (obj.get('output') or {}).get('task_id')
        url = extract_url(obj)
        if url:
            record['artifact_url'] = url
            record['status'] = 'ready_to_download'
        elif record['task_id']:
            record['status'] = 'accepted'
        else:
            record['status'] = 'rejected' if status >= 400 or obj.get('code') else 'unknown_outcome'
        write_json(state_file, state)
        print(json.dumps({'stage': args.stage, 'http_status': status, 'status':record['status'],
                          'posts':state['posts'], **response_summary(obj)}, ensure_ascii=False))
        if status >= 400 or record['status'] in ('rejected','unknown_outcome'):
            return 2
    elif args.stage == 'poll':
        name = 'video' if (state.get('video') or {}).get('task_id') else 'image'
        record = state.get(name) or {}
        task_id = record.get('task_id')
        if not task_id or not re.fullmatch(r'[A-Za-z0-9_-]+',task_id):
            raise ValueError('no accepted task to poll')
        deadline = time.monotonic() + 18 * 60
        while time.monotonic() < deadline:
            status,obj = provider('/tasks/'+task_id,key)
            summary = response_summary(obj)
            record['last_poll'] = summary
            url = extract_url(obj)
            task_status = (obj.get('output') or {}).get('task_status')
            if status >= 400:
                record['status'] = 'poll_failed';write_json(state_file,state)
                print(json.dumps({'stage':name,'http_status':status,**summary},ensure_ascii=False));return 3
            if url and (task_status in (None,'SUCCEEDED')):
                record['artifact_url']=url;record['status']='ready_to_download';write_json(state_file,state)
                print(json.dumps({'stage':name,'status':'ready_to_download',**summary},ensure_ascii=False));break
            if task_status in ('FAILED','CANCELED','UNKNOWN'):
                record['status']='failed';write_json(state_file,state)
                print(json.dumps({'stage':name,'status':'failed',**summary},ensure_ascii=False));return 3
            write_json(state_file,state)
            time.sleep(8)
        else:
            print('poll deadline reached; task retained, no resubmission');return 3
    else:
        for name,target,cap in [('image','character_keyframe.png',15_000_000),('video','product_video_raw.mp4',200_000_000)]:
            record=state.get(name) or {}
            if record.get('status')=='ready_to_download' and record.get('artifact_url'):
                metadata=download(record['artifact_url'],root/target,cap)
                record['artifact']=metadata;record['status']='downloaded';write_json(state_file,state)
                print(json.dumps({'stage':name,**metadata},ensure_ascii=False))
    return 0


if __name__=='__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(safe(type(exc).__name__+': '+str(exc)),file=sys.stderr)
        sys.exit(1)
