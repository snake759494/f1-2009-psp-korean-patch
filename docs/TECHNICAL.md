# 기술 문서

## 교체 파일
- UI 언어 파일 `PSP_GAME/USRDIR/UI/*_EN.DAT`·`*_US.DAT` (+ 짝 `.REL`)
- 레이스 중 UI `USRDIR/{RACING,PRACTICE,QUALIFYING,CHALLENGES,MULTIPLAYER}_EN.PAK`·`_US.PAK`
- 피트 무전 `USRDIR/AUDIO/WAV/PITR/PITRADIO_EN.PAC`
- PSP 언어가 영어(그 외 미지원 언어 포함)면 EN 파일을 읽습니다. 미국 영어용 US 파일은 해시로 EN 번역에 대응시킵니다.

## DAT 청크
- 청크 = 태그, 크기(0x40 정렬), 사용 크기, 매직 `0x44332211`. 종류: `PTEX`(텍스처), `FONT`(글리프 표), `TEXT`(UTF-8 문자열).
- 포인터는 `.REL` 재배치 섹션(형식 1 = 포인터 오프셋 목록)으로 고칩니다. PTEX 항목은 `0x24 + 0x54*i`.
- TEXT 는 원본 문자열 풀 순서를 유지한 채 다시 씁니다.

## PTEX 압축 (EBOOT 0x169894)
- 플래그 바이트를 MSB 부터 읽는 LZ. 일치 토큰 BE16 `dist<<4 | (len-3)`.
- `dist == 0` 은 RLE: 바이트 b3 을 `((b1&15)<<8 | b2) + 16` 회 반복.
- 압축 해제 결과는 CLUT 다음 스위즐된 픽셀(16바이트 × 8행 블록). 항목은 해시 순 정렬, 데이터 스트림은 원래 순서.
- `tools/lz.py`(압축·해제), `tools/tex.py`(디코드·스위즐).

## FONT
- 글리프 수 필드의 상위 16비트가 커닝 쌍 수.
- 글리프 레코드 `<IHHHHHhhhI` = 텍스처, 문자, x, y, w, h, ox, 전진폭, oy, 플래그. 문자 코드로 이진 탐색하므로 정렬 유지, 미지원 글자용 `0xFFFF` 레코드는 맨 끝.
- 한글은 원본 라틴 글리프를 그대로 두고 아틀라스 아래쪽에 추가합니다(4bpp 흰색+알파 / 8bpp 그림자 스타일 재현).

## 아틀라스 한계와 글자 선택
- 텍스처 높이가 약 320~410px 를 넘거나 텍스처를 추가하면 게임이 그리지 않습니다 → 원래 텍스처 하나 안에서 해결.
- 레이스 중에는 VRAM 이 빠듯해 PAK 글꼴은 COMPACT 모드(필요한 글자만, 더 작게).
- 글꼴마다 넣을 글자는 일본어판에서 같은 글꼴이 담당하는 문장을 기준(oracle)으로 고르고, 이름·국가 글자를 우선순위로 채운 뒤 넘치면 크기를 단계적으로 줄입니다(`build_lang.add_hangul`).
- `tools/verify.py` 로 모든 문장의 글자가 실제 쓰이는 글꼴에 있는지 전수 검사합니다.

## ISO
- pycdlib 로 추출, `tools/patch_iso.py` 가 같은 자리에 덮어쓰거나 끝에 붙이고 디렉터리 레코드·PVD 를 갱신합니다.

## 피트 무전
`docs/DUBBING.md` 참고.
