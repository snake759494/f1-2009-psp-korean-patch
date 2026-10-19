# 피트 무전 더빙

대상: `USRDIR/AUDIO/WAV/PITR/PITRADIO_EN.PAC` — RIFF ATRAC3plus 클립 1,678개.

1. 받아쓰기: `tools/at3.py` 로 원본 클립을 PyAV 로 디코드하고, `tools/asr.py`(faster-whisper medium) 로 영어 대본을 만듭니다.
2. 대본: `dub_script.py`(저장소 미포함)가 드라이버 이름·순위·숫자·랩 수 같은 조각 템플릿과 문장 사전으로 한국어 대본을 만듭니다. 게임이 조각을 영어 어순으로 이어 붙이므로 조각마다 자연스럽게 끝나도록 번역했습니다.
3. 합성: `tools/dub_tts.py` — Supertonic 3 내장 화자 M1, 원본 발화 길이에 맞춰 속도 0.9~1.3, 넘치면 WSOLA 로 최대 1.25배 압축. 무전기 대역(300~2800Hz) + 약한 포화, 원본과 같은 LUFS 로 맞춤.
4. 인코딩: `tools/build_dub.py` — 클립 120개씩 이어 Sony psmfenc(`-audio -avgb 96`)로 AT3+ 인코딩 후 프레임 단위로 잘라 원래 RIFF 구조로 복원.
   - 인코더 지연 2,416 샘플을 보정하고, `fact` = (샘플 수, 앞 지연 3,456), `smpl` 재생 구간 = 지연 .. 지연+n-1.
   - fmt 청크는 원본 것을 쓰고 채널·비트레이트 필드만 갱신(psmfenc 의 GUID 를 그대로 쓰면 디코더가 실패).
5. PAC 재조립: 0x400 정렬 데이터, 파일 0x800 정렬(`tools/pak.py`, `build_pak.write_pak`).

PPSSPP `DumpAudio=True` 로 레이스 중 실제 재생을 녹음해 확인했습니다.
