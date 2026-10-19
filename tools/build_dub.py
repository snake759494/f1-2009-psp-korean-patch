"""한국어 합성 음성(dub/ko_wav) -> AT3+ -> PITRADIO_EN.PAC 재구성.
원본 클립 규칙: fact=(샘플 수, 앞 지연 D), smpl 재생 구간 = D .. D+n-1. 새 클립도 같은 규칙으로 만든다."""
import os, sys, glob, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.io import wavfile
from pak import read_pak
from build_pak import write_pak
from at3 import encode_many, chunks, decode

D = 3456          # 앞 지연(샘플): 원본과 비슷한 값
OUTP = 'build/OTHER/PSP_GAME/USRDIR/AUDIO/WAV/PITR/PITRADIO_EN.PAC'


def make_riff(fmt, frames, n, orig):
    c = chunks(orig)
    fo0, fn0 = c[b'fmt ']
    of = bytearray(orig[fo0 + 8:fo0 + 8 + fn0])
    of[2:4] = fmt[2:4]; of[8:12] = fmt[8:12]; of[12:14] = fmt[12:14]
    of[20:24] = fmt[20:24]; of[40:44] = fmt[40:44]
    so, sn = c[b'smpl']
    smpl = bytearray(orig[so + 8:so + 8 + sn])
    struct.pack_into('<I', smpl, 44, D)              # 재생 시작
    struct.pack_into('<I', smpl, 48, D + n - 1)      # 재생 끝
    body = b'fmt ' + struct.pack('<I', len(of)) + bytes(of)
    body += b'fact' + struct.pack('<I', 8) + struct.pack('<II', n, D)
    body += b'smpl' + struct.pack('<I', len(smpl)) + bytes(smpl)
    data = b''.join(frames)
    body += b'data' + struct.pack('<I', len(data)) + data
    return b'RIFF' + struct.pack('<I', 4 + len(body)) + b'WAVE' + body


def main(batch=120):
    d = open('aud/PITRADIO_EN.PAC', 'rb').read(); hdr, ents = read_pak(d)
    wavs = sorted(glob.glob('dub/ko_wav/*.wav'))
    idx = [int(os.path.basename(p)[:4]) for p in wavs]
    newdata = {}
    for b in range(0, len(idx), batch):
        part = idx[b:b + batch]
        sigs = []
        for i in part:
            r, x = wavfile.read(f'dub/ko_wav/{i:04d}.wav')
            x = x.astype(np.float32) / 32768.0
            sigs.append(np.concatenate([np.zeros(D, np.float32), x]))
        fmt, frames, spans = encode_many(sigs)
        for i, x, (st, nf) in zip(part, sigs, spans):
            n = len(x) - D
            newdata[i] = make_riff(fmt, frames[st:st + nf], n, ents[i]['data'])
        print('encoded', b + len(part), '/', len(idx), flush=True)
    out = write_pak(hdr, ents, newdata)
    os.makedirs(os.path.dirname(OUTP), exist_ok=True)
    open(OUTP, 'wb').write(out)
    print('PAC', len(d), '->', len(out), 'replaced', len(newdata))


if __name__ == '__main__':
    main()
