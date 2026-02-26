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

## 우리는 어떻게 하나요? — Code-First 자동화

위의 모든 방법에서 공통적으로 불편한 점이 있습니다:
- **UI 의존** (Console 클릭, 비주얼 에디터)
- **코드 관리 안 됨** (git 없음, 히스토리 없음)
- **테스트 어려움** (로컬에서 실행해볼 수 없음)
- **확장 한계** (작업이 늘어나면 관리 불가능)

우리 방식은 이 모든 걸 **코드 한 곳**에서 해결합니다.

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
│      BigQuery 저장                return jsonify(result)        │
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

### 일반적인 방법 vs 우리 방법 비교

같은 작업을 구현한다고 가정합니다: **"매일 아침 9시에 주가 데이터를 수집해서 BigQuery에 저장"**

| 단계 | Console UI 방식 | Code-First 방식 (우리) |
|------|----------------|----------------------|
| 코드 작성 | GCP Console 브라우저 에디터 | **로컬 VS Code / Cursor** (자동완성, 린팅) |
| 테스트 | 배포 후에야 테스트 가능 | **로컬에서 바로 실행** (`python my_job.py --dry-run`) |
| 배포 | Console에서 버튼 클릭 | **터미널 한 줄** (`bash deploy.sh`) |
| 스케줄 등록 | Console → Scheduler → 폼 입력 | **터미널 한 줄** (`bash create_scheduler.sh ...`) |
| 코드 수정 | Console 에디터 열기 → 수정 → 재배포 | **파일 수정 → git commit → deploy.sh** |
| 코드 관리 | Console 안에만 존재 | **git 버전관리** (히스토리, 브랜치, PR) |
| 비밀 관리 | Console → 환경변수 직접 입력 | **Secret Manager** (코드로 관리) |
| 작업 10개 관리 | 10개 함수 각각 Console에서 관리 | **batch_endpoint.py 1개 파일**에 10개 라우트 |
| 협업 | 공유 어려움 | **git push → 누구나 동일 환경** |
| AI 활용 | 불가능 | **Claude Code가 코드 자동 생성** |

### Claude Code가 바꾸는 것

전통적인 Code-First 방식도 있었습니다 — Terraform, Pulumi, serverless framework 등.
하지만 이런 도구들은 **학습 곡선이 높고 설정이 복잡해서** 결국 Console UI로 돌아가는 사람이 많았습니다.

**Claude Code가 이 문제를 해결합니다:**

```
이전: "코드로 자동화하고 싶지만 Flask, Docker, gcloud 명령어 다 배워야 하니까
      그냥 Console에서 클릭하자..."

지금: "Claude Code야, 매일 9시에 환율 수집해줘"
      → Claude Code가 함수 + 엔드포인트 + Dockerfile + 배포 명령어 전부 생성
      → 사용자는 결과만 확인
```

코드 작성의 진입 장벽이 사실상 0이 되면서, Console UI의 유일한 장점(쉬움)이 사라집니다.

---

## 실전 예시: 16개 자동화를 1개 파일로

이 스킬을 사용해서 실제로 운영 중인 StockAI Platform의 자동화 목록입니다.
**batch_endpoint.py 파일 1개** 안에 16개 라우트가 들어있고, 각각 Cloud Scheduler가 트리거합니다.

```python
# batch_endpoint.py — 실제 운영 코드 구조

@app.route('/run-news-ingest')         # 30분마다: RSS 뉴스 수집
@app.route('/run-ai-analyze')          # 30분마다: Gemini AI 감정분석
@app.route('/run-signal-generate')     # 매시간: ML 매매 시그널 생성
@app.route('/run-signal-generate-us')  # 매일 08:00: US 시그널 생성
@app.route('/run-prices-increment-kr') # 매일 06:20: 한국 주가 수집
@app.route('/run-prices-increment-us') # 매일 06:30: 미국 주가 수집
@app.route('/run-technical-increment') # 매일 06:40: 기술지표 계산
@app.route('/run-fundamental-refresh') # 매주 월요일: 재무 데이터
@app.route('/run-dedap-refresh')       # 4시간마다: 공포탐욕 지표
@app.route('/run-signal-evaluate')     # 매일 07:00: 시그널 성과 평가
@app.route('/run-supply-demand')       # 매일 16:00: 수급 데이터
@app.route('/run-telegram-briefing')   # 하루 4회: 텔레그램 뉴스 브리핑
@app.route('/run-twitter-curation')    # 하루 3회: X 큐레이션
@app.route('/run-threads-generate')    # 매일 20:00: Threads 드래프트 생성
@app.route('/run-threads-publish')     # 매일 21:00: Threads 발행
@app.route('/run-threads-token-refresh') # 매월 1,15일: 토큰 자동 갱신
```

이걸 Console UI로 관리한다면?
- Cloud Functions 16개를 각각 브라우저에서 관리
- 코드 수정할 때마다 16번 Console 에디터 열기
- 환경 변수 16번 각각 설정
- 에러 발생하면 16개 로그를 각각 확인

Code-First로 관리하면?
- **파일 1개** (batch_endpoint.py)에 16개 라우트
- **배포 1번** (`bash deploy.sh`)이면 16개 전부 업데이트
- **git log**로 모든 변경 이력 추적
- **1개 터미널**에서 모든 로그 확인 (`bash logs.sh`)

---

## 아키텍처 상세

```
┌──────────────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                          │
│                                                                  │
│  ┌─────────────────┐                                             │
│  │ Cloud Scheduler  │  cron: "0 9 * * 1-5"                       │
│  │                  │  cron: "*/30 * * * *"                       │
│  │  (잡 16개 등록)   │  cron: "0 */4 * * *"                       │
│  └────────┬────────┘  ...                                        │
│           │ HTTP POST (OIDC 인증)                                 │
│           ▼                                                      │
│  ┌──────────────────────────────────────────┐                    │
│  │           Cloud Run (Flask)               │                    │
│  │                                          │                    │
│  │  batch_endpoint.py                       │                    │
│  │  ├── /run-news-ingest     → NewsIngest   │                    │
│  │  ├── /run-ai-analyze      → AIAnalyze    │                    │
│  │  ├── /run-prices-kr       → PricesKR     │                    │
│  │  ├── /run-signal-generate → SignalGen    │                    │
│  │  └── ... (16개 라우트)                    │                    │
│  │                                          │                    │
│  │  [서버리스: 요청 올 때만 실행, 자동 스케일] │                    │
│  └──────┬──────────┬──────────┬─────────────┘                    │
│         │          │          │                                   │
│         ▼          ▼          ▼                                   │
│  ┌──────────┐ ┌─────────┐ ┌───────────┐                         │
│  │ BigQuery  │ │ Secret  │ │ 외부 API   │                         │
│  │ (데이터)  │ │ Manager │ │ (Naver,   │                         │
│  │          │ │ (비밀값) │ │  AV, RSS) │                         │
│  └──────────┘ └─────────┘ └───────────┘                         │
└──────────────────────────────────────────────────────────────────┘

[로컬 개발 환경]

  VS Code / Cursor
  ├── batch_endpoint.py  ← 동일한 코드
  ├── scripts/batch/     ← 동일한 배치 잡
  └── python my_job.py --dry-run  ← 로컬 테스트
        │
        └── 수정 → git commit → bash deploy.sh → 끝!
```

### 왜 Cloud Functions가 아니라 Cloud Run인가?

| 항목 | Cloud Functions | Cloud Run |
|------|----------------|-----------|
| 진입점 | 함수 1개 = 서비스 1개 | **라우트 N개 = 서비스 1개** |
| 작업 16개 | 서비스 16개 관리 | **서비스 1개로 통합** |
| 타임아웃 | 최대 540초 (9분) | **최대 3600초 (60분)** |
| 런타임 | 제한된 환경 | **Docker = 어떤 패키지든 가능** |
| 로컬 테스트 | 에뮬레이터 필요 | **Flask 그대로 실행** |
| 비용 | 호출당 과금 | **동일 (요청당 과금)** |

Cloud Run은 "Docker 컨테이너를 서버리스로 실행"하는 서비스입니다.
Flask 앱을 Docker에 넣으면, 요청이 올 때만 컨테이너가 실행되고 없으면 꺼집니다.
Cloud Functions는 함수 1개가 서비스 1개인데, Cloud Run은 라우트 16개가 서비스 1개.
이 차이가 관리 복잡도를 극적으로 줄여줍니다.

---

## 자동화 추가가 이렇게 쉽습니다

새로운 자동화를 추가하는 전체 과정입니다.
Claude Code를 사용하면 1~3번은 대화 한 번으로 끝납니다.

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

        # 1. API 호출
        resp = requests.get("https://api.exchangerate.host/latest?base=USD")
        rates = resp.json()["rates"]

        # 2. 필요한 통화만 추출
        target = {k: rates[k] for k in ["KRW", "JPY", "EUR", "CNY"]}

        # 3. BigQuery 저장 (예시)
        if not self.test_mode:
            self._save_to_bigquery(target)

        return {"collected": len(target), "rates": target}

    def _save_to_bigquery(self, data):
        # BigQuery 저장 로직
        pass
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
        return jsonify(make_response('success', result=result))
    except Exception as e:
        logger.error("환율 수집 실패: %s", e)
        traceback.print_exc()
        return jsonify(make_response('error', error=e)), 500
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
# → Cloud Build (~12분) → Cloud Run 배포 → 트래픽 전환
```

### Step 5: 스케줄러 등록

```bash
bash scripts/create_scheduler.sh \
  stockai-exchange-rate \
  "0 9 * * 1-5" \
  "/run-exchange-rate"
# → 평일 매일 09:00에 자동 실행!
```

**끝.** 이제 매일 아침 9시에 환율이 수집됩니다.

---

## 비교 총정리

| 항목 | Console UI | BigQuery 예약 | n8n/Zapier | Terraform | **Code-First (우리)** |
|------|-----------|-------------|-----------|-----------|---------------------|
| 학습 곡선 | 낮음 | 낮음 | 중간 | 높음 | **낮음** (Claude Code) |
| 코드 관리 | 없음 | SQL만 | 없음 | HCL 별도 | **git** |
| 로컬 테스트 | 불가 | 불가 | 불가 | 불가 | **가능** |
| 복잡한 로직 | 제한 | SQL만 | 노드 한계 | 가능 | **Python 무제한** |
| 16개 작업 관리 | 16개 서비스 | 16개 쿼리 | 16개 워크플로우 | 16개 리소스 | **파일 1개** |
| 배포 | UI 클릭 | 자동 | 자동 | CLI | **CLI 1줄** |
| 비용/월 | 무료~ | 무료~ | $24+ | 무료~ | **무료~** |
| AI 연동 | 제한 | 불가 | 플러그인 | 없음 | **직접 호출** |
| 확장성 | 낮음 | 중간 | 중간 | 높음 | **높음** |

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
│   ├── secret_manager_helper.py       # Secret Manager 유틸리티
│   └── Dockerfile                     # Cloud Run용 Dockerfile
└── scripts/
    ├── deploy.sh                      # 빌드+배포 스크립트
    ├── create_scheduler.sh            # 스케줄러 등록 스크립트
    └── logs.sh                        # 로그 확인 스크립트
```

---

## 설치 방법

### 1. Claude Code 스킬로 등록

프로젝트 루트의 `.claude/commands/` 에 스킬 파일을 복사합니다:

```bash
# 프로젝트 루트에서
mkdir -p .claude/commands
cp gcp-automation-skill/commands/gcp-automation.md .claude/commands/
```

이후 Claude Code에서 `/gcp-automation`으로 호출할 수 있습니다.

### 2. 템플릿 활용

새 프로젝트를 시작할 때 `templates/` 폴더의 파일을 복사해서 시작합니다:

```bash
cp templates/batch_endpoint.py my-project/
cp templates/Dockerfile my-project/
cp templates/batch_job_async.py my-project/scripts/batch/my_job.py
```

### 3. 배포 스크립트

`scripts/` 폴더의 쉘 스크립트에서 변수 3개만 수정합니다:

```bash
# scripts/deploy.sh, create_scheduler.sh, logs.sh 공통
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

- `gcloud` CLI 설치: https://cloud.google.com/sdk/docs/install
- Python 3.11+
- Docker (선택 - Cloud Build 사용 시 불필요)

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
자동 갱신이 필요한 토큰(OAuth 등)은 `templates/secret_manager_helper.py`를 참조하세요.

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| 504 Timeout | 작업이 스케줄러 deadline 초과 | `--attempt-deadline=900s` 또는 작업 분리 |
| 첫 요청 실패 | Cold Start (컨테이너 부팅 지연) | `--min-instances=1` (~$15/월) |
| 429 Rate Limit | Cloud Run 공유 IP | 요청 간 sleep, 대체 API 사용 |
| 함수 import 에러 | PYTHONPATH 누락 | Dockerfile에 `ENV PYTHONPATH=/app` 확인 |

로그 확인:
```bash
bash scripts/logs.sh            # 최근 로그
bash scripts/logs.sh errors     # 에러만
bash scripts/logs.sh search "키워드"  # 검색
```

---

## 실전 프로젝트 사례

이 스킬은 StockAI Platform에서 실제 운영 중인 16개 자동화 파이프라인을 기반으로 만들었습니다:

- 30분마다 RSS 뉴스 수집 (28개 피드)
- Gemini AI 감정분석 자동 실행
- 주가 데이터 수집 (한국: Naver Finance, 미국: Alpha Vantage)
- 기술지표 / 재무 데이터 / 수급 데이터 갱신
- ML 앙상블 모델 (XGBoost + LightGBM + CatBoost) 시그널 생성
- 시그널 성과 자동 추적 (Triple Barrier)
- 텔레그램 뉴스 브리핑 자동 발송 (하루 4회)
- X(트위터) 큐레이션 (하루 3회)
- Threads 자동 발행 + OAuth 토큰 자동 갱신

16개 자동화가 batch_endpoint.py **파일 1개**, Cloud Run **서비스 1개**로 운영됩니다.
월 비용: Cloud Run ~$15 (min-instances=1) + Cloud Scheduler 무료 티어.
