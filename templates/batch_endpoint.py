#!/usr/bin/env python3
"""
Cloud Run 배치 엔드포인트 템플릿
Google Cloud Scheduler에서 HTTP POST로 호출하는 Flask 서버.

사용법:
  1. 이 파일을 프로젝트 루트에 복사
  2. 하단의 라우트 섹션에 엔드포인트 추가
  3. Dockerfile과 함께 Cloud Run에 배포

로컬 테스트:
  python batch_endpoint.py
  curl -X POST http://localhost:8080/run-my-job
"""

import os
import sys
import asyncio
import traceback
from datetime import datetime
from flask import Flask, request, jsonify
import logging

# ── 경로 설정 (필요 시 하위 모듈 경로 추가) ──────────────
# 예: sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sub-module'))

# ── 환경 변수 기본값 ──────────────────────────────────────
os.environ.setdefault('GOOGLE_CLOUD_PROJECT', 'your-project-id')

# ── 로깅 ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('batch_endpoint')

app = Flask(__name__)


# ── 유틸리티 ──────────────────────────────────────────────

def get_test_mode():
    """환경 변수에서 테스트 모드 확인."""
    return os.getenv('TEST_MODE', 'false').lower() == 'true'


def make_response(status, result=None, error=None, **kwargs):
    """표준 JSON 응답 포맷."""
    resp = {
        'status': status,
        'timestamp': datetime.now().isoformat(),
        'test_mode': get_test_mode(),
    }
    if result is not None:
        resp['result'] = result
    if error is not None:
        resp['error'] = str(error)
    resp.update(kwargs)
    return resp


def run_async(coro):
    """비동기 코루틴을 동기적으로 실행."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── 헬스 체크 & 인덱스 ───────────────────────────────────

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify(make_response('healthy'))


@app.route('/', methods=['GET'])
def index():
    return jsonify(make_response('healthy', endpoints=[
        'GET  /health',
        # 여기에 엔드포인트 추가
        # 'POST /run-my-job',
    ]))


# ── 엔드포인트 (여기에 추가) ─────────────────────────────

# --- 예시: async 클래스 기반 ---
# @app.route('/run-my-async-job', methods=['POST'])
# def run_my_async_job():
#     try:
#         logger.info("=== My Async Job 시작 ===")
#         from scripts.batch.my_job import MyJob
#
#         data = request.get_json(silent=True) or {}
#         job = MyJob(test_mode=get_test_mode())
#         result = run_async(job.run(dry_run=data.get('dry_run', False)))
#
#         logger.info("My Async Job 완료: %s", result)
#         return jsonify(make_response('success', result=result))
#     except Exception as e:
#         logger.error("My Async Job 실패: %s", e)
#         traceback.print_exc()
#         return jsonify(make_response('error', error=e)), 500

# --- 예시: sync 함수 기반 ---
# @app.route('/run-my-sync-job', methods=['POST'])
# def run_my_sync_job():
#     try:
#         logger.info("=== My Sync Job 시작 ===")
#         from scripts.my_module import do_something
#
#         data = request.get_json(silent=True) or {}
#         result = do_something(dry_run=data.get('dry_run', False))
#
#         logger.info("My Sync Job 완료: %s", result)
#         return jsonify(make_response('success', result=result))
#     except Exception as e:
#         logger.error("My Sync Job 실패: %s", e)
#         traceback.print_exc()
#         return jsonify(make_response('error', error=e)), 500


# ── 서버 시작 ────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info("배치 엔드포인트 서버 시작 (포트: %d)", port)
    logger.info("테스트 모드: %s", get_test_mode())
    app.run(host='0.0.0.0', port=port, debug=False)
