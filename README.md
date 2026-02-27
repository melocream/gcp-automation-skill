# GCP Automation Skill for Claude Code

**Claude Code + Google Cloud Run + Cloud Scheduler**로 n8n/Zapier 없이 서버리스 자동화를 구축하는 스킬 패키지입니다.

---

## 이게 뭔가요?

Claude Code에게 "XX를 매일 자동으로 돌려줘"라고 말하면, 이 스킬을 참조해서:
1. Python 배치 함수 작성
2. Flask 엔드포인트 등록
3. Docker 이미지 빌드 & Cloud Run 배포
4. Cloud Scheduler 등록

까지 **한 번에** 만들어줍니다.

```
사용자: "환율 데이터 매일 아침 9시에 수집해줘"
       ↓
Claude Code: 이 스킬 참조 → 코드+배포+스케줄러 자동 생성
       ↓
결과: Cloud Scheduler → Cloud Run → 매일 09:00 자동 실행
```

---

## 보통은 어떻게 하나요? — 일반적인 GCP 스케줄링 방법

GCP에서 "매일 9시에 데이터를 수집해라"를 구현하려면, 일반적으로 아래 중 하나를 거칩니다.

### 방법 1: GCP Console UI에서 직접 설정 (가장 흔한 방법)

대부분의 튜토리얼과 강의에서 알려주는 방식입니다.

```
1. GCP Console 접속 → Cloud Functions 메뉴
2. "함수 만들기" 버튼 클릭
3. 런타임 선택 (Python 3.11)
4. 브라우저 에디터에서 코드 작성 (main.py, requirements.txt)
5. 배포 버튼 클릭 → 빌드 대기 (~5분)
6. Cloud Scheduler 메뉴 이동
7. "작업 만들기" 클릭
8. cron 표현식 입력, URL 복사/붙여넣기, 인증 설정
9. 만들기 클릭
```

**문제점:**
- 코드를 브라우저에서 작성 → 자동완성, 린팅, 테스트 없음
- 코드가 GCP Console 안에만 존재 → git 버전관리 불가
- 수정할 때마다 Console 들어가서 에디터 열고 재배포
- 환경이 바뀌면 처음부터 다시 UI 클릭
- **함수가 10개 넘어가면 관리 불가능**

### 방법 2: BigQuery 예약 쿼리

데이터 변환/집계 작업을 BigQuery 안에서 스케줄링하는 방법입니다.

```
1. BigQuery Console 접속
2. SQL 쿼리 작성
3. "예약" 버튼 클릭
4. 반복 일정 설정 (매일 09:00 등)
5. 대상 테이블 지정
```

**제한:**
- SQL만 실행 가능 → 외부 API 호출, 파일 처리, AI 분석 불가
- 단순 ETL(Extract-Transform-Load)에만 적합
- 복잡한 비즈니스 로직은 표현 불가

### 방법 3: Terraform/IaC

인프라를 코드로 관리하는 방법입니다.

```hcl
resource "google_cloud_scheduler_job" "my_job" {
  name     = "my-job"
  schedule = "0 9 * * 1-5"
  http_target {
    uri         = "https://my-service.run.app/run-my-job"
    http_method = "POST"
  }
}
```

**문제점:**
- Terraform 문법 별도 학습 필요 (HCL)
- 인프라 코드와 비즈니스 코드가 분리 → 2곳 관리
- 개인/소규모 프로젝트에는 과도한 복잡성
- 배포 파이프라인(CI/CD) 별도 구성 필요

### 방법 4: n8n / Zapier / Make

비주얼 워크플로우 빌더를 사용하는 방법입니다.

```
1. n8n 설치 (Docker 또는 Cloud 플랜 $24+/월)
2. 워크플로우 캔버스에서 노드 드래그&드롭
3. HTTP Request 노드 → Code 노드 → BigQuery 노드 연결
4. cron 트리거 노드 설정
5. 활성화
```

**제한:**
- 복잡한 로직(조건분기, 반복, 에러처리)을 노드 조합으로 표현 → 스파게티
- 코드 노드에서 Python 쓸 수 있지만 외부 패키지 제한
- git 관리 안 됨 (export/import 수동)
- 노드 10개 넘으면 가독성 급락
- 로컬 디버깅 불가

---

## Code-First 자동화 — 이 스킬의 접근법

위 방법들의 공통 불편함:
- **UI 의존** (Console 클릭, 비주얼 에디터)
- **코드 관리 안 됨** (git 없음, 히스토리 없음)
- **테스트 어려움** (로컬에서 실행해볼 수 없음)
- **확장 한계** (작업이 늘어나면 관리 불가능)

이 스킬은 **코드 한 곳**에서 전부 해결합니다.

### 핵심 아이디어

```
"모든 자동화는 결국 Python 함수다.
 함수를 HTTP로 감싸면 Cloud Run이 되고,
 Cloud Run에 cron을 걸면 자동화가 된다."
```

### 전체 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ① Python 함수 작성          ② Flask 엔드포인트 등록            │
│                                                                 │
│  def collect_data():         @app.route('/run-collect')         │
│      api 호출                def run_collect():                 │
│      데이터 가공                  result = collect_data()       │
│      DB 저장                     return jsonify(result)         │
│                                                                 │
│  ③ Docker + Cloud Run 배포   ④ Cloud Scheduler 등록             │
│                                                                 │
│  gcloud builds submit        gcloud scheduler jobs create       │
│  gcloud run deploy             --schedule="0 9 * * 1-5"        │
│                                --uri=".../run-collect"          │
│                                                                 │
│  ⑤ 매일 09:00 자동 실행!                                        │
│                                                                 │
│  Cloud Scheduler ──HTTP POST──→ Cloud Run ──→ Python 함수       │
│  (cron 트리거)                  (서버리스)     (비즈니스 로직)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Console UI vs Code-First 비교

| 단계 | Console UI 방식 | Code-First 방식 |
|------|----------------|----------------|
| 코드 작성 | GCP Console 브라우저 에디터 | **로컬 IDE** (자동완성, 린팅) |
| 테스트 | 배포 후에야 확인 가능 | **로컬에서 바로 실행** (`--dry-run`) |
| 배포 | Console에서 버튼 클릭 | **터미널 한 줄** (`bash deploy.sh`) |
| 스케줄 등록 | Console → Scheduler → 폼 입력 | **터미널 한 줄** (`bash create_scheduler.sh`) |
| 코드 수정 | Console 다시 열기 → 재배포 | **파일 수정 → git commit → deploy** |
| 코드 관리 | Console 안에만 존재 | **git 버전관리** |
| 작업 10개 관리 | 10개 서비스 각각 Console에서 | **1개 파일**에 10개 라우트 |
| AI 활용 | 불가능 | **Claude Code가 코드 자동 생성** |

### Claude Code가 바꾸는 것

전통적인 Code-First 도구(Terraform, Pulumi, serverless framework)는 **학습 곡선이 높아서** 결국 Console UI로 돌아가는 사람이 많았습니다.

```
이전: "코드로 자동화하고 싶지만 Flask, Docker, gcloud 다 배워야 하니까
      그냥 Console에서 클릭하자..."

지금: "Claude Code야, 매일 9시에 환율 수집해줘"
      → 함수 + 엔드포인트 + Dockerfile + 배포 명령어 전부 자동 생성
      → 사용자는 결과만 확인
```

코드 작성의 진입 장벽이 0이 되면서, Console UI의 유일한 장점(쉬움)이 사라집니다.

---

## 이런 자동화를 만들 수 있습니다

이 스킬 하나로 만들 수 있는 자동화 예시입니다.
모두 **같은 패턴** (Python 함수 → Flask 라우트 → Cloud Run → Scheduler)으로 구현됩니다.

### 데이터 수집

```python
# 예시: 환율 수집 (매일 09:00)
@app.route('/run-exchange-rate')     # "0 9 * * *"
# 예시: 날씨 데이터 수집 (매시간)
@app.route('/run-weather-collect')   # "0 * * * *"
# 예시: RSS/뉴스 크롤링 (30분마다)
@app.route('/run-news-ingest')       # "*/30 * * * *"
# 예시: 소셜미디어 멘션 수집 (1시간마다)
@app.route('/run-social-mentions')   # "0 * * * *"
# 예시: 경쟁사 가격 모니터링 (평일 10시, 14시)
@app.route('/run-competitor-prices') # "0 10,14 * * 1-5"
```

### AI 분석 & 생성

```python
# 예시: 수집된 뉴스 감정분석 (1시간마다)
@app.route('/run-sentiment-analysis')  # "0 * * * *"
# 예시: 블로그 포스트 자동 생성 (매일 18:00)
@app.route('/run-blog-generate')       # "0 18 * * *"
# 예시: 이미지 썸네일 자동 생성 (매시간)
@app.route('/run-thumbnail-generate')  # "0 * * * *"
# 예시: 고객 리뷰 요약 리포트 (매주 월요일)
@app.route('/run-review-summary')      # "0 9 * * 1"
```

### 알림 & 리포트

```python
# 예시: 텔레그램/Slack 일일 리포트 (매일 08:00)
@app.route('/run-daily-report')      # "0 8 * * *"
# 예시: 이메일 뉴스레터 발송 (매주 수요일)
@app.route('/run-newsletter')        # "0 10 * * 3"
# 예시: 서버 상태 체크 + 장애 알림 (5분마다)
@app.route('/run-health-check')      # "*/5 * * * *"
# 예시: 매출 일보 Slack 알림 (평일 09:00)
@app.route('/run-sales-alert')       # "0 9 * * 1-5"
```

### 콘텐츠 발행

```python
# 예시: SNS 자동 포스팅 — Threads/X/인스타 (매일 12:00, 18:00)
@app.route('/run-social-publish')    # "0 12,18 * * *"
# 예시: YouTube 커뮤니티 글 자동 게시 (매일 20:00)
@app.route('/run-youtube-community') # "0 20 * * *"
# 예시: 자동 번역 + 다국어 블로그 발행 (매일 22:00)
@app.route('/run-translate-publish') # "0 22 * * *"
```

### 데이터 관리 & 유지보수

```python
# 예시: DB 백업 (매일 새벽 03:00)
@app.route('/run-db-backup')           # "0 3 * * *"
# 예시: 30일 지난 데이터 정리 (매주 일요일)
@app.route('/run-data-cleanup')        # "0 4 * * 0"
# 예시: OAuth 토큰 자동 갱신 (매월 1일, 15일)
@app.route('/run-token-refresh')       # "0 0 1,15 * *"
# 예시: BigQuery 테이블 파티션 정리 (매월 1일)
@app.route('/run-partition-cleanup')   # "0 5 1 * *"
# 예시: 외부 API 사용량 체크 (매일 23:00)
@app.route('/run-api-usage-check')     # "0 23 * * *"
```

### 커머스 & 비즈니스

```python
# 예시: 쇼핑몰 재고 동기화 (4시간마다)
@app.route('/run-inventory-sync')    # "0 */4 * * *"
# 예시: 정산 데이터 집계 (매일 새벽 02:00)
@app.route('/run-settlement')        # "0 2 * * *"
# 예시: 쿠폰 만료 처리 (매일 00:00)
@app.route('/run-coupon-expire')     # "0 0 * * *"
# 예시: 배송 상태 추적 + 고객 알림 (2시간마다)
@app.route('/run-shipping-track')    # "0 */2 * * *"
```

**핵심: 위 예시 전부 같은 패턴입니다.** Python 함수 하나 + Flask 라우트 하나 + Scheduler cron 하나.
10개든 30개든 `batch_endpoint.py` **파일 1개**에 라우트만 추가하면 됩니다.

---

## 아키텍처 상세

```
┌──────────────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                          │
│                                                                  │
│  ┌─────────────────┐                                             │
│  │ Cloud Scheduler  │  cron: "0 9 * * 1-5"                       │
│  │                  │  cron: "*/30 * * * *"                       │
│  │  (잡 N개 등록)    │  cron: "0 */4 * * *"                       │
│  └────────┬────────┘  ...                                        │
│           │ HTTP POST (OIDC 인증)                                 │
│           ▼                                                      │
│  ┌──────────────────────────────────────────┐                    │
│  │           Cloud Run (Flask)               │                    │
│  │                                          │                    │
│  │  batch_endpoint.py                       │                    │
│  │  ├── /run-data-collect                   │                    │
│  │  ├── /run-ai-analyze                     │                    │
│  │  ├── /run-daily-report                   │                    │
│  │  ├── /run-social-publish                 │                    │
│  │  └── ... (라우트 N개)                     │                    │
│  │                                          │                    │
│  │  [서버리스: 요청 올 때만 실행, 자동 스케일] │                    │
│  └──────┬──────────┬──────────┬─────────────┘                    │
│         │          │          │                                   │
│         ▼          ▼          ▼                                   │
│  ┌──────────┐ ┌─────────┐ ┌───────────┐                         │
│  │ BigQuery  │ │ Secret  │ │ 외부 API   │                         │
│  │ Firestore │ │ Manager │ │ Gemini    │                         │
│  │ Cloud SQL │ │ (비밀값) │ │ Slack 등  │                         │
│  └──────────┘ └─────────┘ └───────────┘                         │
└──────────────────────────────────────────────────────────────────┘

[로컬 개발 환경]

  VS Code / Cursor / Claude Code
  ├── batch_endpoint.py  ← Cloud Run과 동일한 코드
  ├── scripts/batch/     ← 배치 잡 모듈
  └── python my_job.py --dry-run  ← 로컬 테스트
        │
        └── 수정 → git commit → bash deploy.sh → 끝!
```

### 왜 Cloud Functions가 아니라 Cloud Run인가?

| 항목 | Cloud Functions | Cloud Run |
|------|----------------|-----------|
| 진입점 | 함수 1개 = 서비스 1개 | **라우트 N개 = 서비스 1개** |
| 작업 10개 | 서비스 10개 관리 | **서비스 1개로 통합** |
| 타임아웃 | 최대 540초 (9분) | **최대 3600초 (60분)** |
| 런타임 | 제한된 환경 | **Docker = 어떤 패키지든 설치 가능** |
| 로컬 테스트 | 에뮬레이터 필요 | **Flask 그대로 실행** |
| 비용 | 호출당 과금 | **동일 (요청당 과금)** |

Cloud Run은 "Docker 컨테이너를 서버리스로 실행"하는 서비스입니다.
Flask 앱을 Docker에 넣으면, 요청이 올 때만 컨테이너가 실행되고 없으면 꺼집니다.
Cloud Functions는 함수 1개가 서비스 1개인데, Cloud Run은 라우트 N개가 서비스 1개.
작업이 늘어나도 관리 포인트가 늘어나지 않습니다.

---

## Flask + Cloud Scheduler 동작 원리

"Flask가 뭔데?", "Scheduler가 어떻게 코드를 실행시키는 거야?" 에 대한 답입니다.

### 핵심 개념: HTTP로 함수를 호출한다

모든 것은 결국 **HTTP 요청**입니다.

```
평소 우리가 브라우저에서 하는 것:
  브라우저 → GET https://google.com → 구글 서버가 HTML 반환

이 스킬이 하는 것:
  Cloud Scheduler → POST https://my-app.run.app/run-my-job → Flask가 Python 함수 실행 후 JSON 반환
```

원리는 완전히 같습니다. 다만 브라우저 대신 Cloud Scheduler가, HTML 대신 Python 함수 결과가 오가는 것뿐입니다.

### Flask란?

Flask는 Python으로 HTTP 서버를 만드는 가장 가벼운 프레임워크입니다.

```python
# ❶ 이게 Flask 앱의 전부입니다
from flask import Flask, jsonify

app = Flask(__name__)

# ❷ "이 URL로 요청이 오면, 이 함수를 실행해라"
@app.route('/hello')
def hello():
    return jsonify({"message": "안녕하세요!"})

# ❸ 서버 시작
app.run(port=8080)
```

이 코드를 실행하면:
```bash
$ python app.py
 * Running on http://localhost:8080

# 다른 터미널에서:
$ curl http://localhost:8080/hello
{"message": "안녕하세요!"}
```

**`@app.route('/hello')`** — 이것이 Flask의 핵심입니다.
URL 경로(`/hello`)와 Python 함수(`hello()`)를 연결합니다.
누군가 `/hello`로 HTTP 요청을 보내면, Flask가 `hello()` 함수를 실행하고 결과를 응답합니다.

### 배치 엔드포인트 = Flask + 비즈니스 로직

우리 `batch_endpoint.py`는 이 원리를 배치 작업에 적용한 것입니다:

```python
# batch_endpoint.py — 실제 구조 (단순화)
from flask import Flask, jsonify, request
app = Flask(__name__)

# ❶ 헬스 체크 (서버가 살아있는지 확인)
@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

# ❷ 환율 수집 배치
@app.route('/run-exchange-rate', methods=['POST'])  # POST만 허용
def run_exchange_rate():
    from scripts.batch.exchange_rate import ExchangeRateCollector
    collector = ExchangeRateCollector()
    result = collector.run()     # ← 여기서 실제 작업 실행
    return jsonify(result)       # ← 결과를 JSON으로 반환

# ❸ 뉴스 수집 배치
@app.route('/run-news-ingest', methods=['POST'])
def run_news_ingest():
    from scripts.batch.news_ingest import NewsIngestJob
    job = NewsIngestJob()
    result = job.run()
    return jsonify(result)

# ... 라우트를 계속 추가할 수 있음 (10개든 30개든)
```

### Cloud Scheduler가 하는 일

Cloud Scheduler는 **cron(일정) + HTTP 호출기**입니다.
등록해놓으면, 정해진 시간에 HTTP POST를 보내줍니다.

```
설정: "평일 09:00에 POST https://my-app.run.app/run-exchange-rate"

실제 일어나는 일 (매일 09:00):

  ┌──────────────────┐                    ┌──────────────────┐
  │ Cloud Scheduler   │  HTTP POST         │   Cloud Run       │
  │                   │ ─────────────────→ │   (Flask 앱)      │
  │ "09:00이다!"      │                    │                   │
  │                   │                    │ 1. POST 수신      │
  │                   │  JSON 응답          │ 2. @app.route 매칭│
  │                   │ ←───────────────── │ 3. 함수 실행      │
  │ "200 OK, 성공"    │                    │ 4. 결과 반환      │
  └──────────────────┘                    └──────────────────┘
```

### 전체 흐름을 코드로 따라가기

**1단계: Scheduler가 HTTP POST를 보냄**
```
POST https://my-app-xyz.a.run.app/run-exchange-rate
Content-Type: application/json
Authorization: Bearer eyJhbGciOi...  ← OIDC 토큰 (자동 첨부)

{}  ← body (빈 JSON 또는 파라미터)
```

**2단계: Cloud Run이 Flask 앱으로 요청 전달**
```python
# Flask가 URL 매칭: /run-exchange-rate → run_exchange_rate()
@app.route('/run-exchange-rate', methods=['POST'])
def run_exchange_rate():
    # request.get_json()으로 body 읽기 가능
    data = request.get_json(silent=True) or {}
```

**3단계: 비즈니스 로직 실행**
```python
    # 실제 작업 수행
    collector = ExchangeRateCollector()
    result = collector.run()
    # result = {"collected": 4, "rates": {"KRW": 1350.5, ...}}
```

**4단계: JSON 응답 반환**
```python
    return jsonify(build_response('success', result=result))
    # → {"status": "success", "result": {"collected": 4, ...}, "timestamp": "..."}
```

**5단계: Scheduler가 응답 확인**
```
HTTP 200 → "성공" (다음 스케줄까지 대기)
HTTP 500 → "실패" (설정에 따라 재시도)
```

### Flask vs 우리가 쓰는 부분

Flask는 거대한 웹 프레임워크이지만, 우리가 배치 서버로 쓸 때 필요한 건 딱 3개뿐입니다:

```python
from flask import Flask, jsonify, request

Flask    → 앱 객체 만들기, @app.route로 URL 등록
jsonify  → Python dict를 JSON 응답으로 변환
request  → 들어온 HTTP 요청의 body/headers 읽기
```

나머지 Flask 기능(템플릿 렌더링, 세션, 쿠키 등)은 사용하지 않습니다.
배치 서버에서 Flask는 "URL과 함수를 연결해주는 라우터" 역할만 합니다.

### Gunicorn은 왜 필요한가?

```
개발 시:  python batch_endpoint.py  → Flask 내장 서버 (1명만 처리 가능)
배포 시:  gunicorn batch_endpoint:app → 프로덕션 서버 (다중 요청 처리)
```

Flask 내장 서버는 개발용입니다. 프로덕션에서는 Gunicorn이 Flask 앱을 감싸서
안정적으로 실행합니다. Dockerfile에서 `gunicorn batch_endpoint:app`이 하는 일:

```
gunicorn
  ├── batch_endpoint:app  → "batch_endpoint.py 파일의 app 변수를 실행해라"
  ├── --workers 1          → 워커 프로세스 1개 (배치는 동시 요청 적음)
  ├── --threads 8          → 스레드 8개 (I/O 대기 시 활용)
  └── --timeout 900        → 15분 타임아웃 (배치 작업이 오래 걸릴 수 있음)
```

### 로컬에서 테스트하는 법

Cloud Run에 배포하기 전에 로컬에서 동일하게 테스트할 수 있습니다:

```bash
# 터미널 1: Flask 서버 실행
$ python batch_endpoint.py
 * Running on http://localhost:8080

# 터미널 2: Scheduler 역할을 curl로 대신
$ curl -X POST http://localhost:8080/run-exchange-rate
{"status": "success", "result": {"collected": 4}, "timestamp": "..."}

# body가 필요한 경우
$ curl -X POST http://localhost:8080/run-my-job \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

Cloud Scheduler가 하는 일을 `curl`로 똑같이 재현할 수 있습니다.
이것이 이 패턴의 가장 큰 장점 — **로컬 = 클라우드, 동일한 코드**.

---

## 자동화 추가 전체 과정

새로운 자동화를 추가하는 5단계입니다.
Claude Code를 사용하면 **1~3단계는 대화 한 번**으로 끝납니다.

### Step 1: 배치 함수 작성

```python
# scripts/batch/exchange_rate.py
import requests
import logging

log = logging.getLogger(__name__)

class ExchangeRateCollector:
    def __init__(self, test_mode=False):
        self.test_mode = test_mode

    async def run(self):
        log.info("환율 데이터 수집 시작")
        resp = requests.get("https://api.exchangerate.host/latest?base=USD")
        rates = resp.json()["rates"]
        target = {k: rates[k] for k in ["KRW", "JPY", "EUR", "CNY"]}

        if not self.test_mode:
            self._save_to_db(target)

        return {"collected": len(target), "rates": target}

    def _save_to_db(self, data):
        pass  # BigQuery, Firestore 등에 저장
```

### Step 2: 엔드포인트 등록

```python
# batch_endpoint.py에 추가
@app.route('/run-exchange-rate', methods=['POST'])
def run_exchange_rate():
    try:
        logger.info("=== 환율 수집 시작 ===")
        from scripts.batch.exchange_rate import ExchangeRateCollector
        collector = ExchangeRateCollector(test_mode=get_test_mode())
        result = run_async(collector.run())
        return jsonify(build_response('success', result=result))
    except Exception as e:
        logger.error("환율 수집 실패: %s", e)
        traceback.print_exc()
        return jsonify(build_response('error', error=e)), 500
```

### Step 3: 로컬 테스트

```bash
# Flask 서버 로컬 실행
python batch_endpoint.py

# 다른 터미널에서 테스트
curl -X POST http://localhost:8080/run-exchange-rate
# → {"status": "success", "result": {"collected": 4, "rates": {"KRW": 1350.5, ...}}}
```

### Step 4: 배포

```bash
bash scripts/deploy.sh
# → Cloud Build → Cloud Run 배포 → 완료
```

### Step 5: 스케줄러 등록

```bash
bash scripts/create_scheduler.sh \
  my-exchange-rate \
  "0 9 * * 1-5" \
  "/run-exchange-rate"
# → 평일 매일 09:00에 자동 실행!
```

**끝.** 이제 매일 아침 9시에 환율이 자동 수집됩니다.
같은 방식으로 라우트를 추가하면 10개, 20개 자동화도 서비스 1개로 관리됩니다.

---

## n8n/Zapier vs Code-First 비교

| 항목 | n8n/Zapier | Code-First + Claude Code |
|------|-----------|--------------------------|
| 코드 관리 | UI에서 수동 관리 | **git 버전관리** |
| 디버깅 | 제한된 UI 로그 | **로컬 실행 + Cloud Logging** |
| 복잡한 로직 | 노드 조합 한계 (스파게티) | **Python 무제한 자유도** |
| 비용 | n8n Cloud $24+/월 | **Cloud Run 무료 티어** |
| 테스트 | 불가능 | **pytest + --dry-run** |
| AI 연동 | 별도 플러그인 | **Gemini/Claude 직접 호출** |
| 비밀 관리 | 자체 credential store | **Secret Manager (IAM 기반)** |
| 패키지 | 제한된 Node 런타임 | **Docker = 뭐든 설치** |
| 작업 생성 속도 | 드래그&드롭 ~30분 | **Claude Code 대화 ~5분** |
| 확장성 | 워커/메모리 제한 | **Cloud Run 자동 스케일** |

**n8n이 더 나은 경우:**
- 비개발자가 간단한 워크플로우를 만들 때
- Webhook → Slack 알림 같은 2~3 노드 수준의 단순한 연결

**Code-First가 더 나은 경우:**
- 로직이 조금이라도 복잡해질 때 (조건분기, 반복, 에러처리)
- 작업 수가 5개 이상일 때
- AI/ML이 포함된 파이프라인
- 팀 협업이 필요할 때 (git)
- 비용을 절감하고 싶을 때

---

## 비교 총정리

| 항목 | Console UI | BigQuery 예약 | n8n/Zapier | Terraform | **Code-First** |
|------|-----------|-------------|-----------|-----------|----------------|
| 학습 곡선 | 낮음 | 낮음 | 중간 | 높음 | **낮음** (Claude Code) |
| 코드 관리 | 없음 | SQL만 | 없음 | HCL 별도 | **git** |
| 로컬 테스트 | 불가 | 불가 | 불가 | 불가 | **가능** |
| 복잡한 로직 | 제한 | SQL만 | 노드 한계 | 가능 | **Python 무제한** |
| 작업 N개 관리 | N개 서비스 | N개 쿼리 | N개 워크플로우 | N개 리소스 | **파일 1개** |
| 배포 | UI 클릭 | 자동 | 자동 | CLI | **CLI 1줄** |
| 비용/월 | 무료~ | 무료~ | $24+ | 무료~ | **무료~** |
| AI 연동 | 제한 | 불가 | 플러그인 | 없음 | **직접 호출** |
| 확장성 | 낮음 | 중간 | 중간 | 높음 | **높음** |

---

## BigQuery 데이터 적재 패턴

자동화의 핵심 = **수집 → 저장**. BigQuery에 데이터를 적재할 때 가장 흔한 문제는 **중복**입니다.
매일 09시에 환율을 수집하는 배치가 있다면, 같은 날 두 번 돌았을 때 데이터가 2줄이 되면 안 됩니다.

### MERGE (Upsert) — 있으면 UPDATE, 없으면 INSERT

```python
from bigquery_helper import upsert

# 환율 데이터 예시
rows = [
    {"date": "2026-02-23", "currency": "KRW", "rate": 1350.5, "updated_at": "..."},
    {"date": "2026-02-23", "currency": "JPY", "rate": 149.2, "updated_at": "..."},
]

# date + currency 조합이 이미 있으면 rate만 UPDATE, 없으면 INSERT
upsert(
    project="my-project",
    dataset="my_dataset",
    table="exchange_rates",
    rows=rows,
    key_columns=["date", "currency"],        # 유니크 키
    update_columns=["rate", "updated_at"],   # 갱신 대상
)
```

내부적으로:
1. 임시 스테이징 테이블에 데이터 로드
2. `MERGE ... WHEN MATCHED THEN UPDATE WHEN NOT MATCHED THEN INSERT`
3. 스테이징 테이블 삭제

이렇게 하면 같은 배치를 10번 돌려도 데이터는 정확히 1줄만 남습니다.

### 테이블 자동 생성

```python
from bigquery_helper import ensure_table

# 코드에서 테이블 스키마 정의 — Console 들어갈 필요 없음
ensure_table("my-project", "my_dataset", "exchange_rates", [
    {"name": "date", "type": "DATE", "mode": "REQUIRED"},
    {"name": "currency", "type": "STRING", "mode": "REQUIRED"},
    {"name": "rate", "type": "FLOAT64"},
    {"name": "updated_at", "type": "TIMESTAMP"},
])
```

### 대량 데이터 팁

- **2,000행씩 청크**: `upsert()`가 자동으로 분할 처리
- **NaN → None**: Python `float('nan')`은 BigQuery에서 에러. 헬퍼가 자동 변환
- **date 타입**: `datetime.date` → `"YYYY-MM-DD"` 문자열로 자동 변환
- **단순 로그**: 중복이 상관없는 로그/이벤트 데이터는 `simple_insert()` 사용

`templates/bigquery_helper.py`에 `ensure_table()`, `upsert()`, `simple_insert()`, `run_query()` 전부 있습니다.

---

## 폴더 구조

```
gcp-automation-skill/
├── README.md                          # 이 파일
├── commands/
│   └── gcp-automation.md              # Claude Code 스킬 문서 (핵심)
├── templates/
│   ├── batch_endpoint.py              # Flask 엔드포인트 보일러플레이트
│   ├── batch_job_async.py             # async 배치 잡 템플릿
│   ├── batch_job_sync.py              # sync 배치 잡 템플릿
│   ├── bigquery_helper.py             # BigQuery 테이블 생성 + MERGE upsert
│   ├── secret_manager_helper.py       # Secret Manager 유틸리티
│   ├── Dockerfile                     # Cloud Run용 Dockerfile
│   ├── .dockerignore                  # Docker 빌드 시 제외 파일
│   └── requirements.txt               # Python 최소 의존성 목록
└── scripts/
    ├── deploy.sh                      # 빌드+배포 스크립트
    ├── create_scheduler.sh            # 스케줄러 등록 (create-or-update)
    └── logs.sh                        # 로그 확인 스크립트
```

---

## 설치 방법

### 1. Claude Code 스킬로 등록

프로젝트 루트의 `.claude/commands/`에 스킬 파일을 복사합니다:

```bash
mkdir -p .claude/commands
cp gcp-automation-skill/commands/gcp-automation.md .claude/commands/
```

이후 Claude Code에서 `/gcp-automation`으로 호출할 수 있습니다.

### 2. 템플릿으로 프로젝트 시작

```bash
cp templates/batch_endpoint.py my-project/
cp templates/Dockerfile my-project/
cp templates/.dockerignore my-project/
cp templates/requirements.txt my-project/
cp templates/batch_job_async.py my-project/scripts/batch/my_job.py
```

### 3. 배포 스크립트 설정

`scripts/` 폴더의 쉘 스크립트에서 변수 3개만 수정:

```bash
GCP_PROJECT="your-project-id"       # GCP 프로젝트 ID
SERVICE_NAME="your-batch-service"    # Cloud Run 서비스 이름
REGION="asia-northeast3"             # 리전
```

---

## 사전 준비

### GCP 프로젝트

1. Google Cloud 프로젝트 생성
2. 필요한 API 활성화:
   ```bash
   gcloud services enable \
     run.googleapis.com \
     cloudbuild.googleapis.com \
     cloudscheduler.googleapis.com \
     secretmanager.googleapis.com \
     --project=YOUR_PROJECT_ID
   ```
3. 서비스 계정 키 발급 (로컬 개발용):
   ```bash
   gcloud iam service-accounts keys create keys/sa-key.json \
     --iam-account=YOUR_PROJECT_ID@appspot.gserviceaccount.com
   ```

### 로컬 도구

- `gcloud` CLI: https://cloud.google.com/sdk/docs/install
- Python 3.11+
- Docker (선택 — Cloud Build 사용 시 불필요)

---

## Secret Manager로 비밀 값 관리

API 토큰, 비밀 키 등은 Secret Manager에 저장하고 Cloud Run이 자동으로 읽습니다.

```bash
# 1. 시크릿 생성
gcloud secrets create my-api-token --project=YOUR_PROJECT

# 2. 값 저장
echo -n "sk-abc123..." | gcloud secrets versions add my-api-token --data-file=-

# 3. Cloud Run에 마운트 (환경 변수로)
gcloud run deploy my-service \
  --set-secrets="API_TOKEN=my-api-token:latest"
```

코드에서는 `os.getenv("API_TOKEN")`으로 읽기만 하면 됩니다.

**자동 갱신이 필요한 토큰** (OAuth 등):
- `templates/secret_manager_helper.py`의 `refresh_and_store()` 패턴 참조
- Cloud Scheduler로 만료 전 주기적 갱신 (예: 매월 1일, 15일)

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 504 Timeout | 작업이 스케줄러 deadline 초과 | `--attempt-deadline=900s` 또는 작업 분리 |
| 첫 요청 실패 | Cold Start (컨테이너 부팅 지연) | `--min-instances=1` (~$15/월) |
| 429 Rate Limit | Cloud Run 공유 IP에서 외부 API 차단 | 요청 간 sleep, 대체 API 사용 |
| import 에러 | PYTHONPATH 누락 | Dockerfile에 `ENV PYTHONPATH=/app` |
| 30분+ 작업 타임아웃 | 단일 작업이 너무 오래 걸림 | 작업 분리 (예: KR/US 분리, 청크 처리) |

로그 확인:
```bash
bash scripts/logs.sh            # 최근 로그
bash scripts/logs.sh errors     # 에러만
bash scripts/logs.sh search "키워드"  # 검색
```

---

## FAQ

**Q: Cloud Run 비용이 걱정됩니다.**
A: Cloud Run 무료 티어가 상당히 넉넉합니다 (월 200만 요청, 36만 vCPU-초). 배치 작업 수준이면 대부분 무료 범위 안에 들어옵니다. `min-instances=1`을 설정하면 콜드 스타트를 방지하는 대신 ~$15/월 정도 들지만, 없어도 동작합니다 (첫 요청만 느림).

**Q: 작업이 30개, 50개로 늘어나면 어떡하나요?**
A: `batch_endpoint.py` 1개에 50개 라우트도 문제 없습니다. 다만 Docker 이미지 크기가 커지면 빌드 시간이 늘어나므로, 성격이 다른 작업군(예: 데이터 수집 vs 콘텐츠 발행)은 서비스를 분리하는 것이 좋습니다.

**Q: Flask 대신 FastAPI를 쓸 수 있나요?**
A: 네. `batch_endpoint.py`를 FastAPI로 작성하고, Dockerfile의 gunicorn 대신 uvicorn을 사용하면 됩니다. 다만 Cloud Scheduler는 단순 HTTP POST만 보내므로 Flask의 간결함이 배치 엔드포인트에 더 적합합니다.

**Q: AWS나 Azure에서도 같은 패턴을 쓸 수 있나요?**
A: 같은 아이디어를 적용할 수 있습니다.
- AWS: Flask → Lambda + API Gateway, Scheduler → EventBridge
- Azure: Flask → Container Apps, Scheduler → Logic Apps Timer

핵심 패턴(Python 함수 → HTTP 엔드포인트 → cron 스케줄러)은 클라우드에 독립적입니다.
