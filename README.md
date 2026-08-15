# Kakao_Daily

매일 아침 카카오톡 '나와의 채팅'으로 명작 한 조각을 보내주는 자동 발송기.

- **한국 근대소설**은 원문 그대로 한 통
- **해외 고전**은 원문 한 통 + 한국어 번역·해설 한 통

저작권 보호기간(사후 70년)이 끝난 작품만 싣는다.

---

## 어떻게 생겼나

**한국 트랙 (짝수 날)**

```
📖 운수 좋은 날 — 현진건 (1/3)

새침하게 흐린 품이 눈이 올 듯하더니 눈은 아니 오고
얼다가 만 비가 추적추적 내리었다.

[원문 읽기]
```

**해외 트랙 (홀수 날)** — 두 통이 이어서 온다

```
📖 Pride and Prejudice — 제인 오스틴 (1/6)

It is a truth universally acknowledged, that a single
man in possession of a good fortune, must be in want
of a wife.

[원문 읽기]
```
```
🔎 오만과 편견 (1/6)

재산깨나 있는 독신 남자에게는 반드시 아내가 필요하다는 것,
이것은 누구나 인정하는 진리다.

— 소설의 첫 문장. 보편적 진리인 척 시치미를 떼지만, 정작
그 '진리'를 믿는 건 사윗감을 노리는 동네 어머니들뿐이다.

[원문 읽기]
```

카카오 텍스트 메시지는 **200자**까지만 들어간다. 그래서 '1장 전체'를 한 번에
보내는 건 불가능하고, 작품을 200자 이하 조각으로 나눠 매일 이어서 보내는
연재 방식으로 동작한다.

---

## 빠른 시작

### 1. 카카오 앱 만들기

[카카오 개발자 콘솔](https://developers.kakao.com/console/app)에서:

1. **애플리케이션 추가하기** → 앱 이름·회사명 입력
2. **앱 설정 → 앱 키**에서 `REST API 키` 복사
3. **제품 설정 → 카카오 로그인** → 활성화 **ON**
4. 같은 화면의 **Redirect URI**에 `http://localhost:8080/callback` 등록
5. **제품 설정 → 카카오 로그인 → 동의항목**에서
   **카카오톡 메시지 전송(`talk_message`)**을 사용 설정

> 나에게 보내기는 앱 검수나 비즈니스 채널 등록이 **필요 없다.**
> 친구에게 보내기로 바꾸려면 그때부터 심사가 필요하다.

### 2. refresh token 발급 (최초 1회, 로컬에서)

```bash
git clone <이 저장소>
cd Kakao_Daily
pip install -r requirements.txt

export KAKAO_REST_API_KEY=<위에서 복사한 REST API 키>
python scripts/get_token.py
```

브라우저가 열리고 동의를 마치면 터미널에 `KAKAO_REFRESH_TOKEN`이 출력된다.

### 3. GitHub에 등록

**Settings → Secrets and variables → Actions**

Secrets (`New repository secret`):

| 이름 | 값 |
|---|---|
| `KAKAO_REST_API_KEY` | 카카오 REST API 키 |
| `KAKAO_REFRESH_TOKEN` | 2단계에서 나온 값 |
| `GH_PAT` | `repo` 권한 Personal Access Token — 토큰 자동 갱신용 |

Variables (`Variables` 탭, 선택사항):

| 이름 | 기본값 | 설명 |
|---|---|---|
| `START_DATE` | `2026-01-01` | 연재 시작일(KST). 이 날이 0일차 |
| `TRACK_PATTERN` | `kr,en` | 편성 순서. `kr,kr,en`이면 사흘 중 이틀이 한국 작품 |

> `GH_PAT`가 왜 필요한가: 카카오 refresh token은 2개월 만료다. 만료가
> 1개월 이내로 남으면 갱신 요청 응답에 새 토큰이 함께 오는데, 이걸 Secret에
> 다시 써넣어야 연재가 끊기지 않는다. Actions 기본 `GITHUB_TOKEN`은 Secret을
> 쓸 권한이 없어서 별도 PAT가 필요하다. 없으면 2개월마다 2단계를 다시 하면 된다.

### 4. 첫 발송 확인

**Actions → 매일 발송 → Run workflow**에서 `dry_run`을 켜고 한 번 돌려
로그에 오늘 분량이 제대로 찍히는지 확인한다. 그다음 `dry_run`을 끄고
다시 돌리면 실제로 카톡이 온다.

이후로는 **매일 오전 8시(KST)** 자동 발송된다.

---

## 로컬에서 돌려보기

```bash
pip install -r requirements.txt -r requirements-dev.txt

# 보내지 않고 미리보기만
DRY_RUN=1 START_DATE=2026-01-01 python -m src.main

# 테스트
python -m pytest tests -q
```

---

## 원문 채우기 (권장)

기본으로 들어 있는 건 **손으로 고른 시드 구절**이라 분량이 얇다. 특히 한국
트랙은 8조각뿐이다. 전문을 받아오면 작품 하나가 수십~수백 조각으로 늘어난다.

**GitHub Actions에서 (로컬 환경 불필요)**

**Actions → 코퍼스 수집·빌드 → Run workflow**

**로컬에서**

```bash
python scripts/fetch_sources.py       # 위키문헌 · Gutenberg에서 전문 수집
python scripts/verify_passages.py --write   # 시드 구절을 원문과 대조
python scripts/build_corpus.py        # data/segments.json 재생성
```

한국 트랙은 전문이 있으면 자동 분할한 조각이 시드를 **대체**한다.
해외 트랙은 원문과 번역이 1:1로 짝지어져야 해서 늘 손으로 고른 구절을 쓴다.

### 시드 구절의 검증 상태

`data/passages/*.json`의 `verified` 필드가 이걸 나타낸다.

- `false` — **아직 원문과 대조하지 않았다.** 저장소에 처음 들어간 구절은
  전부 이 상태다. 기억에 의존해 옮겨 적은 것이라 표기나 띄어쓰기가 판본과
  다를 수 있다.
- `true` — `verify_passages.py`가 실제 출처 전문과 글자 단위로 대조해 통과했다.

`verify_passages.py`는 문장부호 이형(`“ ” … —` 등)만 정규화하고 나머지는
그대로 비교하므로, 통과했다면 그 구절은 원문과 같다고 봐도 된다.
**한 번은 꼭 돌려서 `true`로 만들어 두는 걸 권한다.**

---

## 작품 추가하기

1. `data/works.json`의 `works` 배열에 항목 추가

   ```json
   {
     "id": "melville_moby_dick",
     "track": "en",
     "title": "모비 딕",
     "title_original": "Moby Dick",
     "author": "Herman Melville",
     "author_ko": "허먼 멜빌",
     "author_death": 1891,
     "published": 1851,
     "source_url": "https://www.gutenberg.org/ebooks/2701",
     "source": { "type": "gutenberg", "ebook_id": 2701 }
   }
   ```

   `author_death`는 저작권 만료 판단 근거다. 테스트가 사후 70년을 넘겼는지
   자동으로 확인하고, 안 넘겼으면 실패한다.

2. 해외 작품이면 `data/passages/<id>.json`에 원문·번역·해설을 짝지어 넣는다

   ```json
   {
     "work_id": "melville_moby_dick",
     "verified": false,
     "passages": [
       {
         "text": "Call me Ishmael.",
         "text_ko": "나를 이슈메일이라 불러 다오.",
         "note": "세 단어로 시작하는 유명한 첫 문장. 본명을 밝히지 않고 호칭만 청한다."
       }
     ]
   }
   ```

   한국 작품이면 `text`만 넣거나, 아예 넣지 않고 `fetch_sources.py`에 맡겨도 된다.

3. 다시 빌드

   ```bash
   python scripts/build_corpus.py
   python -m pytest tests -q
   ```

   200자를 넘는 조각이 하나라도 있으면 빌드가 실패한다. 새벽에 발송이 깨지는
   것보다 낫다.

---

## 동작 방식

### 오늘 뭘 보낼지 정하는 법

진행 상태를 파일에 저장하지 않는다. 날짜에서 바로 계산한다.

```
day_index = (오늘 KST − START_DATE).days
track     = TRACK_PATTERN[day_index % len(TRACK_PATTERN)]
seq       = (그날까지 해당 트랙이 등장한 횟수) % 트랙 조각 수
```

덕분에

- 같은 날 두 번 돌려도 같은 내용이 나온다 (멱등)
- 하루 걸러도 다음 날 알아서 제자리를 찾는다
- 진행 상태를 저장소에 커밋할 필요가 없다
- 코퍼스를 다 돌면 처음부터 다시 연재한다

### 토큰 수명

| | 유효기간 | 처리 |
|---|---|---|
| access token | 12~24시간 | 매 실행마다 새로 발급 |
| refresh token | 2개월 | 만료 1개월 전부터 갱신 응답에 새 값이 함께 옴 → Secret 자동 교체 |

매일 실행되므로 사실상 갱신이 끊길 일이 없다.

---

## 저작권

- 저작권 보호기간(**사후 70년**)이 끝난 작품만 싣는다.
- 해외 고전은 **원문**을 쓴다. 시중 한국어 번역본은 번역 저작권이 따로
  살아 있어서 쓸 수 없다. 함께 나가는 한국어 해석은 이 저장소에서 새로 쓴 것이다.
- `data/works.json`의 `author_death`가 근거이고, 테스트가 이를 강제한다.
- 러시아·프랑스 작품의 **영역본**을 쓰려면 원저자뿐 아니라 **번역자의**
  사망연도도 확인해야 한다.

---

## 문제 해결

| 증상 | 원인과 해결 |
|---|---|
| `insufficient scopes` | 카카오 콘솔 동의항목에서 `talk_message`가 꺼져 있다. 켜고 `get_token.py`를 다시 실행 |
| `invalid_grant` / `refresh token expired` | refresh token이 만료됐다. `get_token.py`로 재발급 후 Secret 교체 |
| 워크플로는 성공인데 카톡이 안 온다 | 카카오톡 '나와의 채팅'을 확인. 다른 기기에 로그인된 계정으로 인가했을 수 있다 |
| 발송 시각이 8시가 아니다 | GitHub Actions 크론은 부하에 따라 수 분~수십 분 늦게 뜬다. 정시가 중요하면 개인 서버 crontab으로 옮기면 된다 (`python -m src.main`만 실행하면 됨) |
| `새 refresh token이 발급됐지만 GH_PAT가 없어…` | `GH_PAT` Secret을 등록하거나, `get_token.py`로 직접 재발급 |
| 빌드가 200자 초과로 실패 | 해당 구절을 `data/passages/`에서 더 짧게 나눈다 |

---

## 구조

```
src/
  config.py      환경변수 → 설정
  kakao.py       토큰 갱신 + 나에게 보내기 API
  corpus.py      코퍼스 로딩, 날짜 → 조각 결정
  message.py     200자 말풍선 조립
  main.py        진입점
scripts/
  get_token.py       [최초 1회] OAuth 인가 → refresh token
  fetch_sources.py   위키문헌 · Gutenberg에서 전문 수집
  verify_passages.py 시드 구절을 원문과 대조
  build_corpus.py    segments.json 빌드 (200자 검증 포함)
data/
  works.json      작품 메타 (저작권 근거 포함)
  passages/       손으로 고른 구절 + 번역 + 해설
  sources/        수집한 전문 (gitignore, 캐시)
  segments.json   빌드 산출물 — 실제 발송이 읽는 파일
```
