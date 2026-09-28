#!/usr/bin/env python3
"""Studio-only local finishing. No provider access; not part of the contest ZIP.

Inputs: a creative_plan blueprint and reviewed clip manifest with per-file hashes.
Without --render only produce a dry-run EDL/command on stdout. Actual media are
probed before rendering and outputs are created in a NEW directory, never over
source clips. Role/fidelity/border judgments are caller-reviewed, not inferred.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'agent'))
from src.creative_plan import compile_edit, format_timeline_subtitles


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def ass_subtitles(edit):
    """Explicit 1080px layout avoids SRT/libass implicit 384x288 font scaling."""
    if not edit['ready']:
        raise ValueError('blocked edit')
    header = ('[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1080\nWrapStyle: 0\n\n'
              '[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
              'Style: Default,Arial,36,&H00FFFFFF,&H00FFFFFF,&H00191919,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,2,72,72,64,1\n\n'
              '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
    def ts(frame):
        cs=round(Fraction(frame*100,edit['fps']))
        h,cs=divmod(cs,360000);m,cs=divmod(cs,6000);s,cs=divmod(cs,100)
        return f'{h}:{m:02}:{s:02}.{cs:02}'
    lines=[]
    for cue in edit['captions']:
        # Text is a caption, never ASS override markup.
        text=cue['text'].replace('\\', '/').replace('{','(').replace('}',')').replace('\n',' ')
        lines.append(f"Dialogue: 0,{ts(cue['start_frame'])},{ts(cue['end_frame'])},Default,,0,0,0,,{text}")
    return header+'\n'.join(lines)+'\n'


def command(edit, output, audio=None, burn_subtitles=None):
    if not edit['ready']:
        raise ValueError('cannot render a blocked EDL')
    fps = edit['fps']
    args = ['ffmpeg', '-nostdin', '-n', '-v', 'error', '-threads', '1', '-filter_complex_threads', '1']
    chains = []
    for i, clip in enumerate(edit['sequence']):
        args.extend(['-i', clip['path']])
        # Neutral letterboxing is a visible, explicit layout operation; never
        # paint over generated edge artifacts with time-windowed drawbox overlays.
        chains.append(f'[{i}:v]fps={fps},scale=1080:1080:force_original_aspect_ratio=decrease,'
                      f'pad=1080:1080:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1,'
                      f'trim=start_frame={clip["in_frame"]}:end_frame={clip["in_frame"]+clip["frames"]},'
                      f'setpts=PTS-STARTPTS[v{i}]')
    n = len(edit['sequence'])
    chains.append(''.join(f'[v{i}]' for i in range(n)) + f'concat=n={n}:v=1:a=0[cut]')
    if burn_subtitles:
        if not edit.get('captions'):
            raise ValueError('no readable source-grounded captions to burn; use clean output or revise the edit')
        # Caller uses a fixed simple filename in a new, local working directory.
        if burn_subtitles != 'captions.ass':
            raise ValueError('subtitle filter accepts only the generated local captions.ass')
        chains.append('[cut]subtitles=captions.ass[vout]')
    else:
        chains.append('[cut]null[vout]')
    duration = edit['output_frames'] / fps
    if audio:
        args.extend(['-i', audio])
        chains.append(f'[{n}:a]aresample=48000,volume=0.25,apad,atrim=duration={duration:.6f},'
                      f'afade=t=out:st={max(0,duration-0.8):.6f}:d=0.8[aout]')
    args.extend(['-filter_complex', ';'.join(chains), '-map', '[vout]'])
    if audio:
        args.extend(['-map', '[aout]', '-c:a', 'aac', '-b:a', '128k'])
    args.extend(['-c:v', 'libx264', '-threads', '1', '-preset', 'medium', '-crf', '18',
                 '-pix_fmt', 'yuv420p', '-r', str(fps), '-frames:v', str(edit['output_frames']),
                 '-t', f'{duration:.6f}', '-movflags', '+faststart', str(output)])
    return args


def probe(path):
    obj = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                     '-show_format', '-of', 'json', str(path)], timeout=30))
    streams = obj.get('streams') or []
    video = next((s for s in streams if s.get('codec_type') == 'video'), None)
    if not video:
        raise ValueError('missing video stream: ' + str(path))
    return video, obj


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blueprint', required=True)
    p.add_argument('--clips', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--language', choices=['en', 'ko', 'pt'], default='en')
    p.add_argument('--render', action='store_true')
    p.add_argument('--burn-subtitles', action='store_true')
    args = p.parse_args()
    blueprint = json.loads(Path(args.blueprint).read_text())
    manifest = json.loads(Path(args.clips).read_text())
    clips = manifest['clips']
    edit = compile_edit(blueprint, clips, args.language)
    if not edit['ready']:
        print(json.dumps(edit, ensure_ascii=False, indent=2))
        return 2
    audio_info = manifest.get('audio') or {}
    audio = audio_info.get('path')
    if audio and (audio_info.get('usage_authorized') is not True or audio_info.get('listening_reviewed') is not True):
        raise ValueError('audio usage and listening review must be explicitly recorded')
    output_dir = Path(args.output_dir).resolve()
    argv = command(edit, 'product_video.mp4', str(Path(audio).resolve()) if audio else None,
                   'captions.ass' if args.burn_subtitles else None)
    if not args.render:
        print(json.dumps({'dry_run': True, 'edit': edit, 'command': argv, 'output_dir': str(output_dir),
                          'rendered': False, 'network_calls': 0}, ensure_ascii=False, indent=2))
        return 0
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise ValueError('studio rendering requires installed ffmpeg/ffprobe; contest runtime cannot use it')
    if output_dir.exists():
        raise ValueError('output directory already exists; choose a fresh destination')
    if not output_dir.parent.is_dir():
        raise ValueError('output parent directory does not exist')
    # Verify the exact reviewed files and measured timeline before any render.
    for clip in clips.values():
        path = Path(clip['path']).resolve()
        if path.is_symlink() or not path.is_file() or digest(path) != clip.get('sha256'):
            raise ValueError('review hash mismatch: ' + str(path))
        video, _ = probe(path)
        duration = Fraction(str(video.get('duration') or 0))
        available = int(duration * blueprint['fps'])
        if abs(available - clip['normalized_frames']) > 1:
            raise ValueError('measured frame count changed: ' + str(path))
        clip['path'] = str(path)
    if audio and digest(audio) != audio_info.get('sha256'):
        raise ValueError('audio review hash mismatch')
    edit = compile_edit(blueprint, clips, args.language)
    with tempfile.TemporaryDirectory(prefix='.film-stage-', dir=output_dir.parent) as staging:
        stage = Path(staging)
        (stage/'captions.srt').write_text(format_timeline_subtitles(edit))
        (stage/'captions.vtt').write_text(format_timeline_subtitles(edit, vtt=True))
        (stage/'captions.ass').write_text(ass_subtitles(edit), encoding='utf-8')
        argv = command(edit, 'product_video.mp4', str(Path(audio).resolve()) if audio else None,
                       'captions.ass' if args.burn_subtitles else None)
        subprocess.run(argv, cwd=stage, check=True, timeout=600)
        movie = stage/'product_video.mp4'
        video, metadata = probe(movie)
        if int(video.get('nb_frames') or 0) != edit['output_frames']:
            raise ValueError('rendered video does not have exact planned frame count')
        if movie.stat().st_size >= 200_000_000:
            raise ValueError('rendered movie exceeds delivery size limit')
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-threads', '1',
                        '-i', str(movie), '-f', 'null', '-'], check=True, timeout=120)
        report = {'edit': edit, 'metadata': metadata, 'sha256': digest(movie), 'decode_passed': True,
                  'visual_review': 'pending', 'subtitles': 'burned_in' if args.burn_subtitles else 'sidecar',
                  'audio': 'mixed_pending_final_listening' if audio else 'absent', 'network_calls': 0}
        (stage/'render_manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        output_dir.mkdir()
        for file in stage.iterdir():
            shutil.copy2(file, output_dir/file.name)
    print(str(output_dir/'product_video.mp4'))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print('finishing stopped: ' + str(exc), file=sys.stderr)
        sys.exit(1)
