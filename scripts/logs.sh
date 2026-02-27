#!/bin/bash
#
# Cloud Run 로그 확인 스크립트
#
# 사용법:
#   bash scripts/logs.sh              # 최근 30개 로그
#   bash scripts/logs.sh errors       # 에러만
#   bash scripts/logs.sh search "키워드"  # 키워드 검색
#   bash scripts/logs.sh scheduler JOB  # 스케줄러 잡 상태
#   bash scripts/logs.sh jobs          # 전체 스케줄러 잡 목록

set -euo pipefail

# ── 프로젝트 설정 (수정 필요) ────────────────────────────
GCP_PROJECT="${GCP_PROJECT:-your-project-id}"
SERVICE_NAME="${SERVICE_NAME:-your-batch-service}"
REGION="${REGION:-asia-northeast3}"
GCLOUD="${GCLOUD:-$HOME/google-cloud-sdk/bin/gcloud}"

# Cloud Run은 textPayload(단순 로그)와 jsonPayload(구조화 로그) 둘 다 사용
LOG_FORMAT="table(timestamp,textPayload,jsonPayload.message)"

MODE="${1:-recent}"

case "$MODE" in
  recent)
    echo "=== 최근 로그 (30개, 2시간 이내) ==="
    $GCLOUD logging read \
      "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}" \
      --project="${GCP_PROJECT}" \
      --limit=30 \
      --freshness=2h \
      --format="${LOG_FORMAT}"
    ;;

  errors)
    echo "=== 에러 로그 (최근 2시간) ==="
    $GCLOUD logging read \
      "resource.type=cloud_run_revision AND severity>=ERROR AND resource.labels.service_name=${SERVICE_NAME}" \
      --project="${GCP_PROJECT}" \
      --limit=20 \
      --freshness=2h \
      --format="table(timestamp,severity,textPayload,jsonPayload.message)"
    ;;

  search)
    KEYWORD="${2:?사용법: $0 search KEYWORD}"
    echo "=== '${KEYWORD}' 검색 (최근 2시간) ==="
    $GCLOUD logging read \
      "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME} AND (textPayload:\"${KEYWORD}\" OR jsonPayload.message:\"${KEYWORD}\")" \
      --project="${GCP_PROJECT}" \
      --limit=30 \
      --freshness=2h \
      --format="${LOG_FORMAT}"
    ;;

  scheduler)
    JOB_NAME="${2:?사용법: $0 scheduler JOB_NAME}"
    echo "=== 스케줄러 잡 상태: ${JOB_NAME} ==="
    $GCLOUD scheduler jobs describe "${JOB_NAME}" \
      --project="${GCP_PROJECT}" \
      --location="${REGION}"
    ;;

  jobs)
    echo "=== 전체 스케줄러 잡 목록 ==="
    $GCLOUD scheduler jobs list \
      --project="${GCP_PROJECT}" \
      --location="${REGION}"
    ;;

  *)
    echo "사용법:"
    echo "  $0              # 최근 30개 로그"
    echo "  $0 errors       # 에러만"
    echo "  $0 search 키워드  # 키워드 검색"
    echo "  $0 scheduler JOB # 스케줄러 잡 상태"
    echo "  $0 jobs          # 전체 잡 목록"
    exit 1
    ;;
esac
