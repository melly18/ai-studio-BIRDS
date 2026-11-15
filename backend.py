"""BIRDS 11주차 Streamlit UI 전용 백엔드 래퍼(Facade) 모듈.

UI(app.py)와 데이터 가공 로직을 철저히 분리하기 위해,
파일 로딩, 정제/마스킹 파이프라인 실행, 사이드바 필터링, KPI 산출,
차트용 데이터 집계 함수 제공.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, IO
import pandas as pd

import data_processing as dp
import quant_analysis as qa
import llm_utils as llm

# 실행 위치(cwd)와 무관하게 backend.py와 같은 폴더의 카탈로그를 사용
DEFAULT_CATALOG_PATH = str(Path(__file__).parent / "saas_catalog_30_sample.json")

# 정제 스키마(data_processing.CLEAN_OUTPUT_COLUMNS) 기준 컬럼명
COST_COL = "monthly_cost_krw"
SERVICE_COL = "service_name"


def load_csv_with_fallback(uploaded_file: IO[bytes]) -> pd.DataFrame:
    """업로드된 CSV 파일 객체를 읽어 DataFrame으로 반환 (cp949 재시도 포함).

    Args:
        uploaded_file: st.file_uploader가 반환한 UploadedFile 객체.

    Returns:
        로드된 원본 pandas DataFrame.

    Raises:
        ValueError: 파일이 비어 있거나 CSV 파싱에 실패한 경우.
    """
    # 10주차 load_billing_csv와 동일하게 모든 값을 문자열로 읽음
    read_kwargs = {"dtype": str, "keep_default_na": False}
    try:
        try:
            return pd.read_csv(uploaded_file, encoding="utf-8", **read_kwargs)
        except UnicodeDecodeError:
            uploaded_file.seek(0)  # 파일 포인터를 처음으로 되돌린 뒤 재시도
            return pd.read_csv(uploaded_file, encoding="cp949", **read_kwargs)
    except (
        UnicodeDecodeError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
    ) as exc:
        raise ValueError(f"CSV 파일을 읽을 수 없습니다: {exc}") from exc


def _call_with_supported_args(func: Any, *args: Any) -> Any:
    """모듈 함수의 파라미터 개수에 맞춰 안전하게 호출하는 내부 어댑터."""
    sig = inspect.signature(func)
    param_count = len(sig.parameters)
    return func(*args[:param_count])


def _to_json_safe(value: Any) -> Any:
    """set 등 JSON 직렬화가 불가능한 타입을 재귀적으로 변환."""
    if isinstance(value, set):
        return sorted(str(item) for item in value)
    if isinstance(value, dict):
        return {str(k): _to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(item) for item in value]
    return value


def run_audit_from_df(
    raw_df: pd.DataFrame,
    catalog_path: str = DEFAULT_CATALOG_PATH,
) -> dict[str, Any]:
    """업로드된 원본 DataFrame을 받아 10주차 백엔드 파이프라인 전체 실행.

    Args:
        raw_df: 업로드된 원본 결제 내역 DataFrame.
        catalog_path: 표준 SaaS 카탈로그 JSON 경로.

    Returns:
        정제된 DataFrame(clean_df), 누수 분석(seat_leakage), 중복 분석(duplicate_tags),
        Mock LLM 결과(llm_questions, llm_report)를 담은 딕셔너리.

    Raises:
        ValueError: 입력 데이터가 비어 있거나 필수 컬럼이 누락된 경우.
        KeyError: 스키마 필수 컬럼이 존재하지 않는 경우.
    """
    if raw_df is None or raw_df.empty:
        raise ValueError("업로드된 CSV에 데이터가 없습니다.")

    catalog = dp.load_saas_catalog(catalog_path)

    # 1. PII 마스킹 및 데이터 정제 (표준 스키마 순서 준수)
    masked_raw_df = dp.mask_pii_data(raw_df)
    cleaned_df, clean_warnings = _call_with_supported_args(
        dp.clean_billing_csv, masked_raw_df, catalog
    )
    masked_df = dp.mask_pii_data(cleaned_df)

    if masked_df.empty:
        raise ValueError("정제 조건을 통과한 유효한 결제 내역이 없습니다.")

    # 2. 정량 분석 (유휴 좌석 누수 및 중복 기능 태그 탐지)
    seat_leakage = _call_with_supported_args(
        qa.calculate_seat_leakage, masked_df, catalog
    )
    duplicate_tags = _call_with_supported_args(
        qa.detect_duplicate_tags, masked_df, catalog
    )

    # 3. Mock LLM 진단 연동 (llm_utils.py 실제 시그니처 호출)
    initial_state: dict[str, Any] = {
        "process_codes": ["P1", "P2", "P3", "P4", "P5"],
        "filled_slots": {},
        "missing_slots": ["C-01", "C-02", "C-03", "C-04"],
    }
    extra_data: dict[str, Any] = _to_json_safe(
        {
            "seat_leakage": seat_leakage,
            "duplicate_tags": duplicate_tags,
        }
    )

    question_prompt = llm.build_prompt_template(
        "question", initial_state, extra_data
    )
    question_raw = llm.call_llm_request(question_prompt)
    llm_questions = llm.parse_and_validate_json(
        question_raw, llm.QuestionBatch
    )

    report_prompt = llm.build_prompt_template(
        "report", initial_state, extra_data
    )
    report_raw = llm.call_llm_request(report_prompt)
    llm_report = llm.parse_and_validate_json(
        report_raw, llm.FinalReport
    )

    return {
        "clean_df": masked_df,
        "clean_warnings": clean_warnings,
        "row_count": int(len(masked_df)),
        "warning_count": len(clean_warnings),
        "seat_leakage": seat_leakage,
        "duplicate_tags": duplicate_tags,
        "llm_questions": llm_questions,
        "llm_report": llm_report,
    }


def get_filter_options(clean_df: pd.DataFrame) -> dict[str, list[str]]:
    """사이드바 selectbox에 표시할 필터 옵션 목록 반환."""
    dept_col = "department" if "department" in clean_df.columns else None
    cycle_col = "billing_cycle" if "billing_cycle" in clean_df.columns else None

    departments = (
        ["전체"] + sorted(clean_df[dept_col].dropna().astype(str).unique().tolist())
        if dept_col
        else ["전체"]
    )
    billing_cycles = (
        ["전체"] + sorted(clean_df[cycle_col].dropna().astype(str).unique().tolist())
        if cycle_col
        else ["전체"]
    )

    return {
        "departments": departments,
        "billing_cycles": billing_cycles,
    }


def filter_and_summarize(
    clean_df: pd.DataFrame,
    department: str = "전체",
    billing_cycle: str = "전체",
) -> dict[str, Any]:
    """사이드바 필터 조건에 맞춰 DataFrame을 필터링하고 상단 KPI 지표 계산."""
    view_df = clean_df.copy()

    if department != "전체" and "department" in view_df.columns:
        view_df = view_df[view_df["department"] == department]

    if billing_cycle != "전체" and "billing_cycle" in view_df.columns:
        view_df = view_df[view_df["billing_cycle"] == billing_cycle]

    total_cost = int(view_df[COST_COL].sum()) if not view_df.empty else 0

    wasted_seats = 0
    wasted_cost = 0
    if "seat_count" in view_df.columns and "active_users" in view_df.columns:
        unused = (view_df["seat_count"] - view_df["active_users"]).clip(lower=0)
        wasted_seats = int(unused.sum())
        safe_seats = view_df["seat_count"].replace(0, pd.NA)
        unit_cost = (view_df[COST_COL] / safe_seats).fillna(0)
        wasted_cost = int((unused * unit_cost).sum())

    return {
        "filtered_df": view_df,
        "total_cost": total_cost,
        "wasted_seats": wasted_seats,
        "wasted_cost": wasted_cost,
        "row_count": int(len(view_df)),
    }


def get_chart_data(filtered_df: pd.DataFrame) -> pd.DataFrame:
    """st.bar_chart 시각화를 위해 서비스별 구독 비용 집계 DataFrame 반환."""
    if filtered_df.empty:
        return pd.DataFrame(columns=["서비스명", "월간 구독 비용(원)"])

    chart_df = (
        filtered_df.groupby(SERVICE_COL, as_index=False)[COST_COL]
        .sum()
        .rename(columns={SERVICE_COL: "서비스명", COST_COL: "월간 구독 비용(원)"})
        .sort_values(by="월간 구독 비용(원)", ascending=False)
    )
    return chart_df