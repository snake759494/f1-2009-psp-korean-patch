"""빌드 결과 전수 검사: 각 DAT 의 각 글꼴이 그 파일 문자열(+이름 글자)의 한글을 모두 갖는지."""
import sys, os, glob, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chunks import chunks
from f1fmt import parse_text, parse_font
from pak import read_pak
PRIO = set(json.load(open('trans/prio_chars.json', encoding='utf-8')))
ALL = set(json.load(open('trans/name_chars.json', encoding='utf-8')))
H = lambda s: {c for c in s if 0xac00 <= ord(c) <= 0xd7a3}
def check(name, d, out):
    texts = []; fonts = []
    for o, t, sz, u in chunks(d):
        if t == b'TEXT': texts = parse_text(d, o)
        if t == b'FONT': fonts = parse_font(d, o)
    own = set()
    for h, s in texts: own |= H(s)
    for f in fonts:
        have = {chr(g['ch']) for g in f['glyphs']}
        full = len([c for c in have if c.isascii()]) >= 90
        miss_own = own - have if full else set()
        small = max((g['h'] for g in f['glyphs']), default=0) <= 16
        miss_pr = ((ALL if small else PRIO) - have) if full else set()
        if miss_own or miss_pr:
            out.append(f'{name} font {f["hash"]:08x} full={full} own-miss {len(miss_own)} {"".join(sorted(miss_own))[:60]} | name-miss {len(miss_pr)} {"".join(sorted(miss_pr))[:40]}')
out = []
for p in sorted(glob.glob('build/UI/*.DAT')):
    check(os.path.basename(p), open(p, 'rb').read(), out)
for p in sorted(glob.glob('build/OTHER/PSP_GAME/USRDIR/*.PAK')):
    hdr, ents = read_pak(open(p, 'rb').read())
    for e in ents:
        if e['data'][:4] == b'PTEX': check(f'{os.path.basename(p)}:{e["hash"]:08x}', e['data'], out)
print('\n'.join(out) or 'ALL OK'); print(len(out))
