# GCP 자동화 파이프라인 구축 스킬

사용자가 "XX를 자동으로 돌려줘", "배치 작업 추가해줘", "스케줄러 등록해줘" 요청 시 이 레시피를 따릅니다.

---

## 아키텍처 패턴

```
[Python 함수]  →  [Flask 엔드포인트]  →  [Cloud Run]  →  [Cloud Scheduler]
  비즈니스 로직     batch_endpoint.py      서버리스 컨테이너    cron 트리거
```

---

## 새 자동화 추가 5단계

### Step 1: 배치 함수 작성

`scripts/batch/` 또는 프로젝트에 맞는 위치에 비즈니스 로직을 작성합니다.

**패턴 A — 클래스 기반 (async):**
```python
# scripts/batch/my_job.py
import logging

log = logging.getLogger(__name__)

class MyJob:
    def __init__(self, test_mode=False):
        self.test_mode = test_mode

    async def run(self, **kwargs):
        log.info("MyJob 시작: %s", kwargs)
        # 비즈니스 로직
        result = {"processed": 100, "errors": 0}
        log.info("MyJob 완료: %s", result)
        return result
```

**패턴 B — 함수 기반 (sync):**
```python
# scripts/my_module.py
import logging

log = logging.getLogger(__name__)

def do_something(dry_run=False):
    log.info("do_something 시작 (dry_run=%s)", dry_run)
    # 비즈니스 로직
    return {"status": "done", "count": 42}
```

**주의사항:**
- 외부 API 호출 → 반드시 재시도 로직 (3회 + exponential backoff)
- Cloud Run 타임아웃: 기본 300초, 최대 3600초
- 30분 이상 걸리는 작업 → 분리 (예: KR + US 분리)

### Step 2: batch_endpoint.py에 라우트 추가

**async 클래스 라우트 템플릿:**
```python
@app.route('/run-my-job', methods=['POST'])
def run_my_job():
    try:
        logger.info("=== My Job 시작 ===")
        from scripts.batch.my_job import MyJob

        data = request.get_json(silent=True) or {}
        job = MyJob(test_mode=get_test_mode())
        result = run_async(job.run(dry_run=data.get('dry_run', False)))

        logger.info("My Job 완료: %s", result)
        return jsonify(make_response('success', result=result))
    except Exception as e:
        logger.error("My Job 실패: %s", e)
        traceback.print_exc()
        return jsonify(make_response('error', error=e)), 500
```

**sync 함수 라우트 템플릿:**
```python
@app.route('/run-my-job', methods=['POST'])
def run_my_job():
    try:
        logger.info("=== My Job 시작 ===")
        from scripts.my_module import do_something

        data = request.get_json(silent=True) or {}
        result = do_something(dry_run=data.get('dry_run', False))

        logger.info("My Job 완료: %s", result)
        return jsonify(make_response('success', result=result))
    except Exception as e:
        logger.error("My Job 실패: %s", e)
        traceback.print_exc()
        return jsonify(make_response('error', error=e)), 500
```

**체크리스트:**
- [ ] index() 함수의 endpoints 리스트에 등록
- [ ] import는 함수 내부에서 (lazy import)
- [ ] `request.get_json(silent=True) or {}`로 빈 body 처리
- [ ] 결과에 처리 건수/에러 수 포함 (모니터링용)

### Step 3: 빌드 & 배포

```bash
# 변수 설정 (프로젝트에 맞게 수정)
GCP_PROJECT="your-project-id"
SERVICE_NAME="your-service-name"
REGION="asia-northeast3"
GCLOUD=$HOME/google-cloud-sdk/bin/gcloud

# Cloud Build
$GCLOUD builds submit \
  --tag gcr.io/$GCP_PROJECT/$SERVICE_NAME:latest \
  --project=$GCP_PROJECT

# Cloud Run 배포
$GCLOUD run deploy $SERVICE_NAME \
  --image=gcr.io/$GCP_PROJECT/$SERVICE_NAME:latest \
  --project=$GCP_PROJECT \
  --region=$REGION \
  --memory=2Gi \
  --cpu=2 \
  --timeout=900 \
  --min-instances=1 \
  --quiet

# 트래픽 라우팅 (최신 리비전으로)
$GCLOUD run revisions list \
  --service=$SERVICE_NAME --project=$GCP_PROJECT --region=$REGION --limit=3

$GCLOUD run services update-traffic $SERVICE_NAME \
  --to-revisions=REVISION_NAME=100 \
  --project=$GCP_PROJECT --region=$REGION
```

### Step 4: Cloud Scheduler 등록

```bash
SERVICE_URL=$($GCLOUD run services describe $SERVICE_NAME \
  --project=$GCP_PROJECT --region=$REGION --format='value(status.url)')

$GCLOUD scheduler jobs create http JOB_NAME \
  --project=$GCP_PROJECT \
  --location=$REGION \
  --schedule="CRON_EXPRESSION" \
  --time-zone="Asia/Seoul" \
  --uri="$SERVICE_URL/run-my-job" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --body='{}' \
  --oidc-service-account-email=$GCP_PROJECT@appspot.gserviceaccount.com \
  --oidc-token-audience="$SERVICE_URL" \
  --attempt-deadline=900s
```

**자주 쓰는 cron:**
| 표현식 | 의미 |
|--------|------|
| `*/30 * * * *` | 30분마다 |
| `0 */4 * * *` | 4시간마다 |
| `0 9 * * 1-5` | 평일 09:00 |
| `0 8 * * 2-6` | 화~토 08:00 |
| `0 0 1,15 * *` | 매월 1일, 15일 |

### Step 5: 검증

```bash
# 수동 트리거
$GCLOUD scheduler jobs run JOB_NAME --project=$GCP_PROJECT --location=$REGION

# 로그 확인
$GCLOUD logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" \
  --project=$GCP_PROJECT --limit=30 --freshness=10m \
  --format="table(timestamp,textPayload)"
```

---

## Secret Manager 연동

### 시크릿 생성 & 마운트

```bash
# 생성
$GCLOUD secrets create SECRET_NAME --project=$GCP_PROJECT

# 값 설정
echo -n "secret-value" | $GCLOUD secrets versions add SECRET_NAME \
  --data-file=- --project=$GCP_PROJECT

# Cloud Run에 환경 변수로 마운트
$GCLOUD run deploy $SERVICE_NAME \
  --set-secrets="ENV_VAR=SECRET_NAME:latest" \
  --project=$GCP_PROJECT --region=$REGION
```

### Python에서 시크릿 업데이트 (자동 갱신용)

```python
from google.cloud import secretmanager

def update_secret(secret_id: str, new_value: str, project: str):
    client = secretmanager.SecretManagerServiceClient()
    client.add_secret_version(
        request={
            "parent": f"projects/{project}/secrets/{secret_id}",
            "payload": {"data": new_value.encode("utf-8")},
        }
    )
```

**pip:** `google-cloud-secret-manager`

---

## 트러블슈팅

### 504 Gateway Timeout
- 작업이 `attempt-deadline`보다 오래 걸림
- **해결**: `--attempt-deadline=900s` 또는 작업 분리

### Cold Start 실패
- min-instances=0이면 첫 요청 타임아웃
- **해결**: `--min-instances=1`
- **비용**: ~$15/월 (2vCPU/2Gi 기준)

### 429 Rate Limit
- Cloud Run 공유 IP → 외부 API 차단
- **해결**: 요청 간 sleep, 대체 API 사용

### 로그 확인

```bash
# 에러만
$GCLOUD logging read \
  "resource.type=cloud_run_revision AND severity>=ERROR AND resource.labels.service_name=$SERVICE_NAME" \
  --project=$GCP_PROJECT --limit=20 --freshness=1h

# 스케줄러 상태
$GCLOUD scheduler jobs describe JOB_NAME --project=$GCP_PROJECT --location=$REGION
```

---

## 빠른 시작

사용자에게 3가지만 확인:
1. **무슨 작업?** (예: "매일 환율 수집")
2. **얼마나 자주?** (예: "평일 09시")
3. **특별한 API 키?** (예: "이미 .env에 있음")

그 다음:
1. 배치 함수 작성 (templates/ 참조)
2. batch_endpoint.py 라우트 추가
3. 빌드 & 배포 (`scripts/deploy.sh`)
4. 스케줄러 등록 (`scripts/create_scheduler.sh`)
5. 수동 트리거로 검증
