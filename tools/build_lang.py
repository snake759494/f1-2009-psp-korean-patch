"""언어 DAT (UI/*_EN.DAT 등) 한글 재구성.

TEXT : 번역문(UTF-8)으로 문자열 풀 재작성
FONT : 각 폰트에 파일에서 쓰는 한글 글리프 추가 (코드 순 정렬, 0xFFFF 맨 끝)
PTEX : 폰트 아틀라스를 풀어 아래쪽에 한글 글리프를 붙이고 다시 스위즐/압축
청크 개수와 포인터 필드 위치는 그대로라 .REL 은 손대지 않는다.
"""
import struct, os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chunks import chunks
from f1fmt import parse_text, parse_font
from ptex import entries
from tex import decode, swizzle
from lz import compress
import glyphs
from PIL import Image

MAGIC = 0x44332211
JPH = {}
COMPACT = False
MAXH = {0x0451036b: 448, 0x0e9c0a6f: 352}
import json as _j
PRIO = set(_j.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'trans', 'prio_chars.json'), encoding='utf-8')))


def align(x, a):
    return (x + a - 1) // a * a


def is_hangul(c):
    return 0xAC00 <= ord(c) <= 0xD7A3 or 0x3131 <= ord(c) <= 0x318E


def chunk_bytes(tag, body_used, hdr_extra):
    """tag + size + used + magic + body (body 는 chunk+0x10 부터)."""
    used = len(body_used)
    size = align(0x10 + used, 0x40)
    out = bytearray(size)
    struct.pack_into('<4sIII', out, 0, tag, size, used, MAGIC)
    out[0x10:0x10 + used] = body_used
    return bytes(out)


# ------------------------------------------------------------------ TEXT
def build_text(d, o, sz, u, newstr):
    n = struct.unpack_from('<I', d, o + 0x18)[0]
    hashes = [struct.unpack_from('<I', d, o + 0x1c + 8 * i)[0] for i in range(n)]
    body = bytearray(d[o + 0x10:o + 0x1c])  # +0x10 .. +0x1b (count 포함)
    rec_end = 0x1c + 8 * n
    pool = align(rec_end, 16)
    ptrs = [struct.unpack_from('<I', d, o + 0x20 + 8 * i)[0] for i in range(n)]
    order = sorted(range(n), key=lambda i: ptrs[i])   # 원본 풀 순서 유지
    strbytes = bytearray(); newptr = {}
    for i in order:
        newptr[i] = pool - 0x10 + len(strbytes)
        strbytes += newstr[i].encode('utf-8') + bytes(1)
    recs = bytearray()
    for i, h in enumerate(hashes):
        recs += struct.pack('<II', h, newptr[i])
    body += recs
    body += bytes(pool - rec_end)
    body += strbytes
    return chunk_bytes(b'TEXT', bytes(body), None)


# ------------------------------------------------------------------ 아틀라스
class Atlas:
    def __init__(self, t):
        self.bpp = t['bpp']; self.pal = t['pal']
        self.W = t['tbw']; self.H0 = t['h']
        self.rows = [t['idx'][y * self.W:(y + 1) * self.W] for y in range(t['h'])]
        self.used_h = 0
        self.bg = self._bg_index()

    @classmethod
    def blank(cls, pal, bpp, bg):
        a = cls.__new__(cls)
        a.bpp = bpp; a.pal = pal; a.W = 512; a.H0 = 0
        a.rows = []; a.used_h = 0; a.bg = bg
        return a

    def _bg_index(self):
        cnt = collections.Counter(i for r in self.rows for i in r)
        return cnt.most_common(1)[0][0]

    def widen(self, W):
        if W <= self.W:
            return
        for r in self.rows:
            r.extend([self.bg] * (W - self.W))
        self.W = W

    def ensure_h(self, h):
        while len(self.rows) < h:
            self.rows.append([self.bg] * self.W)

    def put(self, x, y, idxrows):
        self.ensure_h(y + len(idxrows))
        for j, r in enumerate(idxrows):
            self.rows[y + j][x:x + len(r)] = r

    def content_height(self):
        """원본 글리프가 차지하는 높이 (아래 빈 줄 제외)."""
        h = len(self.rows)
        while h > 0 and all(i == self.bg for i in self.rows[h - 1]):
            h -= 1
        return h

    def pack(self):
        H = align(max(len(self.rows), 8), 16)
        self.ensure_h(H)
        lin = bytearray()
        if self.bpp == 4:
            for r in self.rows[:H]:
                for k in range(0, self.W, 2):
                    lin.append((r[k] & 15) | ((r[k + 1] & 15) << 4))
        else:
            for r in self.rows[:H]:
                lin += bytes(r)
        rowb = self.W * self.bpp // 8
        return swizzle(bytes(lin), rowb, H), H


def nearest_index(pal, rgba, cache):
    if rgba in cache:
        return cache[rgba]
    r, g, b, a = rgba
    best = None
    for i, (pr, pg, pb, pa) in enumerate(pal):
        # 프리멀티플라이 공간 거리 + 알파
        dr = (pr * pa - r * a) / 255.0
        dg = (pg * pa - g * a) / 255.0
        db = (pb * pa - b * a) / 255.0
        da = pa - a
        dist = dr * dr + dg * dg + db * db + 2 * da * da
        if best is None or dist < best[0]:
            best = (dist, i)
    cache[rgba] = best[1]
    return best[1]


# ------------------------------------------------------------------ 스타일 추정
def glyph_ink(atlas, g):
    """글리프 박스 안 픽셀 (RGBA 리스트 2D)."""
    out = []
    for y in range(g['y'], g['y'] + g['h']):
        out.append([atlas.pal[i] for i in atlas.rows[y][g['x']:g['x'] + g['w']]])
    return out


def measure_cap(atlas, glyphs_by_ch):
    """'H' 등 대문자의 실제 잉크 (cap 높이, 박스 내 top 위치)."""
    for c in 'HEITLNMB':
        g = glyphs_by_ch.get(ord(c))
        if not g or g['w'] == 0:
            continue
        px = glyph_ink(atlas, g)
        rows = [j for j, r in enumerate(px) if any(p[3] > 140 and p[0] + p[1] + p[2] > 300 for p in r)]
        if rows:
            return rows[-1] - rows[0] + 1, rows[0], g
    return None


def detect_style(atlas, glyphs_by_ch):
    """8bpp 폰트: 채움색 / 그림자 / 외곽선 추정."""
    cnt = collections.Counter()
    for g in glyphs_by_ch.values():
        if g['w'] == 0:
            continue
        for r in glyph_ink(atlas, g):
            for p in r:
                if p[3] > 200:
                    cnt[p[:3]] += 1
    fill = cnt.most_common(1)[0][0]
    lum = lambda c: c[0] * 0.3 + c[1] * 0.59 + c[2] * 0.11
    # 채움색과 확연히 다른 색: 어두운 그림자 or 밝은 외곽선
    others = [(c, n) for c, n in cnt.most_common(40) if abs(lum(c) - lum(fill)) > 80]
    style = dict(fill=fill, shadow=None, outline=None, soff=(1, 1))
    if not others:
        return style
    oc = others[0][0]
    if lum(oc) < lum(fill):
        style['shadow'] = oc
    else:
        style['outline'] = oc
        darks = [c for c, n in cnt.most_common(60) if lum(c) < 140 and c != fill]
        style['shadow'] = darks[0] if darks else None
    # 그림자 오프셋 추정: 'H' 채움 마스크를 밀어서 그림자 마스크와 겹침 최대
    if style['shadow'] is not None:
        g = glyphs_by_ch.get(ord('H')) or glyphs_by_ch.get(ord('E'))
        if g:
            px = glyph_ink(atlas, g)
            near = lambda p, c: p[3] > 150 and sum(abs(p[k] - c[k]) for k in range(3)) < 60
            F = {(x, y) for y, r in enumerate(px) for x, p in enumerate(r) if near(p, fill)}
            S = {(x, y) for y, r in enumerate(px) for x, p in enumerate(r) if near(p, style['shadow'])}
            best = (0, (1, 1))
            for dx in range(0, 4):
                for dy in range(0, 4):
                    if dx == dy == 0:
                        continue
                    sc = len({(x + dx, y + dy) for x, y in F} & S)
                    if sc > best[0]:
                        best = (sc, (dx, dy))
            style['soff'] = best[1]
    return style


def stylize(mask, style, pad):
    """L 마스크 -> 스타일 입힌 RGBA (pad 만큼 여백)."""
    W, H = mask.size
    out = Image.new('RGBA', (W + 2 * pad, H + 2 * pad), (0, 0, 0, 0))
    base = Image.new('L', out.size, 0)
    base.paste(mask, (pad, pad))
    if style.get('outline') is not None:
        from PIL import ImageFilter
        ol = base.filter(ImageFilter.MaxFilter(3))
        if style.get('shadow') is not None:
            sh = Image.new('L', out.size, 0)
            dx, dy = style['soff']
            sh.paste(ol, (dx, dy))
            out.paste(Image.new('RGBA', out.size, style['shadow'] + (255,)), (0, 0), sh)
        out.paste(Image.new('RGBA', out.size, style['outline'] + (255,)), (0, 0), ol)
    elif style.get('shadow') is not None:
        sh = Image.new('L', out.size, 0)
        dx, dy = style['soff']
        sh.paste(base, (dx, dy))
        out.paste(Image.new('RGBA', out.size, style['shadow'] + (255,)), (0, 0), sh)
    out.paste(Image.new('RGBA', out.size, style['fill'] + (255,)), (0, 0), base)
    return out


# ------------------------------------------------------------------ 폰트 크기 선택
def choose_face(cap, bold_hint):
    """원본 cap 높이 -> (폰트 키, 한글 잉크 목표 높이)."""
    if cap <= 6:
        return 'g7', None
    if cap <= 8:
        return 'g9', None
    target = round(cap * 1.12 + 0.5)
    return ('eb' if bold_hint else 'bd'), target


def font_metrics(atlas, font, face_override=None, shrink=0):
    gl = {g['ch']: g for g in font['glyphs']}
    cap = measure_cap(atlas, gl)
    if cap is None:
        raise RuntimeError('cap 측정 실패 %08x' % font['hash'])
    capH, top_in_box, gH = cap
    cap_top_from_base = gH['oy'] - top_in_box          # 기준선 위로 cap top 까지
    sp = max(1, gH['adv'] - (gH['w'] - 2))              # 자간
    style = None; pad = 1
    if atlas.bpp == 8:
        style = detect_style(atlas, gl)
        pad = 1 + max(style['soff']) if style.get('shadow') is not None else 2
    key, target = face_override or choose_face(capH, capH >= 14)
    size = glyphs.pick_size(key, max(6, target - shrink)) if target else glyphs.PIXEL[key]
    rtop, rbot = glyphs.ref_box(key, size)
    refH = rbot - rtop
    cap_center = cap_top_from_base - capH / 2.0
    han_top_from_base = round(cap_center + refH / 2.0)
    return dict(capH=capH, sp=sp, style=style, pad=pad, key=key, size=size, top=han_top_from_base)


def add_hangul(atlas, font, chars, log, m, tex, max_h=512):
    """atlas 에 글리프를 선반 배치. 높이 max_h 를 넘으면 남은 글자를 돌려준다."""
    style, pad, key, size = m['style'], m['pad'], m['key'], m['size']
    cache = {}
    new = []
    x = 0
    y = atlas.content_height() + 1 if atlas.rows else 0
    shelf = 0
    atlas.widen(512)
    left = []
    pr = m.get('prio', {})
    todo = sorted(chars, key=lambda c: (pr.get(c, 9), c))
    for k, ch in enumerate(todo):
        r = glyphs.render(key, size, ch)
        if r is None:
            continue
        mask, dy, _ = r
        if style is None:
            img = Image.new('RGBA', (mask.width + 2 * pad, mask.height + 2 * pad), (255, 255, 255, 0))
            a = Image.new('L', img.size, 0); a.paste(mask, (pad, pad))
            img.putalpha(a)
        else:
            img = stylize(mask, style, pad)
        w, h = img.size
        if x + w > atlas.W:
            x = 0; y += shelf + 1; shelf = 0
        if y + h > max_h:
            left = todo[k:]
            break
        px = img.load()
        idxrows = [[nearest_index(atlas.pal, px[i, j], cache) for i in range(w)] for j in range(h)]
        atlas.put(x, y, idxrows)
        oy = m['top'] - dy + pad
        new.append(dict(tex=tex, ch=ord(ch), x=x, y=y, w=w, h=h,
                        ox=-pad, adv=mask.width + m['sp'], oy=oy, flag=1))
        x += w + 1
        shelf = max(shelf, h)
    if log is not None:
        log.append('font %08x tex %08x cap=%d face=%s size=%d n=%d atlasH=%d left=%d' % (
            font['hash'], tex, m['capH'], key, size, len(new), y + shelf, len(left)))
    return new, set(left)


# ------------------------------------------------------------------ FONT
def build_font(d, o, fonts, newglyphs):
    n = len(fonts)
    body = bytearray(d[o + 0x10:o + 0x1c])
    recs_off = 0x1c
    cur = align(recs_off + 0x20 * n, 16)
    tables = bytearray()
    tab_pos = []
    allg = []
    for f in fonts:
        gl = [g for g in f['glyphs'] if g['ch'] != 0xFFFF] + newglyphs.get(f['hash'], [])
        gl.sort(key=lambda g: g['ch'])
        gl += [g for g in f['glyphs'] if g['ch'] == 0xFFFF]
        allg.append(gl)
        tab_pos.append(cur + len(tables))
        for g in gl:
            tables += struct.pack('<IHHHHHhhhI', g['tex'], g['ch'], g['x'], g['y'], g['w'], g['h'],
                                 g['ox'], g['adv'], g['oy'], g['flag'])
        while len(tables) % 16:
            tables += b'\0'
    kern_start = cur + len(tables)
    kerns = bytearray(); kern_pos = []
    for f in fonts:
        if f['cflags']:
            kern_pos.append(kern_start + len(kerns))
            src = o + 0x10 + f['end']
            kerns += d[src:src + 8 * f['cflags']]
        else:
            kern_pos.append(None)
    end = kern_start + len(kerns)
    end_al = align(end, 16)
    recs = bytearray()
    for i, f in enumerate(fonts):
        kp = kern_pos[i] if kern_pos[i] is not None else end_al
        recs += struct.pack('<IIIIIIff', f['hash'], len(allg[i]) | (f['cflags'] << 16),
                            tab_pos[i] - 0x10, kp - 0x10, f['c'], f['lh'], f['fx'], f['fy'])
    body += recs
    body += bytes(cur - 0x10 - len(body))
    body += tables + kerns
    return chunk_bytes(b'FONT', bytes(body), None)


# ------------------------------------------------------------------ PTEX
def build_ptex(d, o, sz, u, ents, newtex, extra=()):
    """newtex: {hash: (comp, w, h, H, tbw, size)}
    extra: [(hash, template_record_bytes, (comp, w, h, H, tbw, size))] 새로 추가할 텍스처"""
    starts = sorted(o + 0x10 + e['ptr'] for e in ents) + [o + 0x10 + u]
    items = []   # [hash, rec bytes, comp, info or None, 원본 위치]
    for e in ents:
        rec = d[e['e']:e['e'] + 0x54]
        if e['hash'] in newtex:
            comp = newtex[e['hash']][0]; info = newtex[e['hash']]
        else:
            s0 = o + 0x10 + e['ptr']
            nxt = min(x for x in starts if x > s0)
            comp = d[s0:nxt]; info = None
        items.append([e['hash'], rec, comp, info, e['ptr']])
    big = 1 << 40
    for h, rec, info in extra:
        r2 = bytearray(rec); struct.pack_into('<I', r2, 0, h)
        items.append([h, bytes(r2), info[0], info, big + h])
    items.sort(key=lambda it: it[0])          # 엔트리는 해시 오름차순 (이진 탐색)
    n = len(items)
    body = bytearray(d[o + 0x10:o + 0x18]) + struct.pack('<I', n)
    hdr_end = 0x1c + 0x54 * n
    order = sorted(range(n), key=lambda i: items[i][4])   # 스트림은 원본 순서, 새것은 뒤
    pos = {}
    cur = align(hdr_end, 16)
    for i in order:
        pos[i] = cur
        cur = align(cur + len(items[i][2]), 16)
    hdrs = bytearray()
    for i, (h, rec, comp, info, _) in enumerate(items):
        rec = bytearray(rec)
        if info is not None:
            comp, w, hh, H, tbw, size = info
            struct.pack_into('<I', rec, 8, w | (hh << 16))
            struct.pack_into('<I', rec, 0x10, size)
            lw = max(0, (tbw - 1).bit_length())
            lh = max(0, (H - 1).bit_length())
            struct.pack_into('<I', rec, 0x1c + 4 * 9, 0xA8000000 | tbw)
            struct.pack_into('<I', rec, 0x1c + 4 * 10, 0xB8000000 | (lh << 8) | lw)
        struct.pack_into('<I', rec, 0x18, pos[i] - 0x10)
        hdrs += rec
    body += hdrs
    for i in order:
        body += bytes(pos[i] - 0x10 - len(body))
        body += items[i][2]
    return chunk_bytes(b'PTEX', bytes(body), None), n


def rebuild_rel(rel, ptex_count):
    """REL 의 PTEX 섹션을 엔트리 수에 맞게 다시 쓴다."""
    out = bytearray(); o = 0
    while o < len(rel):
        tag = rel[o:o + 4]
        if tag != b'RELO':
            out += rel[o:]; break
        sz, used, m = struct.unpack_from('<III', rel, o + 4)
        ctag = rel[o + 16:o + 20]
        if ctag == b'PTEX':
            body = bytearray(b'PTEX')
            for i in range(ptex_count):
                body += struct.pack('<II', 1, 0x24 + 0x54 * i)
            body += bytes(8)
            nsz = align(0x10 + len(body), 0x40)
            sec = bytearray(nsz)
            struct.pack_into('<4sIII', sec, 0, b'RELO', nsz, len(body), MAGIC)
            sec[0x10:0x10 + len(body)] = body
            out += sec
        else:
            out += rel[o:o + sz]
        o += sz
    return bytes(out)


# ------------------------------------------------------------------ 메인
def rebuild(path_in, path_out, trans, extra_chars='', log=None, face_map=None, jp_path=None):
    d = open(path_in, 'rb').read()
    cs = chunks(d)
    tinfo = None; fonts = None; ents = None
    for o, t, sz, u in cs:
        if t == b'TEXT': tinfo = (o, sz, u, parse_text(d, o))
        if t == b'FONT': fonts = (o, parse_font(d, o))
        if t == b'PTEX': ents = (o, sz, u, entries(d, o))
    newstr = None; chars = set(extra_chars)
    if tinfo:
        newstr = [trans.get(s, s) for h, s in tinfo[3]]
        for s in newstr:
            chars |= {c for c in s if is_hangul(c) or ord(c) > 0x7F and not c.isascii()}
    hangul = {c for c in chars if is_hangul(c) or c in '·…“”‘’→←↑↓'}
    newglyphs = {}; newtex = {}; extra = []
    if fonts and hangul:
        po = ents[0]
        texmap = {e['hash']: e for e in ents[3]}
        hashes = [h for h, s in tinfo[3]] if tinfo else []
        jpsel = None
        if jp_path and os.path.exists(jp_path):
            jd = open(jp_path, 'rb').read()
            jt = {}; jf = {}; jtex = {}; jph = {}
            for o2, t2, sz2, u2 in chunks(jd):
                if t2 == b'TEXT': jt = dict(parse_text(jd, o2))
                if t2 == b'FONT': jf = {f2['hash']: {chr(g['ch']) for g in f2['glyphs']} for f2 in parse_font(jd, o2)}
                if t2 == b'FONT': jtex = {f2['hash']: f2['glyphs'][0]['tex'] for f2 in parse_font(jd, o2)}
                if t2 == b'PTEX': jph = {e2['hash']: e2['h'] for e2 in entries(jd, o2)}
            jpsel = (jt, jf)
            JPH.clear(); JPH.update({fh: jph.get(th2) for fh, th2 in jtex.items()})
        own_all = {c for sn in (newstr or []) for c in sn if c in hangul}
        own_short = {c for (h0, so), sn in zip(tinfo[3] if tinfo else [], newstr or []) if len(so) <= 40 for c in sn if c in hangul}
        extras = {c for c in extra_chars if c in hangul}
        for f in fonts[1]:
            have = {g['ch'] for g in f['glyphs']}
            S = {chr(c) for c in have if c != 0xFFFF}
            full = len([c for c in S if c.isascii()]) >= 90
            sel = None
            if jpsel and f['hash'] in jpsel[1] and jpsel[0]:
                jt, jf = jpsel; SJ = jf[f['hash']] | {' ', chr(10)}
                sel = [i for i, h in enumerate(hashes) if h in jt and set(jt[h]) <= SJ]
            elif not full:
                sel = [i for i, (h, so) in enumerate(tinfo[3]) if so and set(so) - {' ', chr(10)} <= S]
            # 제한 글꼴도 자기 파일 문자열 글자 전체를 후보로 (선택 문장 글자는 최우선)
            sel_chars = {c for i in (sel or []) for c in newstr[i] if c in hangul} if sel is not None and len(sel) < len(hashes) else None
            pool = set(own_all)
            pool_own = set(pool)
            if full:
                pool |= extras
            need = {c for c in pool if ord(c) not in have}
            if not need:
                continue
            th = f['glyphs'][0]['tex']
            e = texmap[th]
            if th in newtex:
                raise RuntimeError('텍스처 공유')
            t = decode(d, po, e)
            fo = (face_map or {}).get(f['hash'])
            shrink = 0
            while True:
                atlas = Atlas(t)
                m = font_metrics(atlas, f, fo, shrink)
                m['prio'] = {c: (0 if (c in sel_chars if sel_chars is not None else c in own_short) else 1 if (c in PRIO and full) or (sel_chars is not None and c in own_short) else 2 if c in pool_own else 3) for c in need}
                need2 = set(need) if not COMPACT else {c for c in need if m['prio'][c] < 3}
                sub = []
                ng, left = add_hangul(atlas, f, need2, sub, m, th, max_h=MAXH.get(f['hash'], 320))
                small = m['capH'] <= 12
                if (not left or (not small and not any(m['prio'][c] < 2 for c in left))) or shrink >= 7 or (small and shrink >= 2 and not any(m['prio'][c] < 2 for c in left)) or m['key'] in glyphs.PIXEL:
                    if log is not None: log.extend(sub)
                    break
                shrink += 1
            packed, H = atlas.pack()
            clut = b''.join(bytes(p) for p in t['pal'])
            newtex[th] = (compress(clut + packed), atlas.W, max(atlas.content_height(), 1), H, atlas.W, len(packed))
            nh = th
            if left and log is not None:
                log.append('    DROPPED %d (important %d): %s' % (len(left), sum(1 for c in left if m['prio'].get(c, 9) < 2), ''.join(sorted(c for c in left if m['prio'].get(c, 9) < 2))))
            while False:
                # 남은 글자는 보조 텍스처로
                taken = set(texmap) | set(newtex) | {x[0] for x in extra}
                nh = (nh + 1) & 0xFFFFFFFF
                while nh in taken:
                    nh = (nh + 1) & 0xFFFFFFFF
                bg = min(range(len(t['pal'])), key=lambda i: t['pal'][i][3])
                at2 = Atlas.blank(t['pal'], t['bpp'], bg)
                g2, left = add_hangul(at2, f, left, log, m, nh)
                ng += g2
                packed2, H2 = at2.pack()
                rec = d[e['e']:e['e'] + 0x54]
                extra.append((nh, rec, (compress(clut + packed2), 512, max(at2.content_height(), 1), H2, 512, len(packed2))))
            if 32 not in have:
                # 공백 글리프가 없는 제한 글꼴: 번역문의 띄어쓰기용 공백 추가
                ng.append(dict(tex=th, ch=32, x=0, y=0, w=0, h=0, ox=0,
                               adv=max(3, round(m['capH'] / 3)), oy=0, flag=0))
            newglyphs[f['hash']] = ng
    out = bytearray()
    for o, t, sz, u in cs:
        if t == b'TEXT' and newstr is not None:
            out += build_text(d, o, sz, u, newstr)
        elif t == b'FONT' and newglyphs:
            out += build_font(d, o, fonts[1], newglyphs)
        elif t == b'PTEX' and (newtex or extra):
            chunk, pcount = build_ptex(d, o, sz, u, ents[3], newtex, extra)
            out += chunk
        else:
            out += d[o:o + sz]
    tail = cs[-1][0] + cs[-1][2]
    out += d[tail:]
    open(path_out, 'wb').write(out)
    rel_in = path_in[:-4] + '.REL'
    if extra:
        if not os.path.exists(rel_in):
            raise RuntimeError('REL 없이 텍스처 추가 불가: ' + path_in)
        open(path_out[:-4] + '.REL', 'wb').write(rebuild_rel(open(rel_in, 'rb').read(), pcount))
    elif os.path.exists(path_out[:-4] + '.REL'):
        os.remove(path_out[:-4] + '.REL')
    return len(d), len(out)
