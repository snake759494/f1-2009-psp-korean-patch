"""ATRAC3plus 클립 도구: 디코딩(PyAV), Sony psmfenc 로 인코딩, 원본과 같은 RIFF 로 감싸기."""
import os, struct, subprocess, numpy as np, wave, av
SUITE = r'D:\psp\전장의발큐리아2\도구\psmfsuite\PSMF Stream Composer Suite'
TMP = r'C:\f1tmp'
FRAME = 2048

def decode(data):
    p = os.path.join(TMP, 'dec.at3'); open(p, 'wb').write(data)
    c = av.open(p); s = c.streams.audio[0]
    x = np.concatenate([f.to_ndarray().reshape(f.to_ndarray().shape[0], -1)[0] for f in c.decode(s)])
    c.close(); return x.astype(np.float32), s.rate

def chunks(d):
    o = 12; out = {}
    while o + 8 <= len(d):
        tag = d[o:o + 4]; n = struct.unpack_from('<I', d, o + 4)[0]
        out[tag] = (o, n); o += 8 + n + (n & 1)
    return out

def encode_many(sigs, kbps=96):
    """여러 모노 신호를 한 번에 인코딩해 각자의 (프레임 리스트) 반환.
    클립 사이에 무음 프레임 2개를 두고 프레임 경계로 자른다."""
    DELAY = 2416                      # psmfenc 지연(샘플) = 1프레임 + 368
    total = 4 * FRAME
    spans = []
    for x in sigs:
        n = (len(x) + FRAME - 1) // FRAME + 1
        spans.append((total // FRAME, n, len(x)))
        total += (n + 2) * FRAME
    y = np.zeros(total + 44100 * 10, np.float32)
    for (st, n, L), x in zip(spans, sigs):
        p = st * FRAME - (DELAY - FRAME)
        y[p:p + L] = x
    spans = [(st + 1, n) for st, n, L in spans]
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    wp = os.path.join(TMP, 'enc.wav'); ap = os.path.join(TMP, 'enc.atx')
    w = wave.open(wp, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
    w.writeframes(np.stack([pcm, pcm], 1).tobytes()); w.close()
    if os.path.exists(ap): os.remove(ap)
    r = subprocess.run([os.path.join(SUITE, 'psmfenc.exe'), '-audio', '-avgb', str(kbps), wp, ap],
                       cwd=SUITE, capture_output=True, text=True)
    if not os.path.exists(ap): raise RuntimeError(r.stdout[-300:])
    a = open(ap, 'rb').read(); c = chunks(a)
    fmt = a[c[b'fmt '][0] + 8:c[b'fmt '][0] + 8 + c[b'fmt '][1]]
    do, dn = c[b'data']; raw = a[do + 8:do + 8 + dn]
    # 8바이트 동기 헤더 + 프레임
    fs = (((raw[2] & 3) << 8) | raw[3]) * 8 + 8
    frames = [raw[i + 8:i + 8 + fs] for i in range(0, len(raw) - 8 - fs + 1, 8 + fs)]
    # psmfenc 은 앞에 지연(프레임) 이 있다: 무음 리드 길이로 보정
    return fmt, frames, spans

def wrap(fmt, frames, nsamples, orig):
    """원본 RIFF 의 fact/smpl 구조를 따라 새 RIFF 생성 (fmt 는 인코더 것)."""
    c = chunks(orig)
    fo0, fn0 = c[b'fmt ']
    of = bytearray(orig[fo0 + 8:fo0 + 8 + fn0])
    of[2:4] = fmt[2:4]                 # 채널 수
    of[8:12] = fmt[8:12]               # 평균 바이트/초
    of[12:14] = fmt[12:14]             # 블록 크기
    of[20:24] = fmt[20:24]             # 채널 마스크
    of[40:44] = fmt[40:44]             # 코덱 설정(채널·프레임 크기)
    body = b'fmt ' + struct.pack('<I', len(of)) + bytes(of)
    if b'fact' in c:
        fo, fn = c[b'fact']; fact = bytearray(orig[fo + 8:fo + 8 + fn])
        struct.pack_into('<I', fact, 0, nsamples)
        body += b'fact' + struct.pack('<I', len(fact)) + bytes(fact)
    data = b''.join(frames)
    body += b'data' + struct.pack('<I', len(data)) + data
    return b'RIFF' + struct.pack('<I', 4 + len(body)) + b'WAVE' + body
