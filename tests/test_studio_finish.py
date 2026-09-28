"""Optional local ffmpeg integration. Synthetic color/sine fixtures, no network."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'agent'))
from src.creative_plan import build_film_plan


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'studio ffmpeg/ffprobe unavailable')
class StudioFinishTest(unittest.TestCase):
    def test_render_exact_frames_captions_audio_no_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='synthetic-film-test-') as directory:
            root=Path(directory)
            plan=build_film_plan({'offer_id':'SYNTHETIC_TEST_ONLY','subject':'测试裙子',
                 'images':[], 'attributes':[{'attributeName':'颜色','value':'粉色'},
                                          {'attributeName':'裙长','value':'长裙'}]},seconds=10)
            clips={}
            for s,color in zip(plan['shots'],('red','blue','green','yellow','pink')):
                path=root/(s['id']+'.mp4');frames=s['output_frames']+12
                subprocess.run(['ffmpeg','-nostdin','-n','-v','error','-f','lavfi','-i',
                                f'color=c={color}:s=96x96:r=24','-frames:v',str(frames),
                                '-c:v','libx264','-threads','1','-pix_fmt','yuv420p',str(path)],check=True,timeout=30)
                clips[s['id']]={'path':str(path),'normalized_frames':frames,'in_frame':6,'fps':24,
                   'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'technical_valid':True,
                   'fidelity_verified':True,'role_verified':True,'borders_verified':True,
                   'source_fingerprint':plan['source_fingerprint'],'render_fingerprint':plan['render_fingerprint']}
            audio=root/'synthetic.wav'
            subprocess.run(['ffmpeg','-nostdin','-n','-v','error','-f','lavfi','-i',
                            'sine=frequency=440:duration=2','-c:a','pcm_s16le',str(audio)],check=True,timeout=30)
            bp=root/'blueprint.json';bp.write_text(json.dumps(plan))
            mp=root/'clips.json';mp.write_text(json.dumps({'clips':clips,'audio':{'path':str(audio),
                    'usage_authorized':True,'listening_reviewed':True,'sha256':hashlib.sha256(audio.read_bytes()).hexdigest()}}))
            output=root/'result'
            cmd=[sys.executable,str(ROOT/'tools/film_finish.py'),'--blueprint',str(bp),'--clips',str(mp),
                 '--output-dir',str(output),'--render','--burn-subtitles']
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads((output/'render_manifest.json').read_text())
            self.assertTrue(report['decode_passed']);self.assertEqual(report['subtitles'],'burned_in')
            self.assertEqual(report['edit']['output_frames'],240)
            video=next(s for s in report['metadata']['streams'] if s['codec_type']=='video')
            self.assertEqual(int(video['nb_frames']),240)
            self.assertEqual(report['visual_review'],'pending')
            self.assertTrue((output/'captions.vtt').read_text().startswith('WEBVTT'))
            repeat=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
            self.assertNotEqual(repeat.returncode,0)
            self.assertIn('already exists',repeat.stderr)
            for c in clips.values():self.assertEqual(hashlib.sha256(Path(c['path']).read_bytes()).hexdigest(),c['sha256'])


if __name__=='__main__':unittest.main()
