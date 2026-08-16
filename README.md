# Kakao_Daily

매일 아침 카카오톡으로(기본은 '나와의 채팅', 설정하면 친구에게도) 명작을
**챕터 한 도막(약 2,000~2,500자)** 분량씩 이어서 보내주는 자동 발송기.
매일 같은 시각에 다음 회차가 오므로, 시간을 들여 한 권을 끝까지
읽어나가는 연재 방식으로 동작한다.

- **한국 근대소설**은 원문 그대로
- **해외 고전**은 원문 전체 + 새로 쓴 한국어 번역 전체, 나란히

저작권 보호기간(사후 70년)이 끝난 작품만 싣는다. 진행 순서는 **항상
순차적**이다 — 무작위로 아무 데서나 오지 않고, 어제 멈춘 자리에서 이어진다.
요일로 언어를 나누지도 않는다 — **지금 읽고 있는 작품이 완결돼야만 다른
언어로 넘어간다.** 한국 소설 한 편을 처음부터 끝까지 다 받은 뒤에야 해외
고전으로 넘어가고, 그것도 다 끝나야 다음 한국 소설로 돌아온다.

---

## 어떻게 생겼나

카카오 텍스트 메시지는 **200자**까지만 들어간다. 그래서 하루 회차(2,000~
2,500자)를 여러 통으로 쪼개 연달아 보낸다 — 대략 10~15통. **첫 통에만**
제목·저자·진행도 헤더가 붙고, 나머지는 본문만 이어진다. 회차 끝에는
"내일 이어집니다" 또는 "오늘로 완결입니다" 안내가 자동으로 붙는다.

**한국 소설을 읽는 동안** — 원문 그대로, 10~15통

```
📖 운수 좋은 날 — 현진건 (3/6)

새침하게 흐린 품이 눈이 올 듯하더니 눈은 아니 오고
얼다가 만 비가 추적추적 내리었다.
[원문 읽기]
```
```
이날이야말로 동소문 안에서 인력거꾼 노릇을 하는
김 첨지에게는 오래간만에도 닥친 운수 좋은 날이었다.
[원문 읽기]
```
```
… (계속 이어짐, 이 회차에서 총 10~15통)
```
```
"괴상하게도 오늘은! 운수가 좋더니만……"

(내일 이어집니다)
[원문 읽기]
```

**그 소설이 끝나면, 해외 고전 한 편이 시작된다** — 원문 전체 회차 + 번역 전체 회차, 잇달아 20~30통

```
📖 The Tell-Tale Heart — Edgar Allan Poe (1/10)

True! nervous, very, very dreadfully nervous I had
been and am; but why will you say that I am mad?
[원문 읽기]
```
```
… (영어 원문 회차 계속)
```
```
🔎 고자질하는 심장 (1/10)

그래! 나는 신경이 곤두서 있었다. 지독하게, 아주
지독하게. 지금도 그렇다. 하지만 어째서 나를
미쳤다고들 하는가?
[원문 읽기]
```
```
… (한국어 번역 회차 계속, 회차 끝에 완결/계속 안내)
```

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
> 대신 카카오톡 '나와의 채팅'은 기본적으로 알림이 꺼져 있는 경우가 많다.
> 알림이 안 오면 아래 "친구에게 보내기" 절을 보거나, 카카오톡 앱에서
> 나와의 채팅방 → 채팅방 설정 → 알림 받기를 켜면 된다.

### 2. refresh token 발급 (최초 1회, 로컬에서)

```bash
git clone <이 저장소>
cd Kakao_Daily
pip install -r requirements.txt

export KAKAO_REST_API_KEY=<위에서 복사한 REST API 키>

# 카카오 로그인 > 보안 > Client Secret이 '사용함'인 경우에만 추가로 필요합니다.
# '사용 안 함'이면 넣지 마세요. 넣으면 오히려 invalid_client가 납니다.
export KAKAO_CLIENT_SECRET=<Client Secret 코드>

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
| `KAKAO_CLIENT_SECRET` | Client Secret을 '사용함'으로 켠 경우에만. 안 켰으면 등록하지 마세요 |
| `KAKAO_RECEIVER_UUIDS` | '나와의 채팅' 대신 친구에게 보내려는 경우만. 아래 "친구에게 보내기" 참고 |
| `GH_PAT` | `repo` 권한 Personal Access Token — 토큰 자동 갱신용 |

Variables (`Variables` 탭, 선택사항):

| 이름 | 기본값 | 설명 |
|---|---|---|
| `START_DATE` | `2026-08-17` | 연재 시작일(KST). 이 날이 코퍼스 맨 처음(첫 작품 1회차)이 나가는 날 |

`START_DATE`는 **코퍼스가 실제로 바뀔 때마다 오늘 날짜로 다시 맞춰야 한다.**
day_index는 "코퍼스가 며칠짜리인가"와 무관하게 그냥 오늘과 START_DATE
사이의 날짜 수라서, 코퍼스를 새로 채워 넣었는데 START_DATE를 안 건드리면
이미 몇 달치 지난 것처럼 계산돼 중간 화차부터 시작해 버린다.

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

## 친구에게 보내기 ('나와의 채팅' 알림이 안 울릴 때)

카카오톡 '나와의 채팅'은 기본적으로 알림이 꺼져 있는 경우가 많다. 가장
간단한 해결책은 카카오톡 앱에서 **나와의 채팅방 → 채팅방 설정 → 알림
받기**를 켜는 것이다. 그래도 부족하면, 알림이 잘 오는 일반 채팅으로
바꿀 수 있다 — 자신을 위한 **테스트 계정을 만들어 이 앱의 팀 멤버로
등록**하고, 그 계정에게 보내는 방식이다.

카카오는 "친구에게 메시지 보내기" API를 앱이 **비즈니스 전환(검수)되기
전까지는 앱의 팀 멤버로 등록된 카카오 계정끼리만** 허용한다. 개인
프로젝트에서 검수 없이 쓸 수 있는 사실상 유일한 방법이 이거다.
(오픈채팅방에 봇처럼 올리는 공개 API는 없다.)

### 준비

1. **카카오 개발자 콘솔 → 앱 설정 → 팀 관리**에서 테스트 계정(또는
   메시지를 받고 싶은 다른 카카오 계정)을 멤버로 추가한다.
2. **카카오톡 앱에서** 발신 계정(1단계에서 `get_token.py`를 실행한 그
   계정)과 수신 계정이 실제로 서로 **친구**여야 한다. 아니면 목록에 안 잡힌다.
3. **카카오 개발자 콘솔 → 카카오 로그인 → 동의항목**에서
   **카카오톡 친구 목록(`friends`)**을 사용 설정한다.

### uuid 조회

```bash
export KAKAO_REST_API_KEY=<REST API 키>
export KAKAO_CLIENT_SECRET=<Client Secret이 켜져 있다면>
python scripts/get_token.py --scope talk_message,friends
```

로그인 창이 뜨면 **발신 계정**(평소 쓰는 계정, `get_token.py`를 처음
돌렸던 그 계정)으로 로그인한다. 완료되면 이 앱에 연결된 친구 목록과
uuid가 함께 출력된다:

```
이 앱에 연결된 카카오톡 친구 목록
============================================================
  abcdef1234567890  —  테스트계정
```

친구가 하나도 안 뜨면 위 "준비" 1~2번을 다시 확인한다.

### 적용

GitHub Secret에 `KAKAO_RECEIVER_UUIDS`를 추가하고 방금 나온 uuid를
넣는다 (받을 사람이 여럿이면 쉼표로 구분). 이 값이 있으면 앞으로 매일
발송이 '나와의 채팅' 대신 그 친구(들)에게 간다 — `KAKAO_REFRESH_TOKEN`은
바꿀 필요 없다, 실제 발송 자체는 여전히 `talk_message` 스코프만 있으면
되기 때문이다.

로컬에서 미리 확인하려면:

```bash
KAKAO_RECEIVER_UUIDS=<위에서 확인한 uuid> DRY_RUN=1 python -m src.main
```

`DRY_RUN=1`이면 실제 API를 부르지 않으므로 uuid가 맞는지는 확인할 수
없다 — `DRY_RUN=0`으로 한 번 실제 발송해서 그 계정 카카오톡에 도착하는지
확인하는 게 가장 확실하다.

---

## 로컬에서 돌려보기

```bash
pip install -r requirements.txt -r requirements-dev.txt

# 보내지 않고 미리보기만
DRY_RUN=1 START_DATE=2026-08-17 python -m src.main

# 테스트
python -m pytest tests -q
```

---

## 원문 채우기

한국 트랙은 위키문헌 전문을 받아오면 **회차(~2,200자)로 자동 분할**된다.
전문이 없으면 손으로 채운 짧은 시드로 대체 동작하지만, 얇아서 며칠 안에
연재가 끝나 버린다 — 아래 방법으로 채워 넣는 걸 권한다.

**GitHub Actions에서 (로컬 환경 불필요, 권장)**

**Actions → 코퍼스 수집·빌드 → Run workflow**

이 워크플로는 위키문헌·Gutenberg에서 전문을 받아 `data/sources/`에
커밋하고, `data/segments.json`을 다시 빌드해 커밋까지 해 준다. 내 세션의
네트워크가 그 사이트들에 막혀 있어서, 이 저장소는 실제 원문 확보를
**GitHub Actions 러너에 위임**하는 구조로 되어 있다.

**로컬에서**

```bash
python scripts/fetch_sources.py       # 위키문헌 · Gutenberg에서 전문 수집
python scripts/verify_passages.py --write   # 손으로 채운 회차를 원문과 대조
python scripts/build_corpus.py        # data/segments.json 재생성
```

한국 트랙은 전문이 있으면 자동 분할한 회차가 시드를 **대체**한다.
해외 트랙은 원문·번역이 1:1로 짝지어져야 해서 늘 `data/passages/`에
손으로(또는 AI가) 채운 회차를 쓴다.

### `data/sources/`는 캐시가 아니다

`data/sources/*.txt`는 커밋 대상이다. 번역 작업의 근거 원문으로 계속
필요하기 때문이다 — 새 회차를 번역하거나 기존 회차를 검증할 때마다 다시
받아올 필요 없이 저장소만 보면 된다.

### 손으로 채운 회차의 검증 상태

`data/passages/*.json`의 `verified` 필드가 이걸 나타낸다.

- `false` — **아직 원문과 대조하지 않았다.**
- `true` — `verify_passages.py`가 실제 출처 전문과 글자 단위로 대조해 통과했다.
  해외 트랙 회차는 원문(`text`)을 `data/sources/`에서 그대로 잘라 쓰므로,
  검증을 통과했다면 원문 충실도는 보장된다. 번역(`text_ko`)의 품질은
  별도로 사람이 검토해야 한다.

`verify_passages.py`는 문장부호 이형(`“ ” … —` 등)만 정규화하고 나머지는
그대로 비교하므로, 통과했다면 그 회차는 원문과 같다고 봐도 된다.

---

## 다음에 번역할 작품 (진행 중인 백로그)

해외 고전은 **소설 전체를 처음부터 끝까지 순차 번역**해야 "1권을 다 읽는다"는
느낌이 난다. 장편(오만과 편견, 두 도시 이야기, 프랑켄슈타인)은 한 번에
완역하기엔 너무 커서, 우선 완역 가능한 단편(포의 「고자질하는 심장」)부터
채웠다. 나머지는 `data/works.json`의 `_backlog_en`에 후보로 남아 있다.

이어서 번역하려면:

1. `python scripts/fetch_sources.py --work <id>`로 전문을 `data/sources/`에 받는다
   (또는 **Actions → 코퍼스 수집·빌드** 실행)
2. `data/passages/<id>.json`을 회차 단위(원문 ~2,200자 + 대응 번역)로 채운다 —
   아래 "작품 추가하기"의 회차 형식을 참고
3. `_backlog_en`의 항목을 `works` 배열로 옮긴다
4. `python scripts/build_corpus.py && python -m pytest tests -q`

이 작품들은 이미 명대사 6개씩 번역이 돼 있다 (`data/passages/austen_pride_prejudice.json` 등).
전문 번역으로 바꾸기 전까지는 `works`에 없으므로 발송에 쓰이지 않는다.

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

2. 해외 작품이면 `data/passages/<id>.json`에 **회차** 단위로 원문·번역을 짝지어 넣는다.
   회차 하나가 하루 발송 분량(약 2,000~2,500자)이 된다 — 200자로 자르는 게
   아니라, 카카오 200자 말풍선 여러 통으로는 `src/message.py`가 알아서 나눈다.

   ```json
   {
     "work_id": "melville_moby_dick",
     "verified": false,
     "passages": [
       {
         "text": "Call me Ishmael. Some years ago... (약 2,000~2,500자, 문장 중간에서 끊지 않는다)",
         "text_ko": "나를 이슈메일이라 불러 다오. 몇 해 전... (원문과 같은 범위의 한국어 번역)",
         "note": "선택. 특별히 짚어줄 대목에만 짧게."
       }
     ]
   }
   ```

   `text`는 `data/sources/<id>.txt`(전문)에서 그대로 잘라 써야 `verify_passages.py`로
   원문 충실도를 검증할 수 있다. 한 편을 통째로 옮길 때는
   `src.wrap.bundle_into_installments(전문, target_chars=2200, hard_cap_chars=2800)`를
   호출해 회차 경계를 자동으로 나눈 뒤, 그 경계에 맞춰 번역을 채우면 수월하다.

   한국 작품이면 `text`만 넣거나, 아예 넣지 않고 `fetch_sources.py`에 맡겨도 된다.

3. 다시 빌드

   ```bash
   python scripts/build_corpus.py
   python -m pytest tests -q
   ```

   말풍선 하나가 200자를 넘거나 하루 발송이 `MAX_BUBBLES_PER_DAY`(24통)를
   넘으면 빌드가 실패한다. 새벽에 발송이 깨지는 것보다 낫다.

---

## 동작 방식

### 오늘 뭘 보낼지 정하는 법

진행 상태를 파일에 저장하지 않는다. 날짜에서 바로 계산한다.

```
day_index = (오늘 KST − START_DATE).days
segment   = queue[day_index % len(queue)]
```

`queue`는 발송 순서 그대로 미리 하나로 엮어 둔 배열이다(`data/segments.json`의
`queue` 필드, `scripts/build_corpus.py`가 만든다). **요일로 언어를 나누지
않는다** — 지금 읽고 있는 작품이 완결돼야만 언어가 바뀐다:

```
봄·봄(5일) → 고자질하는 심장(10일, 그때 해외에 새 작품이 있어서) →
운수 좋은 날(6일) → 날개(9일, 해외에 더 없어서 계속 한국) → (처음으로)
```

해외 트랙에 완역작이 여러 편 쌓이면, 그중 다음 작품으로 자연스럽게
넘어간다. 지금은 완역작이 하나뿐이라 한국 트랙 작품 두 개가 연달아 오는
구간이 있다 — 버그가 아니라, "다른 언어에 새 작품이 없으면 지금 언어를
계속한다"는 규칙이 그대로 적용된 것이다.

`queue`에서 고른 **회차 하나**(~2,000~2,500자)가 그날 발송 전체다. 카카오
200자 제한 때문에 이 회차를 여러 말풍선으로 쪼개 연달아 보낸다
(`src/message.py`). 진행 순서는 항상 이 계산대로 정해지므로 **무작위로
섞이지 않는다** — 어제 멈춘 문장 바로 다음부터 이어진다.

덕분에

- 같은 날 두 번 돌려도 같은 내용이 나온다 (멱등)
- 하루 걸러도 다음 날 알아서 제자리를 찾는다
- 진행 상태를 저장소에 커밋할 필요가 없다
- 코퍼스를 다 돌면 처음부터 다시 연재한다

**주의**: 코퍼스(`queue`)가 바뀌면 `START_DATE`도 그 시점 날짜로 다시
맞춰야 한다. 안 그러면 이미 지난 날짜만큼 큐를 훌쩍 건너뛴 지점부터
시작해 버린다 — 작품이 처음부터가 아니라 중간부터 오는 것처럼 보이는
증상이 바로 이거다.

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
| `invalid_client` (KOE010) | ① Client Secret을 '사용함'으로 켜 뒀는데 `KAKAO_CLIENT_SECRET`을 안 넣었다 (또는 그 반대) ② REST API 키가 아니라 네이티브/JavaScript/Admin 키를 넣었다 ③ 키에 공백·줄바꿈이 섞였다 |
| `KOE006` | Redirect URI가 콘솔에 등록돼 있지 않다. `http://localhost:8080/callback`을 끝 슬래시까지 똑같이 등록 |
| `insufficient scopes` | 카카오 콘솔 동의항목에서 `talk_message`가 꺼져 있다. 켜고 `get_token.py`를 다시 실행 (동의항목을 바꿔도 기존 토큰에는 반영되지 않는다) |
| `invalid_grant` / `refresh token expired` | refresh token이 만료됐다. `get_token.py`로 재발급 후 Secret 교체 |
| 워크플로는 성공인데 카톡이 안 온다 (나와의 채팅) | 카카오톡 '나와의 채팅'을 확인. 다른 기기에 로그인된 계정으로 인가했을 수 있다 |
| 워크플로는 성공인데 친구에게 메시지가 안 온다 | `-401`/`KOE005`: 발신·수신 계정 모두 콘솔 팀 관리에 멤버로 등록됐는지, 카카오톡에서 실제로 서로 친구인지 확인 |
| `get_token.py --scope ...,friends`에서 친구 목록이 비어 있다 | 로그인한 계정(발신 계정)과 받으려는 계정이 카카오톡에서 서로 친구가 아니거나, 받으려는 계정이 팀 멤버로 등록 안 됐다 |
| 발송 시각이 8시가 아니다 | GitHub Actions 크론은 부하에 따라 수 분~수십 분 늦게 뜬다. 정시가 중요하면 개인 서버 crontab으로 옮기면 된다 (`python -m src.main`만 실행하면 됨) |
| `새 refresh token이 발급됐지만 GH_PAT가 없어…` | `GH_PAT` Secret을 등록하거나, `get_token.py`로 직접 재발급 |
| 빌드가 200자 초과로 실패 | `src/message.py`의 분할 로직 버그 가능성 — 회차 텍스트 자체는 200자 넘어도 된다 (여러 통으로 쪼개진다), 말풍선 하나가 넘으면 실패다 |
| 빌드가 "하루에 N통이나 보낸다"로 실패 | 회차가 너무 길다. `data/passages/`에서 회차를 둘로 나누거나, `bundle_into_installments`의 `target_chars`를 줄인다 |

---

## 구조

```
src/
  config.py      환경변수 → 설정
  kakao.py       토큰 갱신 + 나에게/친구에게 보내기 API
  corpus.py      코퍼스 로딩, 날짜 → 회차 결정
  wrap.py        문장 경계를 지키는 텍스트 분할 (말풍선 단위 + 회차 단위)
  message.py     회차 → 200자 말풍선 여러 통 (헤더는 첫 통에만, 끝에 완결/계속 안내)
  main.py        진입점
scripts/
  get_token.py       [최초 1회] OAuth 인가 → refresh token (+ --scope로 친구 uuid 조회)
  fetch_sources.py   위키문헌 · Gutenberg에서 전문 수집
  verify_passages.py 회차 원문을 소스와 대조
  build_corpus.py    segments.json 빌드 (회차 자동 분할 + 200자/통수 검증)
data/
  works.json      작품 메타 (저작권 근거 포함) + 번역 대기 백로그
  passages/       회차 단위 원문 + 번역 (해외 트랙은 항상 이걸 씀)
  sources/        수집한 전문 — 커밋 대상. 캐시 아님, 번역 근거 자료
  segments.json   빌드 산출물 — 실제 발송이 읽는 파일
```
