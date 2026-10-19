"""EN/US 언어 DAT 전체 한글 빌드 -> build/UI/"""
import sys, os, json, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chunks import chunks
from f1fmt import parse_text
from build_lang import rebuild, is_hangul
UI = 'ext/PSP_GAME/USRDIR/UI'
OUT = 'build/UI'
ko = json.load(open('trans/ko.json', encoding='utf-8'))
COUNTRY_SCREENS = {'SEL_NATIONALITY', 'CREATE_PROFILE', 'PROFILE_SELECT', 'DRIVER_RESUME', 'DRIVER_SELECT', 'DRIVER_SELECT_MULTI', 'CAREER_SUMMARY', 'CAR_PREVIEW', 'CIRCUIT_SELECT', 'MULTIPLAYER', 'VERSUS'}
OVR = json.load(open('trans/override.json', encoding='utf-8'))

def texts(path):
    d = open(path, 'rb').read()
    for o, t, sz, u in chunks(d):
        if t == b'TEXT':
            return parse_text(d, o)
    return []

def trans_for(lang, name):
    """파일별 번역 dict (원문 -> 한글). US 는 같은 해시의 EN 문장 번역을 쓴다."""
    tr = {}
    p = f'{UI}/{name}_{lang}.DAT'
    if lang == 'EN':
        for h, s in texts(p):
            if s in ko: tr[s] = ko[s]
    else:
        en = dict(texts(f'{UI}/{name}_EN.DAT'))
        for h, s in texts(p):
            e = en.get(h)
            if s in ko: tr[s] = ko[s]
            elif e is not None and e in ko: tr[s] = ko[e]
    for k, v in OVR.get(name, {}).items():
        if k in tr or any(s == k for h, s in texts(p)): tr[k] = v
    return tr

def chars_of(lang, name):
    tr = trans_for(lang, name)
    return {c for s in tr.values() for c in s if ord(c) > 0x7f}

def _jp_info(name):
    """JP 파일의 (문자열 {hash: s}, 글꼴 글자 집합 리스트)"""
    d = open(f'{UI}/{name}_JP.DAT', 'rb').read()
    t = {}; fs = []
    from f1fmt import parse_font
    for o, tg, sz, u in chunks(d):
        if tg == b'TEXT': t = dict(parse_text(d, o))
        if tg == b'FONT': fs = [{chr(g['ch']) for g in f['glyphs']} for f in parse_font(d, o)]
    return t, fs

_CROSS = None
def cross_chars(lang, name):
    """다른 파일의 문자열을 이 파일 글꼴로 찍는 경우(국가명 등):
    JP 글꼴이 자기 파일 문장에 없는 글자를 담고 있으면, 그 글자를 쓰는 다른 파일 JP 문장의 한글을 추가"""
    global _CROSS
    if _CROSS is None:
        _CROSS = {}
        names = [os.path.basename(p)[:-7] for p in glob.glob(f'{UI}/*_JP.DAT')]
        info = {n: _jp_info(n) for n in names}
        for n, (t, fs) in info.items():
            own = set(''.join(t.values()))
            res = {}
            for S in fs:
                ex = {c for c in S - own if ord(c) > 0x7f}
                if len(ex) < 5: continue
                for n2, (t2, _) in info.items():
                    if n2 == n: continue
                    for h, s in t2.items():
                        na = {c for c in s if ord(c) > 0x7f}
                        if na and set(s) - {' ', chr(10)} <= S and (n2 == 'OPTIONS_LISTS' or len(na & ex) >= 0.6 * len(na)):
                            res.setdefault(n2, set()).add(h)
            _CROSS[n] = res
    out = set()
    for n2, hs in _CROSS.get(name, {}).items():
        p = f'{UI}/{n2}_{lang}.DAT'
        if not os.path.exists(p): continue
        tr = trans_for(lang, n2)
        for h, s in texts(p):
            if h in hs and s in tr:
                out |= {c for c in tr[s] if ord(c) > 0x7f}
    return out

def main(langs=('EN', 'US')):
    os.makedirs(OUT, exist_ok=True)
    report = []
    for lang in langs:
        common = chars_of(lang, 'QUICK_RACE') | chars_of(lang, 'OPTIONS_CAMERA')
        mc = chars_of(lang, 'MCMSGS')
        for p in sorted(glob.glob(f'{UI}/*_{lang}.DAT')):
            b = os.path.basename(p); name = b[:-len(f'_{lang}.DAT')]
            d = open(p, 'rb').read()
            tags = [c[1] for c in chunks(d)]
            if b'TEXT' not in tags and b'FONT' not in tags:
                continue
            extra = set(common) | cross_chars(lang, name)
            extra |= set(json.load(open('trans/name_chars.json', encoding='utf-8')))
            if name == 'POP_UPS': extra |= mc
            log = []
            a, n = rebuild(p, f'{OUT}/{b}', trans_for(lang, name), ''.join(sorted(extra)), log, face_map={0x78b11606: ('eb', 30)}, jp_path=f'{UI}/{name}_JP.DAT')
            jp = os.path.getsize(f'{UI}/{name}_JP.DAT')
            report.append(f'{b:34s} {a:7d} -> {n:7d}  (JP {jp:7d}) ' + ('!!' if n > jp else ''))
            for l in log: report.append('    ' + l)
    open('build/report.txt', 'w', encoding='utf-8').write('\n'.join(report))
    print('\n'.join(report))

if __name__ == '__main__':
    main(tuple(sys.argv[1:]) or ('EN', 'US'))
