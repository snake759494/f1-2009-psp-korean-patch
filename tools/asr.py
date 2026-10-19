"""피트 무전 영어 클립 받아쓰기 -> dub/asr_en.jsonl"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('HF_HUB_OFFLINE', '1')
from pak import read_pak
from at3 import decode
from scipy.signal import resample_poly
from faster_whisper import WhisperModel
import ctranslate2
dev = 'cuda' if ctranslate2.get_cuda_device_count() else 'cpu'
m = WhisperModel('large-v3' if dev == 'cuda' else 'medium', device=dev, compute_type='float16' if dev == 'cuda' else 'int8')
d = open('aud/PITRADIO_EN.PAC', 'rb').read(); hdr, ents = read_pak(d)
out = 'dub/asr_en.jsonl'
done = set()
if os.path.exists(out):
    done = {json.loads(l)['i'] for l in open(out, encoding='utf-8')}
f = open(out, 'a', encoding='utf-8')
for i, e in enumerate(ents):
    if i in done: continue
    x, r = decode(e['data'])
    y = resample_poly(x, 160, 441).astype(np.float32)
    segs, _ = m.transcribe(y, language='en', beam_size=5, vad_filter=False)
    t = ' '.join(s.text.strip() for s in segs).strip()
    f.write(json.dumps({'i': i, 'hash': '%08x' % e['hash'], 'dur': round(len(x) / r, 3), 'en': t}, ensure_ascii=False) + '\n'); f.flush()
    if i % 50 == 0: print(i, t, flush=True)
