"""
Google Secret Manager 헬퍼
토큰 자동 갱신, API 키 관리 등에 사용.

필요 패키지:
  pip install google-cloud-secret-manager

사용 예시:
  from secret_manager_helper import read_secret, update_secret

  # 읽기
  token = read_secret("my-api-token", project="my-project")

  # 쓰기 (새 버전 추가)
  update_secret("my-api-token", "new-value", project="my-project")

  # 토큰 갱신 + 저장 패턴
  result = refresh_and_store("my-api-token", refresh_func, project="my-project")
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def read_secret(secret_id: str, project: str, version: str = "latest") -> str | None:
    """
    Secret Manager에서 시크릿 값 읽기.

    Args:
        secret_id: 시크릿 이름
        project: GCP 프로젝트 ID
        version: 버전 ("latest" 또는 숫자)

    Returns:
        시크릿 값 문자열, 실패 시 None
    """
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project}/secrets/{secret_id}/versions/{version}"
        response = client.access_secret_version(name=name)
        value = response.payload.data.decode("utf-8")
        log.info("Secret '%s' 읽기 성공 (version=%s)", secret_id, version)
        return value

    except ImportError:
        log.error("google-cloud-secret-manager 패키지가 설치되지 않았습니다")
        return None

    except Exception as e:
        log.error("Secret '%s' 읽기 실패: %s", secret_id, e)
        return None


def update_secret(secret_id: str, new_value: str, project: str) -> bool:
    """
    Secret Manager에 새 버전 추가.

    Args:
        secret_id: 시크릿 이름
        new_value: 새 값
        project: GCP 프로젝트 ID

    Returns:
        성공 여부
    """
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{project}/secrets/{secret_id}"

        response = client.add_secret_version(
            request={
                "parent": parent,
                "payload": {"data": new_value.encode("utf-8")},
            }
        )

        log.info("Secret '%s' 업데이트 성공: %s", secret_id, response.name)
        return True

    except ImportError:
        log.error("google-cloud-secret-manager 패키지가 설치되지 않았습니다")
        return False

    except Exception as e:
        log.error("Secret '%s' 업데이트 실패: %s", secret_id, e)
        return False


def create_secret(secret_id: str, project: str) -> bool:
    """
    새 시크릿 생성 (값 없이).

    Args:
        secret_id: 시크릿 이름
        project: GCP 프로젝트 ID

    Returns:
        성공 여부
    """
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{project}"

        client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"auto": {}}},
            }
        )

        log.info("Secret '%s' 생성 성공", secret_id)
        return True

    except Exception as e:
        log.error("Secret '%s' 생성 실패: %s", secret_id, e)
        return False


def refresh_and_store(
    secret_id: str,
    refresh_func,
    project: str,
) -> dict:
    """
    토큰/시크릿 갱신 + Secret Manager 저장 통합 패턴.

    Args:
        secret_id: 저장할 시크릿 이름
        refresh_func: 새 값을 반환하는 콜러블 (예: threads_publisher.refresh_token)
        project: GCP 프로젝트 ID

    Returns:
        {"refreshed": bool, "stored": bool, "error": str|None}
    """
    result = {"refreshed": False, "stored": False, "error": None}

    # 1. 갱신
    try:
        new_value = refresh_func()
    except Exception as e:
        log.error("refresh_func 실행 실패: %s", e)
        result["error"] = f"refresh_func raised: {e}"
        return result

    if not new_value:
        result["error"] = "refresh_func returned None"
        return result
    result["refreshed"] = True

    # 2. Secret Manager 저장
    stored = update_secret(secret_id, new_value, project)
    result["stored"] = stored
    if not stored:
        result["error"] = "Secret Manager storage failed (token still refreshed)"

    return result
