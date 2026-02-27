#!/bin/bash
#
# Cloud Run 빌드 + 배포 스크립트
#
# 사용법:
#   bash scripts/deploy.sh
#
# 사전 설정:
#   아래 변수들을 프로젝트에 맞게 수정하세요.

set -euo pipefail

# ── 프로젝트 설정 (수정 필요) ────────────────────────────
GCP_PROJECT="${GCP_PROJECT:-your-project-id}"
SERVICE_NAME="${SERVICE_NAME:-your-batch-service}"
REGION="${REGION:-asia-northeast3}"
IMAGE="gcr.io/${GCP_PROJECT}/${SERVICE_NAME}:latest"
GCLOUD="${GCLOUD:-$HOME/google-cloud-sdk/bin/gcloud}"

# Cloud Run 설정
MEMORY="2Gi"
CPU="2"
TIMEOUT="900"
MIN_INSTANCES="1"
MAX_INSTANCES="${MAX_INSTANCES:-5}"

# ── 빌드 대상 디렉토리 (Dockerfile이 있는 곳) ──────────
BUILD_DIR="${BUILD_DIR:-.}"

# ── 1. Cloud Build ────────────────────────────────────────
echo "=== Cloud Build 시작 ==="
echo "  프로젝트: ${GCP_PROJECT}"
echo "  이미지: ${IMAGE}"
echo "  빌드 디렉토리: ${BUILD_DIR}"

$GCLOUD builds submit \
  --tag "${IMAGE}" \
  --project="${GCP_PROJECT}" \
  "${BUILD_DIR}"

echo "=== Cloud Build 완료 ==="

# ── 2. Cloud Run 배포 ────────────────────────────────────
echo ""
echo "=== Cloud Run 배포 시작 ==="

$GCLOUD run deploy "${SERVICE_NAME}" \
  --image="${IMAGE}" \
  --project="${GCP_PROJECT}" \
  --region="${REGION}" \
  --memory="${MEMORY}" \
  --cpu="${CPU}" \
  --timeout="${TIMEOUT}" \
  --min-instances="${MIN_INSTANCES}" \
  --max-instances="${MAX_INSTANCES}" \
  --no-allow-unauthenticated \
  --quiet

echo "=== Cloud Run 배포 완료 ==="

# ── 3. 최신 리비전 확인 ──────────────────────────────────
echo ""
echo "=== 최근 리비전 ==="
$GCLOUD run revisions list \
  --service="${SERVICE_NAME}" \
  --project="${GCP_PROJECT}" \
  --region="${REGION}" \
  --limit=3

# ── 4. 트래픽 라우팅 안내 ────────────────────────────────
echo ""
echo "=== 트래픽 라우팅 ==="
echo "최신 리비전으로 100% 트래픽을 전환하려면:"
echo ""
echo "  $GCLOUD run services update-traffic ${SERVICE_NAME} \\"
echo "    --to-revisions=REVISION_NAME=100 \\"
echo "    --project=${GCP_PROJECT} --region=${REGION}"
echo ""

# ── 5. 서비스 URL 출력 ──────────────────────────────────
SERVICE_URL=$($GCLOUD run services describe "${SERVICE_NAME}" \
  --project="${GCP_PROJECT}" \
  --region="${REGION}" \
  --format='value(status.url)')

echo "서비스 URL: ${SERVICE_URL}"
echo ""
echo "헬스 체크:"
echo "  curl -s ${SERVICE_URL}/ | python3 -m json.tool"
