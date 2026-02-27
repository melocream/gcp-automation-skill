"""
비동기 배치 잡 템플릿 (async/await)
외부 API를 여러 개 호출하거나, I/O 작업이 많을 때 사용.

사용법:
  1. 이 파일을 scripts/batch/ 에 복사
  2. 클래스명과 run() 메서드 내용 수정
  3. batch_endpoint.py에서 import하여 run_async(job.run()) 호출

batch_endpoint.py 라우트 예시:
  @app.route('/run-my-job', methods=['POST'])
  def run_my_job():
      from scripts.batch.my_job import MyJob
      job = MyJob(test_mode=get_test_mode())
      result = run_async(job.run())
      return jsonify(build_response('success', result=result))
"""
from __future__ import annotations

import asyncio
import logging
import time

log = logging.getLogger(__name__)


class MyAsyncJob:
    """비동기 배치 잡."""

    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode

    async def run(self, dry_run: bool = False, **kwargs) -> dict:
        """
        메인 실행 메서드.

        Args:
            dry_run: True면 실제 쓰기/발송 없이 시뮬레이션만
            **kwargs: 추가 파라미터 (Cloud Scheduler body에서 전달)

        Returns:
            결과 딕셔너리 (processed, errors, elapsed_sec 등)
        """
        start = time.time()
        processed = 0
        errors = 0

        log.info("MyAsyncJob 시작 (test_mode=%s, dry_run=%s)", self.test_mode, dry_run)

        try:
            # ──────────────────────────────────────────
            # 여기에 비즈니스 로직 작성
            #
            # 예시:
            # items = await self._fetch_data()
            # for item in items:
            #     try:
            #         await self._process_item(item, dry_run=dry_run)
            #         processed += 1
            #     except Exception as e:
            #         log.error("항목 처리 실패: %s", e)
            #         errors += 1
            # ──────────────────────────────────────────
            pass

        except Exception as e:
            log.error("MyAsyncJob 치명적 오류: %s", e)
            errors += 1

        elapsed = round(time.time() - start, 1)
        result = {
            "processed": processed,
            "errors": errors,
            "elapsed_sec": elapsed,
            "dry_run": dry_run,
        }
        log.info("MyAsyncJob 완료: %s", result)
        return result

    # ── 내부 메서드 예시 ─────────────────────────────────

    async def _fetch_data(self) -> list:
        """데이터 조회 (BigQuery, API 등)."""
        # import aiohttp
        # async with aiohttp.ClientSession() as session:
        #     async with session.get("https://api.example.com/data") as resp:
        #         return await resp.json()
        return []

    async def _process_item(self, item: dict, dry_run: bool = False) -> None:
        """개별 항목 처리."""
        if dry_run:
            log.info("[DRY RUN] 처리 스킵: %s", item)
            return
        # 실제 처리 로직
        pass


# ── CLI 직접 실행 (로컬 테스트용) ───────────────────────

if __name__ == "__main__":
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description="MyAsyncJob CLI")
    parser.add_argument("--dry-run", action="store_true", help="실제 쓰기 없이 시뮬레이션")
    parser.add_argument("--test-mode", action="store_true", help="테스트 모드")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    job = MyAsyncJob(test_mode=args.test_mode)
    result = asyncio.run(job.run(dry_run=args.dry_run))
    print(f"\n결과: {result}")
