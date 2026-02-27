# Cloud Run 배치 서비스용 Dockerfile
#
# 사용법:
#   프로젝트 루트에 복사 후 필요에 맞게 수정
#   Cloud Build: gcloud builds submit --tag gcr.io/PROJECT/SERVICE:latest
#
# 참고:
#   - Python 3.11-slim (경량)
#   - gunicorn + Flask (Cloud Run 표준)
#   - 단일 워커 + 8 스레드 (배치 작업에 적합)

FROM python:3.11-slim

# 시스템 패키지 (C 컴파일이 필요한 패키지가 없으면 build-essential 제거 가능)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 설치 (레이어 캐싱)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir flask==3.1.0 gunicorn==23.0.0

# 앱 코드 복사
COPY . .

# 비-루트 사용자 (보안 권장사항)
RUN useradd -m appuser
USER appuser

# Python 경로
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Cloud Run 포트
ENV PORT=8080
EXPOSE 8080

# 구니콘 실행
# --workers 1        : 배치 작업은 동시 요청 적으므로 1 워커 충분
# --threads 8        : I/O 대기 시 멀티스레드 활용
# --timeout 900      : Cloud Run 최대 타임아웃에 맞춤 (필요 시 3600)
# batch_endpoint:app : Flask 앱 진입점 (파일명:변수명)
CMD exec gunicorn \
    --bind :$PORT \
    --workers 1 \
    --threads 8 \
    --timeout 900 \
    batch_endpoint:app
