#!/bin/bash
#
# Cloud Scheduler 잡 등록 (create-or-update)
#
# 사용법:
#   bash scripts/create_scheduler.sh JOB_NAME "CRON" "/run-endpoint" ['{"key":"val"}']
#
# 예시:
#   bash scripts/create_scheduler.sh my-daily-job "0 9 * * 1-5" "/run-my-job"
#   bash scripts/create_scheduler.sh my-job-with-body "*/30 * * * *" "/run-my-job" '{"hours":6}'
#
# 자주 쓰는 cron:
#   "*/30 * * * *"    → 30분마다
#   "0 */4 * * *"     → 4시간마다
#   "0 9 * * 1-5"     → 평일 09:00
#   "0 8 * * 2-6"     → 화~토 08:00
#   "0 0 1,15 * *"    → 매월 1일, 15일

set -euo pipefail

# ── 프로젝트 설정 (수정 필요) ────────────────────────────
GCP_PROJECT="${GCP_PROJECT:-your-project-id}"
SERVICE_NAME="${SERVICE_NAME:-your-batch-service}"
REGION="${REGION:-asia-northeast3}"
TIMEZONE="${TIMEZONE:-Asia/Seoul}"
GCLOUD="${GCLOUD:-$HOME/google-cloud-sdk/bin/gcloud}"
ATTEMPT_DEADLINE="${ATTEMPT_DEADLINE:-900s}"

# OIDC 서비스 계정 (아래 중 하나 선택)
#   App Engine 기본: ${GCP_PROJECT}@appspot.gserviceaccount.com
#   Compute Engine 기본: PROJECT_NUMBER-compute@developer.gserviceaccount.com
#   전용 계정 (권장): scheduler-sa@${GCP_PROJECT}.iam.gserviceaccount.com
SA_EMAIL="${SA_EMAIL:-${GCP_PROJECT}@appspot.gserviceaccount.com}"

# ── 인자 파싱 ────────────────────────────────────────────
JOB_NAME="${1:?사용법: $0 JOB_NAME CRON ENDPOINT [BODY]}"
CRON="${2:?사용법: $0 JOB_NAME CRON ENDPOINT [BODY]}"
ENDPOINT="${3:?사용법: $0 JOB_NAME CRON ENDPOINT [BODY]}"
BODY="${4:-{}}"

# ── 서비스 URL 조회 ──────────────────────────────────────
echo "서비스 URL 조회 중..."
SERVICE_URL=$($GCLOUD run services describe "${SERVICE_NAME}" \
  --project="${GCP_PROJECT}" \
  --region="${REGION}" \
  --format='value(status.url)')

if [ -z "$SERVICE_URL" ]; then
  echo "ERROR: 서비스 URL을 찾을 수 없습니다. Cloud Run 서비스가 배포되었는지 확인하세요."
  exit 1
fi

FULL_URL="${SERVICE_URL}${ENDPOINT}"

# ── 스케줄러 잡 생성 (이미 있으면 업데이트) ──────────────
echo ""
echo "=== Cloud Scheduler 잡 등록 ==="
echo "  잡 이름: ${JOB_NAME}"
echo "  cron:    ${CRON} (${TIMEZONE})"
echo "  URL:     ${FULL_URL}"
echo "  body:    ${BODY}"
echo "  deadline: ${ATTEMPT_DEADLINE}"
echo ""

SCHEDULER_ARGS=(
  --project="${GCP_PROJECT}"
  --location="${REGION}"
  --schedule="${CRON}"
  --time-zone="${TIMEZONE}"
  --uri="${FULL_URL}"
  --http-method=POST
  --headers="Content-Type=application/json"
  --body="${BODY}"
  --oidc-service-account-email="${SA_EMAIL}"
  --oidc-token-audience="${SERVICE_URL}"
  --attempt-deadline="${ATTEMPT_DEADLINE}"
)

# create 시도 → 이미 존재하면 update
if $GCLOUD scheduler jobs create http "${JOB_NAME}" "${SCHEDULER_ARGS[@]}" 2>/dev/null; then
  echo "=== 새 잡 생성 완료 ==="
else
  echo "잡이 이미 존재합니다. 업데이트 중..."
  $GCLOUD scheduler jobs update http "${JOB_NAME}" "${SCHEDULER_ARGS[@]}"
  echo "=== 기존 잡 업데이트 완료 ==="
fi

echo ""
echo "즉시 테스트:"
echo "  $GCLOUD scheduler jobs run ${JOB_NAME} --project=${GCP_PROJECT} --location=${REGION}"
echo ""
echo "잡 상태 확인:"
echo "  $GCLOUD scheduler jobs describe ${JOB_NAME} --project=${GCP_PROJECT} --location=${REGION}"
