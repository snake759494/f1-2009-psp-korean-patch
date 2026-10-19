"""피트 무전 한국어 합성 - Supertonic 3 (Supertone, 코드 MIT / 모델 OpenRAIL-M), 건담 클라이맥스 UC 방식.
dub/script_ko.jsonl -> dub/ko_wav/<i>.wav (44.1kHz 모노)
 - 목소리: 모델 내장 화자 하나(레이스 엔지니어). 원작 성우 목소리를 복제하지 않는다.
 - 길이: 원본 발화 길이에 맞게 속도(0.9~1.6)를 정하고, 넘치면 WSOLA 로 원본 x1.15 안으로.
 - 음색: 원본처럼 무전기 대역(300~2800Hz) + 약한 포화.
 - 음량: 원본과 같은 체감 음량(LUFS).
"""
import os, sys, json, re, hashlib
os.environ.setdefault('HF_HUB_OFFLINE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
from pak import read_pak
from at3 import decode
from loudness import lufs, master

RATE = 44100
VOICE = sys.argv[1] if len(sys.argv) > 1 else 'M1'
NATURAL = 5.6           # 음절/초 (속도 1.0)
OUT = 'dub/ko_wav'
SOS = butter(4, [300, 2800], 'bandpass', fs=RATE, output='sos')


def trim(x, margin):
    env = np.abs(x) > max(300.0, np.abs(x).max() * 0.02)
    idx = np.nonzero(env)[0]
    if len(idx) == 0: return x
    return x[max(0, idx[0] - margin):idx[-1] + margin]


def wsola(x, speed, win=1320, tol=330):
    hop = win // 2; w = np.hanning(win); n_out = int(len(x) / speed)
    xp = np.concatenate([np.zeros(tol + win), x, np.zeros(tol + 2 * win)])
    base = tol + win; y = np.zeros(n_out + win); ws = np.zeros(n_out + win); prev = base
    for m in range(0, n_out, hop):
        ideal = base + int(m * speed)
        if m == 0: pos = ideal
        else:
            target = xp[prev + hop:prev + hop + win]; seg = xp[ideal - tol:ideal + tol + win]
            pos = ideal - tol + int(np.argmax(np.correlate(seg, target, 'valid')))
        y[m:m + win] += xp[pos:pos + win] * w; ws[m:m + win] += w; prev = pos
    return (y / np.maximum(ws, 1e-3))[:n_out]


def tts_text(t):
    t = t.replace('…', ', ').replace('...', ', ')
    t = re.sub(r'[^가-힣0-9A-Za-z .,!?&]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip(' ,') or '.'


def radio(x):
    y = sosfilt(SOS, x / 32768.0)
    y = np.tanh(y * 2.2) / np.tanh(2.2)
    return y * 32768.0


class Voice:
    def __init__(self, name):
        from huggingface_hub import hf_hub_download
        from supertonic import TTS
        path = os.path.dirname(hf_hub_download('Supertone/supertonic-3', 'config.json', local_files_only=True))
        self.tts = TTS(model='supertonic-3', model_dir=path, auto_download=False)
        self.style = self.tts.get_voice_style(name)

    def say(self, text, speed, seed):
        np.random.seed(seed)
        wav, _ = self.tts.synthesize(text, voice_style=self.style, lang='ko', speed=speed)
        x = wav.squeeze().astype(np.float64) * 32767
        return trim(x, int(0.01 * RATE))


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = [json.loads(l) for l in open('dub/script_ko.jsonl', encoding='utf-8')]
    d = open('aud/PITRADIO_EN.PAC', 'rb').read(); hdr, ents = read_pak(d)
    v = Voice(VOICE)
    log = open('dub/tts_log.jsonl', 'a', encoding='utf-8')
    for r in rows:
        p = f"{OUT}/{r['i']:04d}.wav"
        if os.path.exists(p): continue
        o, _ = decode(ents[r['i']]['data']); o = o.astype(np.float64) * 32767
        speech = max(0.25, len(trim(o, 0)) / RATE)
        target = lufs(o, RATE)
        limit = int(max(len(o) * 1.4, len(o) + 0.4 * RATE))
        text = tts_text(r['ko'])
        syl = len(re.findall('[가-힣]', text)) + len(re.findall('[0-9A-Za-z]', text)) * 0.6
        speed = float(np.clip(syl / NATURAL / speech, 0.9, 1.3))
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16) % 100000
        x = v.say(text, speed, seed)
        k = 1.0
        if len(x) > limit - int(0.06 * RATE):
            k = len(x) / (limit - int(0.06 * RATE))
            k = min(k, 1.25)          # 너무 빨라지면 알아듣기 어렵다: 최대 1.25배까지만 압축
            x = wsola(x, k * 1.003)
        y = radio(x)
        y = master(y, RATE, target)
        pad = np.zeros(int(0.03 * RATE))
        y = np.concatenate([pad, y, pad])
        wavfile.write(p, RATE, np.clip(y, -32768, 32767).astype(np.int16))
        log.write(json.dumps({'i': r['i'], 'ko': r['ko'], 'speed': round(speed, 2), 'stretch': round(k, 3),
                              'orig': round(len(o) / RATE, 2), 'new': round(len(y) / RATE, 2)}, ensure_ascii=False) + '\n')
        log.flush()
        if r['i'] % 100 == 0: print(r['i'], r['ko'], flush=True)


if __name__ == '__main__':
    main()
