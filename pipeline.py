"""BIRDS 백엔드 통합 파이프라인 스크립트 (pipeline.py).

9주차에 구현한 데이터 로드·마스킹·정제·정량 분석 모듈과 10주차 Mock LLM 모듈을
하나의 비즈니스 워크플로우로 연결하여 화면(Streamlit) 및 리포트 출력용 dict를 반환한다.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from data_processing import (
    clean_billing_csv,
    load_billing_csv,
    load_saas_catalog,
    mask_pii_data,
)
from llm_utils import (
    ConversationState,
    FinalReport,
    QuestionBatch,
    USE_MOCK,
    build_prompt_template,
    call_llm_request,
    parse_and_validate_json,
)
from quant_analysis import (
    SeatLeakage,
    calculate_seat_leakage,
    detect_duplicate_tags,
)

# 기본 샘플 데이터 경로 상수
DEFAULT_BILLING_CSV_PATH: str = "payment_history_raw_100_sample.csv"
DEFAULT_CATALOG_JSON_PATH: str = "saas_catalog_30_sample.json"


def adapt_duplicate_pairs_for_json(
    raw_pairs: list[dict[str, Any]],
) -> list[dict[str, list[str]]]:
    """[어댑터 함수] detect_duplicate_tags()의 set 포함 반환값을 JSON 직렬화 가능한 dict 리스트로 변환한다.

    quant_analysis.detect_duplicate_tags()는 {'tools': set, 'common_tags': set} 구조를 반환하나,
    llm_utils.build_prompt_template()의 JSON 직렬화기는 set 타입을 허용하지 않으므로
    원 모듈을 수정하지 않고 경계에서 정렬된 list[str] 형태로 변환한다.

    Args:
        raw_pairs (list[dict[str, Any]]): detect_duplicate_tags()가 반환한 원본 중복 쌍 리스트.

    Returns:
        list[dict[str, list[str]]]: 'tools'와 'categories'가 정렬된 문자열 리스트로 변환된 구조.

    Raises:
        AssertionError: 입력이 list가 아니거나 내부 원소가 dict가 아닐 경우 발생.
    """
    assert isinstance(raw_pairs, list), f"list 타입 필요, {type(raw_pairs).__name__} 수신"

    adapted: list[dict[str, list[str]]] = []
    for item in raw_pairs:
        assert isinstance(item, dict), f"중복 쌍 원소는 dict여야 함: {type(item).__name__}"
        tools_raw = item.get("tools", set())
        tags_raw = item.get("common_tags", item.get("categories", set()))
        adapted.append(
            {
                "tools": sorted(str(t) for t in tools_raw),
                "categories": sorted(str(tag) for tag in tags_raw),
            }
        )
    return adapted


def summarize_analysis_for_llm(
    clean_df: pd.DataFrame,
    warnings: list[dict[str, str]],
    seat_leakage: list[SeatLeakage],
    duplicate_pairs: list[dict[str, list[str]]],
) -> dict[str, Any]:
    """[어댑터 및 요약 함수] 정량 분석 결과를 LLM 프롬프트 및 UI 전달용 단일 dict로 요약한다.

    Args:
        clean_df (pd.DataFrame): 정제 완료된 결제 내역 DataFrame.
        warnings (list[dict[str, str]]): 정제 과정에서 발생한 경고/보정 목록.
        seat_leakage (list[SeatLeakage]): 서비스별 유휴 좌석 및 낭비 금액 리스트.
        duplicate_pairs (list[dict[str, list[str]]]): JSON 호환 변환된 중복 태그 서비스 쌍 리스트.

    Returns:
        dict[str, Any]: 총 월간 비용, 총 낭비 금액, 누수 상세, 중복 쌍을 포함한 요약 딕셔너리.
    """
    assert isinstance(clean_df, pd.DataFrame), "clean_df는 DataFrame이어야 합니다."

    total_monthly_cost = (
        int(clean_df["monthly_cost_krw"].sum())
        if not clean_df.empty and "monthly_cost_krw" in clean_df.columns
        else 0
    )
    total_wasted_spend = sum(int(item["wasted_spend"]) for item in seat_leakage)
    total_inactive_seats = sum(int(item["inactive_seats"]) for item in seat_leakage)

    return {
        "valid_transaction_count": int(len(clean_df)),
        "warning_count": int(len(warnings)),
        "total_monthly_cost_krw": total_monthly_cost,
        "total_inactive_seats": total_inactive_seats,
        "total_wasted_spend_krw": total_wasted_spend,
        "seat_leakage": seat_leakage,
        "duplicate_pairs": duplicate_pairs,
    }


def run_pipeline_from_data(
    raw_df: pd.DataFrame,
    catalog: dict[str, Any],
    initial_state: ConversationState | None = None,
) -> dict[str, Any]:
    """메모리에 로드된 DataFrame과 카탈로그 dict를 받아 파이프라인 전체를 관통 실행한다.

    단위/통합 테스트(fixture 입력) 및 파일 기반 실행 양쪽에서 공통으로 호출되는 코어 오케스트레이션 함수.
    순서(docs/schema.md 기준):
    [1] mask_pii_data -> [2] clean_billing_csv -> [3] calculate_seat_leakage & detect_duplicate_tags
    -> [4] 어댑터 변환 및 경계 assert -> [5] Mock LLM 역질문(question) & 최종 리포트(report) 생성.

    Args:
        raw_df (pd.DataFrame): 원본 결제 내역 DataFrame.
        catalog (dict[str, Any]): 검증된 SaaS 카탈로그 dict ('meta', 'tools' 키 포함).
        initial_state (ConversationState | None): LLM에 전달할 초기 대화 상태. None이면 기본값 사용.

    Returns:
        dict[str, Any]: 정제 결과, 정량 분석 요약, Mock LLM 역질문 및 리포트를 담은 구조화된 dict.

    Raises:
        TypeError: 입력 타입이 데이터 계약과 다를 경우 발생.
        ValueError: 필수 컬럼 누락 또는 스키마 검증 실패 시 발생.
        AssertionError: 모듈 간 경계 계약 위반 시 발생.
    """
    # Step 1. PII 마스킹 (docs/schema.md 순서 준수: mask_pii_data -> clean_billing_csv)
    masked_df = mask_pii_data(raw_df)
    assert isinstance(masked_df, pd.DataFrame), "mask_pii_data 반환값은 DataFrame이어야 합니다."
    if not masked_df.empty and "card_holder_pii" in masked_df.columns:
        assert (masked_df["card_holder_pii"] == "[REDACTED]").all(), (
            "경계 검증 실패: card_holder_pii 컬럼이 완전히 마스킹되지 않았습니다."
        )

    # Step 2. 결제 데이터 정제 및 표준화
    clean_df, warnings = clean_billing_csv(masked_df, catalog)
    assert isinstance(clean_df, pd.DataFrame), "clean_billing_csv 첫 번째 반환값은 DataFrame이어야 합니다."
    assert isinstance(warnings, list), "clean_billing_csv 두 번째 반환값은 list여야 합니다."

    # Step 3. 정량 분석 (유휴 좌석 누수 계산 & 중복 카테고리 태그 탐지)
    seat_leakage = calculate_seat_leakage(clean_df)
    raw_duplicate_pairs = detect_duplicate_tags(clean_df, catalog)

    # Step 4. 어댑터 변환 및 요약 dict 생성 (경계 검증 포함)
    adapted_duplicates = adapt_duplicate_pairs_for_json(raw_duplicate_pairs)
    analysis_summary = summarize_analysis_for_llm(
        clean_df=clean_df,
        warnings=warnings,
        seat_leakage=seat_leakage,
        duplicate_pairs=adapted_duplicates,
    )

    required_summary_keys = {
        "valid_transaction_count",
        "warning_count",
        "total_monthly_cost_krw",
        "total_inactive_seats",
        "total_wasted_spend_krw",
        "seat_leakage",
        "duplicate_pairs",
    }
    missing_keys = required_summary_keys - analysis_summary.keys()
    assert not missing_keys, f"요약 dict 필수 키 누락: {missing_keys}"

    # Step 5. Mock LLM 연동 (설계도 Slot 기반 역질문 생성 + 최종 진단 리포트 생성)
    state: ConversationState = (
        initial_state
        if initial_state is not None
        else {
            "session_id": "birds-audit-session-001",
            "round_number": 1,
            "process_codes": ["P1", "P3", "P5"],
            "filled_slots": {},
            "missing_slots": ["C-01", "P1-S08", "P3-S04", "P5-S10"],
            "workflow_summary": "스타트업 SaaS 결제 내역 정량 감사 및 프로세스 매핑",
            "must_keep": ["Slack"],
        }
    )

    question_prompt = build_prompt_template("question", state, analysis_summary)
    question_raw = call_llm_request(question_prompt)
    question_batch = parse_and_validate_json(question_raw, QuestionBatch)

    report_prompt = build_prompt_template("report", state, analysis_summary)
    report_raw = call_llm_request(report_prompt)
    final_report = parse_and_validate_json(report_raw, FinalReport)

    return {
        "meta": {
            "use_mock": USE_MOCK,
            "process_codes": state.get("process_codes", []),
        },
        "clean_data": clean_df.to_dict(orient="records"),
        "warnings": warnings,
        "summary": analysis_summary,
        "llm_questions": question_batch,
        "llm_report": final_report,
    }


def run_pipeline(
    billing_csv_path: str = DEFAULT_BILLING_CSV_PATH,
    catalog_json_path: str = DEFAULT_CATALOG_JSON_PATH,
) -> dict[str, Any]:
    """파일 경로로부터 CSV와 카탈로그 JSON을 로드하여 전체 백엔드 파이프라인을 실행한다.

    Args:
        billing_csv_path (str): 결제 내역 CSV 파일 경로.
        catalog_json_path (str): SaaS 카탈로그 JSON 파일 경로.

    Returns:
        dict[str, Any]: 파이프라인 전체 실행 결과 dict.

    Raises:
        FileNotFoundError: 지정된 경로에 파일이 존재하지 않을 경우 발생.
        ValueError: CSV 또는 카탈로그 JSON 형식이 손상되었거나 필수 키가 누락된 경우 발생.
    """
    raw_df = load_billing_csv(billing_csv_path)
    catalog = load_saas_catalog(catalog_json_path)
    return run_pipeline_from_data(raw_df=raw_df, catalog=catalog)


def make_fixture() -> tuple[pd.DataFrame, dict[str, Any]]:
    """파이프라인 관통 실행 검증을 위한 고정 입력(fixture) 데이터를 생성한다.

    Returns:
        tuple[pd.DataFrame, dict[str, Any]]: (테스트용 결제 내역 DataFrame, 테스트용 카탈로그 dict).
    """
    fixture_df = pd.DataFrame(
        {
            "tx_id": ["TX-001", "TX-002", "TX-003"],
            "billing_date": ["2026-11-01", "2026-11-02", "2026-11-03"],
            "service_name": ["Slack", "Notion", "Jira"],
            "department": ["개발팀", "기획팀", "개발팀"],
            "billing_cycle": ["월간", "월간", "연간"],
            "seat_count": ["20", "15", "10"],
            "active_users": ["12", "15", "5"],
            "billing_amount_krw": ["200,000원", "150000", "1200000"],
            "card_holder_pii": ["김철수(1234-5678)", "이영희", "박민수"],
        }
    )
    fixture_catalog: dict[str, Any] = {
        "meta": {"version": "1.0", "description": "fixture catalog"},
        "tools": [
            {
                "tool_id": "T-01",
                "service_name": "Slack",
                "aliases": ["슬랙"],
                "category_tags": ["협업", "메신저"],
                "pricing_tiers": [{"tier": "Pro", "monthly_krw": 10000}],
            },
            {
                "tool_id": "T-02",
                "service_name": "Notion",
                "aliases": ["노션"],
                "category_tags": ["협업", "문서", "프로젝트관리"],
                "pricing_tiers": [{"tier": "Plus", "monthly_krw": 10000}],
            },
            {
                "tool_id": "T-03",
                "service_name": "Jira",
                "aliases": ["지라"],
                "category_tags": ["협업", "프로젝트관리", "이슈트래킹"],
                "pricing_tiers": [{"tier": "Standard", "monthly_krw": 10000}],
            },
        ],
    }
    return fixture_df, fixture_catalog


if __name__ == "__main__":
    print("=================================================================")
    print(" [1] Fixture 입력 기반 백엔드 파이프라인 관통 실행 검증")
    print("=================================================================")
    fx_df, fx_catalog = make_fixture()
    fx_result = run_pipeline_from_data(fx_df, fx_catalog)
    print(f"- USE_MOCK 상태: {fx_result['meta']['use_mock']}")
    print(f"- 정제 통과 행 수: {fx_result['summary']['valid_transaction_count']}건")
    print(f"- 총 월간 구독 비용: {fx_result['summary']['total_monthly_cost_krw']:,}원")
    print(f"- 총 유휴 좌석 수: {fx_result['summary']['total_inactive_seats']}석")
    print(f"- 총 월간 낭비 금액: {fx_result['summary']['total_wasted_spend_krw']:,}원")
    print(f"- 중복 기능 탐지 쌍: {fx_result['summary']['duplicate_pairs']}")
    print(f"- Mock LLM 역질문 샘플: {fx_result['llm_questions']['questions'][0]['question']}")
    print(f"- Mock LLM 리포트 요약: {fx_result['llm_report']['summary']}")

    print("\n=================================================================")
    print(" [2] 실제 샘플 파일(100건 CSV & 30개 카탈로그 JSON) 파이프라인 실행")
    print("=================================================================")
    sample_result = run_pipeline()
    print(f"- 정제 통과 행 수: {sample_result['summary']['valid_transaction_count']}건")
    print(f"- 발생 경고/보정 수: {sample_result['summary']['warning_count']}건")
    print(f"- 총 월간 구독 비용: {sample_result['summary']['total_monthly_cost_krw']:,}원")
    print(f"- 총 유휴 좌석 수: {sample_result['summary']['total_inactive_seats']}석")
    print(f"- 총 월간 낭비 금액: {sample_result['summary']['total_wasted_spend_krw']:,}원")
    print(f"- 감지된 중복 서비스 쌍 수: {len(sample_result['summary']['duplicate_pairs'])}쌍")
    print(f"- Mock LLM 최종 승인 요약: {sample_result['llm_report']['candidate_sets'][0]['approval_summary']}")
    print("=================================================================")