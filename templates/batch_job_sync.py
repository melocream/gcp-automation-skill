"""
동기 배치 잡 템플릿 (sync)
간단한 작업이나 동기 라이브러리(requests 등)만 쓸 때 사용.

사용법:
  1. 이 파일을 scripts/ 또는 src/ 에 복사
  2. 함수 내용 수정
  3. batch_endpoint.py에서 직접 호출

batch_endpoint.py 라우트 예시:
  @app.route('/run-my-job', methods=['POST'])
  def run_my_job():
      from scripts.my_job import run_job
      result = run_job(dry_run=data.get('dry_run', False))
      return jsonify(make_response('success', result=result))
"""
from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)

# ── 설정 ─────────────────────────────────────────────────

MAX_RETRIES = 3
RETRY_BACKOFF = 2  # 지수 백오프 기본값 (초)


# ── 메인 함수 ────────────────────────────────────────────

def run_job(dry_run: bool = False, **kwargs) -> dict:
    """
    배치 잡 실행.

    Args:
        dry_run: True면 실제 쓰기/발송 없이 시뮬레이션
        **kwargs: 추가 파라미터

    Returns:
        결과 딕셔너리
    """
    start = time.time()
    processed = 0
    errors = 0

    log.info("run_job 시작 (dry_run=%s)", dry_run)

    try:
        # ──────────────────────────────────────────
        # 여기에 비즈니스 로직 작성
        #
        # 예시:
        # data = fetch_with_retry("https://api.example.com/data")
        # for item in data:
        #     process_item(item, dry_run=dry_run)
        #     processed += 1
        # ──────────────────────────────────────────
        pass

    except Exception as e:
        log.error("run_job 실패: %s", e)
        errors += 1

    elapsed = round(time.time() - start, 1)
    result = {
        "processed": processed,
        "errors": errors,
        "elapsed_sec": elapsed,
        "dry_run": dry_run,
    }
    log.info("run_job 완료: %s", result)
    return result


# ── 재시도 헬퍼 ──────────────────────────────────────────

def fetch_with_retry(url: str, method: str = "GET", **kwargs) -> dict:
    """
    HTTP 요청 + 재시도 (3회, 지수 백오프).

    Args:
        url: 요청 URL
        method: HTTP 메서드 (GET, POST 등)
        **kwargs: requests 추가 인자 (json, headers, timeout 등)

    Returns:
        응답 JSON 딕셔너리

    Raises:
        Exception: 3회 실패 시
    """
    kwargs.setdefault("timeout", 15)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.request(method, url, **kwargs)

            # 429 Rate Limit
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 60))
                log.warning("Rate limited (429), %ds 대기 (attempt %d)", retry_after, attempt)
                time.sleep(retry_after)
                continue

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.RequestException as e:
            log.warning("요청 실패 (attempt %d/%d): %s", attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF ** attempt)

    raise Exception(f"요청 실패 ({MAX_RETRIES}회 재시도 후): {url}")


# ── CLI 직접 실행 (로컬 테스트용) ───────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="My Sync Job CLI")
    parser.add_argument("--dry-run", action="store_true", help="실제 쓰기 없이 시뮬레이션")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    result = run_job(dry_run=args.dry_run)
    print(f"\n결과: {result}")
