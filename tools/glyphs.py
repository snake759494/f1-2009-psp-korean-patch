"""한글 글리프 렌더링 (나눔스퀘어네오 / 작은 글씨는 갈무리)."""
import os
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.join(ROOT, 'work')
FONT_FILES = {
    'rg': os.path.join(ROOT, 'NanumSquareNeo-bRg.ttf'),
    'bd': os.path.join(ROOT, 'NanumSquareNeo-cBd.ttf'),
    'eb': os.path.join(ROOT, 'NanumSquareNeo-dEb.ttf'),
    'hv': os.path.join(ROOT, 'NanumSquareNeo-eHv.ttf'),
    'g7': os.path.join(WORK, 'fonts', 'Galmuri7.ttf'),
    'g9': os.path.join(WORK, 'fonts', 'Galmuri9.ttf'),
    'g11': os.path.join(WORK, 'fonts', 'Galmuri11.ttf'),
    'g11b': os.path.join(WORK, 'fonts', 'Galmuri11-Bold.ttf'),
}
PIXEL = {'g7': 8, 'g9': 10, 'g11': 12, 'g11b': 12}


@lru_cache(None)
def _font(key, size):
    return ImageFont.truetype(FONT_FILES[key], size)


def ink_box(im):
    return im.getbbox()


@lru_cache(None)
def pick_size(key, target_ink):
    """target_ink 픽셀 높이(한글 '한' 기준)에 맞는 폰트 크기."""
    if key in PIXEL:
        return PIXEL[key]
    best = None
    for s in range(6, 64):
        im = render_raw(key, s, '한')
        b = im.getbbox()
        h = b[3] - b[1]
        if best is None or abs(h - target_ink) < abs(best[1] - target_ink):
            best = (s, h)
        if h > target_ink + 2:
            break
    return best[0]


def render_raw(key, size, ch):
    f = _font(key, size)
    im = Image.new('L', (size * 3, size * 3), 0)
    dr = ImageDraw.Draw(im)
    if key in PIXEL:
        dr.fontmode = '1'
    dr.text((size, size), ch, font=f, fill=255)
    return im


@lru_cache(None)
def ref_box(key, size):
    """'한' 의 잉크 상하 (정렬 기준)."""
    im = render_raw(key, size, '한')
    b = im.getbbox()
    return b[1], b[3]


def render(key, size, ch):
    """(L 이미지(잉크 bbox crop), 잉크 top 의 기준선 대비 위치 dy, 잉크 폭)
    dy: '한' 잉크 top 을 0 으로 한 상대 위치."""
    im = render_raw(key, size, ch)
    b = im.getbbox()
    if b is None:
        return None
    top, _ = ref_box(key, size)
    crop = im.crop(b)
    return crop, b[1] - top, b[0]
