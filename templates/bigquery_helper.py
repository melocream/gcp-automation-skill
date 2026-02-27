"""
BigQuery 테이블 관리 + MERGE (Upsert) 헬퍼
배치 자동화에서 수집한 데이터를 BigQuery에 적재할 때 사용.

필요 패키지:
  pip install google-cloud-bigquery

사용 예시:
  from bigquery_helper import ensure_table, upsert, simple_insert

  # 테이블 없으면 자동 생성
  ensure_table("my-project", "my_dataset", "exchange_rates", [
      {"name": "date", "type": "DATE", "mode": "REQUIRED"},
      {"name": "currency", "type": "STRING", "mode": "REQUIRED"},
      {"name": "rate", "type": "FLOAT64"},
  ])

  # MERGE upsert (있으면 UPDATE, 없으면 INSERT)
  upsert(
      project="my-project",
      dataset="my_dataset",
      table="exchange_rates",
      rows=[{"date": "2026-01-01", "currency": "KRW", "rate": 1350.5}],
      key_columns=["date", "currency"],
      update_columns=["rate"],
  )

  # 단순 INSERT (중복 신경 안 쓸 때)
  simple_insert("my-project", "my_dataset", "logs", rows)
"""
from __future__ import annotations

import datetime
import logging
import math
from typing import Any

log = logging.getLogger(__name__)


# ── 테이블 생성 ──────────────────────────────────────────

def ensure_table(
    project: str,
    dataset: str,
    table: str,
    schema: list[dict],
) -> bool:
    """
    테이블이 없으면 생성, 있으면 스킵.

    Args:
        project: GCP 프로젝트 ID
        dataset: BigQuery 데이터셋 이름
        table: 테이블 이름
        schema: 스키마 정의 리스트
            [{"name": "col", "type": "STRING", "mode": "REQUIRED"}, ...]
            type: STRING, INT64, FLOAT64, BOOL, DATE, TIMESTAMP, RECORD, ...
            mode: REQUIRED, NULLABLE (기본), REPEATED

    Returns:
        True면 새로 생성됨, False면 이미 존재
    """
    from google.cloud import bigquery
    import google.cloud.exceptions

    client = bigquery.Client(project=project)
    table_ref = f"{project}.{dataset}.{table}"

    try:
        client.get_table(table_ref)
        log.info("테이블 이미 존재: %s", table_ref)
        return False
    except google.cloud.exceptions.NotFound:
        bq_schema = [
            bigquery.SchemaField(
                name=col["name"],
                field_type=col["type"],
                mode=col.get("mode", "NULLABLE"),
            )
            for col in schema
        ]
        table_obj = bigquery.Table(table_ref, schema=bq_schema)
        client.create_table(table_obj)
        log.info("테이블 생성 완료: %s", table_ref)
        return True


# ── MERGE (Upsert) ───────────────────────────────────────

def upsert(
    project: str,
    dataset: str,
    table: str,
    rows: list[dict],
    key_columns: list[str],
    update_columns: list[str] | None = None,
    chunk_size: int = 2000,
) -> dict:
    """
    BigQuery MERGE를 사용한 Upsert.
    스테이징 테이블 → MERGE → 스테이징 삭제.

    Args:
        project: GCP 프로젝트 ID
        dataset: BigQuery 데이터셋
        table: 대상 테이블
        rows: 적재할 데이터 (딕셔너리 리스트)
        key_columns: MERGE 키 컬럼 (예: ["date", "symbol_id"])
        update_columns: UPDATE 할 컬럼. None이면 키 이외 전체 컬럼.
        chunk_size: 청크 크기 (대량 데이터 시 분할)

    Returns:
        {"merged": int, "chunks": int}
    """
    if not rows:
        log.warning("upsert: 빈 rows, 스킵")
        return {"merged": 0, "chunks": 0}

    from google.cloud import bigquery

    client = bigquery.Client(project=project)
    target = f"`{project}.{dataset}.{table}`"
    staging_name = f"_staging_{table}"
    staging = f"`{project}.{dataset}.{staging_name}`"
    staging_ref = f"{project}.{dataset}.{staging_name}"

    # NaN 정리
    clean_rows = [_clean_row(r) for r in rows]

    # UPDATE 컬럼 자동 결정
    if update_columns is None:
        all_cols = list(clean_rows[0].keys())
        update_columns = [c for c in all_cols if c not in key_columns]

    total_merged = 0
    chunks = 0

    for i in range(0, len(clean_rows), chunk_size):
        chunk = clean_rows[i:i + chunk_size]
        chunks += 1

        # 1. 스테이징 로드
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
            autodetect=True,  # 스테이징은 autodetect OK (임시 테이블)
        )
        client.load_table_from_json(chunk, staging_ref, job_config=job_config).result()

        # 2. MERGE (컬럼명을 backtick으로 감싸 예약어 충돌 방지)
        on_clause = " AND ".join(f"T.`{k}` = S.`{k}`" for k in key_columns)
        update_set = ", ".join(f"T.`{c}` = S.`{c}`" for c in update_columns)
        all_columns = list(chunk[0].keys())
        insert_cols = ", ".join(f"`{c}`" for c in all_columns)
        insert_vals = ", ".join(f"S.`{c}`" for c in all_columns)

        merge_sql = f"""
        MERGE {target} T
        USING {staging} S
        ON {on_clause}
        WHEN MATCHED THEN
            UPDATE SET {update_set}
        WHEN NOT MATCHED THEN
            INSERT ({insert_cols})
            VALUES ({insert_vals})
        """
        result = client.query(merge_sql).result()
        total_merged += len(chunk)

        log.info(
            "MERGE 청크 %d 완료: %d행 (%d/%d)",
            chunks, len(chunk), min(i + chunk_size, len(clean_rows)), len(clean_rows),
        )

    # 3. 스테이징 삭제
    client.delete_table(staging_ref, not_found_ok=True)

    result = {"merged": total_merged, "chunks": chunks}
    log.info("upsert 완료: %s", result)
    return result


# ── 단순 INSERT ──────────────────────────────────────────

def simple_insert(
    project: str,
    dataset: str,
    table: str,
    rows: list[dict],
) -> dict:
    """
    단순 INSERT (중복 체크 없이 추가).
    로그성 데이터, 이벤트 데이터 등 중복이 상관없는 경우.

    Returns:
        {"inserted": int, "errors": list}
    """
    if not rows:
        return {"inserted": 0, "errors": []}

    from google.cloud import bigquery

    client = bigquery.Client(project=project)
    table_ref = f"{project}.{dataset}.{table}"

    clean_rows = [_clean_row(r) for r in rows]
    errors = client.insert_rows_json(table_ref, clean_rows)

    if errors:
        log.error("insert 에러 %d건: %s", len(errors), errors[:3])

    return {"inserted": len(clean_rows), "errors": errors}


# ── 쿼리 실행 ────────────────────────────────────────────

def run_query(project: str, sql: str, params: dict | None = None) -> list[dict]:
    """
    BigQuery SQL 실행 + 결과를 딕셔너리 리스트로 반환.

    Args:
        project: GCP 프로젝트 ID
        sql: SQL 쿼리 (파라미터는 @name 형식으로 참조)
        params: 쿼리 파라미터 (선택)
            예: {"start_date": "2026-01-01", "limit": 100}
            SQL에서 @start_date, @limit 으로 참조

    Returns:
        행 딕셔너리 리스트
    """
    from google.cloud import bigquery

    client = bigquery.Client(project=project)

    job_config = None
    if params:
        type_map = {
            str: "STRING",
            int: "INT64",
            float: "FLOAT64",
            bool: "BOOL",
        }
        query_params = []
        for key, value in params.items():
            bq_type = type_map.get(type(value), "STRING")
            query_params.append(
                bigquery.ScalarQueryParameter(key, bq_type, value)
            )
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)

    result = client.query(sql, job_config=job_config).result()
    return [dict(row) for row in result]


# ── 내부 헬퍼 ────────────────────────────────────────────

def _clean_row(row: dict) -> dict:
    """NaN/Inf → None 변환, date → str 변환."""
    cleaned = {}
    for k, v in row.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            cleaned[k] = None
        elif isinstance(v, (datetime.date, datetime.datetime)):
            cleaned[k] = str(v)
        else:
            cleaned[k] = v
    return cleaned
