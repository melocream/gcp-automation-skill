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
# 새 프로젝트에 기본 구조 생성
cp templates/batch_endpoint.py my-project/
cp templates/Dockerfile my-project/
cp templates/batch_job_async.py my-project/scripts/batch/my_job.py
```

### 3. 배포 스크립트 사용

`scripts/` 폴더의 쉘 스크립트를 프로젝트에 맞게 수정 후 사용합니다:

```bash
# 변수 수정 후 실행
vi scripts/deploy.sh       # GCP_PROJECT, SERVICE_NAME 등 수정
bash scripts/deploy.sh
bash scripts/create_scheduler.sh my-job "0 9 * * 1-5" "/run-my-job"
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
- Docker (로컬 테스트용, 필수 아님 - Cloud Build 사용 가능)
- Python 3.11+

---

## 핵심 아키텍처

```
┌──────────────────────────────────────────────────────┐
│                  Google Cloud Platform                │
│                                                      │
│  ┌───────────┐    HTTP POST    ┌──────────────┐     │
│  │  Cloud     │ ──────────────→│  Cloud Run    │     │
│  │  Scheduler │   cron 트리거   │  (Flask)      │     │
│  └───────────┘                 │               │     │
│                                │  /run-job-a   │     │
│  ┌───────────┐                 │  /run-job-b   │     │
│  │  Secret    │←── 읽기/쓰기 ──│  /run-job-c   │     │
│  │  Manager   │                │               │     │
│  └───────────┘                 └──────┬───────┘     │
│                                       │              │
│  ┌───────────┐     ┌──────────┐      │              │
│  │  BigQuery  │     │ 외부 API  │←─────┘              │
│  └───────────┘     └──────────┘   비즈니스 로직       │
└──────────────────────────────────────────────────────┘
```

**요점**: 모든 비즈니스 로직은 Python 코드로 작성하고, Cloud Run이 서버리스로 실행하고, Cloud Scheduler가 cron으로 트리거합니다.

---

## 왜 n8n/Zapier 대신 이걸 쓰나요?

| 항목 | n8n/Zapier | Claude Code + GCP |
|------|-----------|-------------------|
| 코드 관리 | UI에서 수동 관리 | **git 버전관리** |
| 디버깅 | 제한된 UI 로그 | **로컬 실행 + Cloud Logging** |
| 복잡한 로직 | 노드 조합 한계 | **Python 무제한 자유도** |
| 비용 | n8n Cloud $24+/월 | **Cloud Run 무료 티어** |
| 테스트 | 불가능 | **pytest + --dry-run** |
| AI 연동 | 별도 플러그인 | **Gemini/Claude 직접 호출** |
| 비밀 관리 | 자체 저장 | **Secret Manager (IAM)** |
| 자동화 생성 | 수동 구성 | **Claude Code가 코드 자동 생성** |

**결론**: Claude Code가 코드를 즉시 생성하므로, n8n의 비주얼 편집 장점이 사라집니다.
대신 git 관리, 디버깅, 테스트, AI 통합이라는 압도적 이점을 얻습니다.

---

## 빠른 시작 (5분)

```bash
# 1. 템플릿 복사
cp templates/batch_endpoint.py my-project/
cp templates/Dockerfile my-project/
cp templates/batch_job_sync.py my-project/scripts/my_job.py

# 2. my_job.py에 비즈니스 로직 작성
#    (혹은 Claude Code에게 작성 요청)

# 3. batch_endpoint.py에 라우트 추가
#    (혹은 Claude Code에게 추가 요청)

# 4. 배포
bash scripts/deploy.sh

# 5. 스케줄러 등록
bash scripts/create_scheduler.sh my-job "0 9 * * 1-5" "/run-my-job"

# 6. 즉시 테스트
gcloud scheduler jobs run my-job --project=YOUR_PROJECT --location=YOUR_REGION
```

---

## 참고: 실전 프로젝트 사례

이 스킬은 [StockAI Platform](https://github.com/) 프로젝트에서 실제 운영 중인 16개 자동화 파이프라인을 기반으로 만들었습니다:

- 30분마다 RSS 뉴스 수집
- AI 감정분석 자동 실행
- 주가 데이터 수집 (한국: Naver, 미국: Alpha Vantage)
- 기술지표 / 재무 데이터 / 수급 데이터 갱신
- ML 시그널 생성 및 성과 평가
- 텔레그램 브리핑 자동 발송 (하루 4회)
- X(트위터) 큐레이션 (하루 3회)
- Threads 자동 발행 + 토큰 자동 갱신

모든 자동화가 이 패턴 하나로 구현되어 있습니다.
