# 빌드 방법

번역 대본·원문은 저장소에 없으므로, 아래는 자신이 가진 원본과 번역 파일로 다시 빌드하는 절차입니다.

## 준비물
- 원본 ISO `F1 2009 (Europe) (En,Fr,De,Es,It).iso` (MD5 `fa3bf469327ebfaa4df61e0ea3fe4524`)
- Python 3.12+ : `pip install -r requirements.txt`
- 글꼴 `NanumSquareNeo-cBd.ttf`, `NanumSquareNeo-dEb.ttf`, `Galmuri7/9/11*.ttf`
- 더빙: Sony `psmfenc.exe`(ATRAC3plus 인코더), Supertonic 3 모델(Hugging Face `Supertone/supertonic-3`)

## 폴더 구성
```
<게임 폴더>/
  F1 2009 (Europe) (En,Fr,De,Es,It).iso
  NanumSquareNeo-*.ttf
  work/
    tools/       (이 저장소의 tools)
    fonts/       Galmuri*.ttf
    trans/       b*.json, p*.json, override.json, name_chars.json, prio_chars.json  (번역 — 저장소 미포함)
    dub/         asr_en.jsonl, script_ko.jsonl  (무전 대본 — 저장소 미포함)
```

## 순서 (작업 폴더 `work/` 에서)
1. ISO 추출: `python tools/extract.py "../F1 2009 (Europe) (En,Fr,De,Es,It).iso" ext`
2. 원문 목록: `python tools/survey.py` → `uniq_EN.txt`, `uniq_PAK.txt`
3. 번역 작성: `trans/b*.json` = `{순번: 한국어}`, 합치기 `python tools/merge_trans.py`
4. UI DAT: `python tools/build_all.py EN US`
5. 레이스 PAK: `python tools/build_pak.py EN US`
6. 글꼴 검사: `python tools/verify.py` (모든 문장의 글자가 해당 글꼴에 있는지)
7. 더빙(선택): `docs/DUBBING.md`
8. ISO: `python tools/make_iso.py "../F1 2009 (Europe) (En,Fr,De,Es,It) (KOR).iso"`
9. 차분: `xdelta3 -e -0 -s 원본.iso 한글.iso 패치.xdelta`

PPSSPP 원격 디버거로 자동 확인할 때는 `python tools/emu.py` 를 씁니다.
