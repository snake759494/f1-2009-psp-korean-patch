# F1 2009 (PSP, 유럽판) 비공식 한글패치

PSP 유럽판 **F1 2009 (ULES-01355)** 비공식 한국어 패치입니다. 이 저장소에는 제작 도구와 기술 문서만 있고, 패치 파일(xdelta)은 [Releases](../../releases)에서 받을 수 있습니다. 게임 원본·영어 원문·번역 대본·음성은 포함하지 않습니다.

## 적용 방법
1. 아래 해시와 일치하는 **원본 `.iso`** 를 준비합니다. (CSO·CHD 등으로 변환한 이미지에는 적용할 수 없습니다.)
   - PowerShell: `Get-FileHash -Algorithm MD5 -LiteralPath '.\F1 2009 (Europe) (En,Fr,De,Es,It).iso'`
2. xdeltaUI 같은 도구로 원본에 `F1_2009_Europe_KO_v1.0.xdelta` 를 적용합니다.
   - 명령줄: `xdelta3 -d -s "F1 2009 (Europe) (En,Fr,De,Es,It).iso" F1_2009_Europe_KO_v1.0.xdelta "F1 2009 (Europe) (KOR).iso"`
3. 만들어진 ISO를 PPSSPP 또는 커스텀 펌웨어에서 실행합니다. **PSP 본체(PPSSPP) 언어를 영어로** 두면 한국어가 나옵니다. (프랑스어·독일어·스페인어·이탈리아어 설정에서는 원문 그대로입니다.)

| 항목 | 값 |
| --- | --- |
| 원본 ISO 크기 | 684,359,680 바이트 |
| 원본 ISO MD5 | `fa3bf469327ebfaa4df61e0ea3fe4524` |
| 원본 ISO SHA-256 | `85339b42074bd0876122d3176a424577d87eb283ce68f70dacda7c46310d07ed` |
| xdelta SHA-256 | `c647528d4e5c87846c55884e8dcac0b70aef37481c7e99e6684e153a1b3fae5c` |
| 결과 ISO 크기 | 703,973,376 바이트 |
| 결과 ISO SHA-256 | `bbcd6a9cff68bcdc252e43eb0fe47183b3977ec955809b3d0f3bb2fcd14f7f06` |

## 한글화 내용
- 메뉴·시스템 문장 전체: UI 언어 파일(`UI/*_EN.DAT`, `*_US.DAT`)과 레이스 중 UI(`RACING`·`PRACTICE`·`QUALIFYING`·`CHALLENGES`·`MULTIPLAYER` PAK)
- 국가·그랑프리·서킷 이름, 드라이버·팀 이름, 팀 대표, 트로피 이름, 레이스 순위표, 일시 정지·그만두기 확인 창
- 글꼴: 게임 글꼴 아틀라스에 한글 712자 추가 (나눔스퀘어네오 Bold/ExtraBold, 아주 작은 글씨만 갈무리)
- **피트 무전 한국어 더빙**: 레이스 엔지니어 무전 1,678개 클립을 한국어 합성 음성으로 교체

## AI 음성 고지
피트 무전 한국어 음성은 **Supertonic 3(Supertone) 모델에 내장된 화자 M1** 로 합성했습니다. 원작 성우의 목소리를 복제·학습하지 않았습니다. 번역은 기계 번역 서비스를 쓰지 않고 작성했으며, 무전 대사의 조각 이어 붙이기는 원작 구조(영어 어순)를 따르므로 어색한 곳이 있을 수 있습니다.

## 그대로 둔 것
- 레이스 중계 해설(원작에 없음)·엔진음 등 효과음, 동영상, 로고, 그림으로 된 영문 장식 문구
- 대형 제목 글꼴은 아틀라스 크기 제한 때문에 한글이 라틴 글자보다 작게 보일 수 있습니다.

## 검증 범위
PPSSPP에서 타이틀, 국가 선택, 빠른 시작, 그랑프리(드라이버 선택·서킷 선택·연습 주행·그만두기), 트로피 진열장, 순위표, 피트 무전 재생을 확인했습니다. 실기와 전체 플레이 검증은 하지 않았습니다. 문제를 발견하면 Issues에 알려 주세요.

## 문서
- [CHANGELOG.md](CHANGELOG.md) — 변경 기록
- [docs/TECHNICAL.md](docs/TECHNICAL.md) — 파일 형식과 한글화 방법
- [docs/DUBBING.md](docs/DUBBING.md) — 피트 무전 더빙 방법
- [docs/BUILD.md](docs/BUILD.md) — 직접 빌드하는 방법
- [docs/FONT_CREDITS.md](docs/FONT_CREDITS.md) — 글꼴
- [RIGHTS.md](RIGHTS.md) — 권리 및 외부 자료
