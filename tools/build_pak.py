"""레이스 중 UI 언어 PAK (RACING_EN.PAK 등) 한글 재구성 -> build/OTHER/PSP_GAME/USRDIR/
PAK = [u32 개수 x4][엔트리 16바이트: 이름해시, 오프셋, 크기, 크기] + 0x400 정렬 데이터"""
import sys, os, json, glob, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chunks import chunks
from f1fmt import parse_text, parse_font
from pak import read_pak
import build_lang
build_lang.COMPACT = True
from build_lang import rebuild, align

SRC = 'ext/PSP_GAME/USRDIR'
OUT = 'build/OTHER/PSP_GAME/USRDIR'
TMP = 'build/tmp'
ko = json.load(open('trans/ko.json', encoding='utf-8'))
NAMES = json.load(open('trans/name_chars.json', encoding='utf-8'))


def rel_sig(d):
    """REL -> [(태그, 엔트리 수)]"""
    out = []; o = 0
    while o + 16 <= len(d) and d[o:o + 4] == b'RELO':
        sz = struct.unpack_from('<I', d, o + 4)[0]
        tag = d[o + 16:o + 20]; k = o + 20; n = 0
        while struct.unpack_from('<I', d, k)[0] != 0:
            n += 1; k += 8
        out.append((tag, n)); o += sz
    return out


def dat_sig(d):
    out = []
    for o, t, sz, u in chunks(d):
        n = 0
        if t == b'PTEX' or t == b'TEXT':
            n = struct.unpack_from('<I', d, o + 0x18)[0]
        elif t == b'FONT':
            n = 2 * struct.unpack_from('<I', d, o + 0x18)[0]
        else:
            n = None
        out.append((t, n))
    return out


def find_rel(ents, dat):
    sig = dat_sig(dat)
    cands = []
    for e in ents:
        if e['data'][:4] != b'RELO':
            continue
        rs = rel_sig(e['data'])
        if len(rs) == len(sig) and all(a[0] == b[0] and (b[1] is None or a[1] == b[1]) for a, b in zip(rs, sig)):
            cands.append(e)
    if len(cands) != 1:
        raise RuntimeError('REL 짝 찾기 실패 %d' % len(cands))
    return cands[0]


def texts(d):
    for o, t, sz, u in chunks(d):
        if t == b'TEXT':
            return parse_text(d, o)
    return []


def write_pak(hdr, ents, newdata):
    order = sorted(range(len(ents)), key=lambda i: ents[i]['off'])
    n = len(ents)
    out = bytearray(struct.pack('<4I', *hdr))
    out += bytes(16 * n)
    cur = align(len(out), 0x400)
    pos = {}
    for i in order:
        pos[i] = cur
        cur = align(cur + len(newdata.get(i, ents[i]['data'])), 0x400)
    buf = bytearray(align(cur, 0x800))
    buf[:len(out)] = out
    for i, e in enumerate(ents):
        data = newdata.get(i, e['data'])
        struct.pack_into('<4I', buf, 16 + 16 * i, e['hash'], pos[i], len(data), len(data))
        buf[pos[i]:pos[i] + len(data)] = data
    return bytes(buf)


def main(langs=('EN', 'US')):
    os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
    built = {}     # (lang, hash) -> (dat bytes, rel bytes or None)
    report = []
    for lang in langs:
        for p in sorted(glob.glob(f'{SRC}/*_{lang}.PAK')):
            name = os.path.basename(p)[:-len(f'_{lang}.PAK')]
            hdr, ents = read_pak(open(p, 'rb').read())
            _, jents = read_pak(open(f'{SRC}/{name}_JP.PAK', 'rb').read())
            jmap = {e['hash']: e['data'] for e in jents}
            enmap = {}
            if lang != 'EN':
                _, eents = read_pak(open(f'{SRC}/{name}_EN.PAK', 'rb').read())
                enmap = {e['hash']: dict(texts(e['data'])) for e in eents}
            newdata = {}
            for i, e in enumerate(ents):
                d = e['data']
                tags = [c[1] for c in chunks(d)]
                if b'TEXT' not in tags:
                    continue
                key = (lang, e['hash'])
                if key not in built:
                    tr = {}
                    en = enmap.get(e['hash'], {})
                    for h, s in texts(d):
                        if s in ko: tr[s] = ko[s]
                        elif h in en and en[h] in ko: tr[s] = ko[en[h]]
                    fi = f'{TMP}/in.DAT'; fo = f'{TMP}/out.DAT'
                    open(fi, 'wb').write(d)
                    if e['hash'] in jmap:
                        open(f'{TMP}/jp.DAT', 'wb').write(jmap[e['hash']])
                    rel = find_rel(ents, d)
                    open(f'{TMP}/in.REL', 'wb').write(rel['data'])
                    log = []
                    rebuild(fi, fo, tr, NAMES, log, face_map={0x36394d4e: ('eb', 17), 0x78b11606: ('eb', 30)}, jp_path=f'{TMP}/jp.DAT' if e['hash'] in jmap else None)
                    nd = open(fo, 'rb').read()
                    nr = open(f'{TMP}/out.REL', 'rb').read() if os.path.exists(f'{TMP}/out.REL') else None
                    built[key] = (nd, nr, rel['hash'])
                    report.append(f'{name}_{lang} {e["hash"]:08x} {len(d)} -> {len(nd)}' + (' +REL' if nr else ''))
                    report += ['    ' + l for l in log]
                    for f in ('in.DAT', 'out.DAT', 'jp.DAT', 'in.REL', 'out.REL'):
                        if os.path.exists(f'{TMP}/{f}'): os.remove(f'{TMP}/{f}')
                nd, nr, rh = built[key]
                newdata[i] = nd
                if nr is not None:
                    j = next(k for k, x in enumerate(ents) if x['hash'] == rh)
                    newdata[j] = nr
            out = write_pak(hdr, ents, newdata)
            open(f'{OUT}/{name}_{lang}.PAK', 'wb').write(out)
            report.append(f'== {name}_{lang}.PAK {os.path.getsize(p)} -> {len(out)}')
    open('build/report_pak.txt', 'w', encoding='utf-8').write('\n'.join(report))
    print('\n'.join(report))


if __name__ == '__main__':
    main(tuple(sys.argv[1:]) or ('EN', 'US'))
