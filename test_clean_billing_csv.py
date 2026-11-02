import json
from pathlib import Path

import pandas as pd
import pytest

from data_processing import clean_billing_csv


CATALOG = {
    "tools": [
        {"service_name": "Figma", "aliases": ["피그마", "figma"]},
        {"service_name": "Slack", "aliases": ["슬랙", "slack"]},
    ]
}


def _sample_paths():
    base_dir = Path(__file__).resolve().parent
    required = [
        base_dir / "payment_history_raw_100_sample.csv",
        base_dir / "saas_catalog_30_sample.json",
        base_dir / "정답지_정제후_결제내역.csv",
    ]
    if any(not path.exists() for path in required):
        pytest.skip("required sample files are missing")
    return required


def test_t01_normal_row_cleaning_and_monthly_conversion():
    """정상: 표준 alias와 월간/연간 변환을 적용한 정제 결과를 검증한다."""
    df = pd.DataFrame(
        {
            "tx_id": ["TX-1", "TX-2"],
            "billing_date": ["2026/10/05", "20261006"],
            "service_name": ["피그마", "slack"],
            "department": ["디자인", "영업"],
            "billing_cycle": ["월간", "annual"],
            "seat_count": ["10", "7"],
            "active_users": ["6", "4"],
            "billing_amount_krw": ["180,000원", "1478400"],
            "card_holder_pii": ["더미", "더미"],
        },
        dtype=str,
    )

    result, warnings = clean_billing_csv(df, CATALOG)

    assert len(result) == 2
    assert result["billing_date"].tolist() == ["2026-10-05", "2026-10-06"]
    assert result["service_name"].tolist() == ["Figma", "Slack"]
    assert result["billing_cycle"].tolist() == ["월간", "연간"]
    assert result["billing_amount_krw"].tolist() == [180000, 1478400]
    assert result["monthly_cost_krw"].tolist() == [180000, 123200]
    assert all(pd.api.types.is_integer_dtype(result[col]) for col in [
        "seat_count",
        "active_users",
        "billing_amount_krw",
        "monthly_cost_krw",
    ])
    assert isinstance(warnings, list)


def test_t02_empty_df_returns_empty_result_and_no_warnings():
    """경계: 비어 있는 DataFrame은 10개 열의 빈 결과와 빈 경고를 반환한다."""
    df = pd.DataFrame(
        columns=[
            "tx_id",
            "billing_date",
            "service_name",
            "department",
            "billing_cycle",
            "seat_count",
            "active_users",
            "billing_amount_krw",
            "card_holder_pii",
        ],
        dtype=str,
    )

    result, warnings = clean_billing_csv(df, CATALOG)

    assert result.empty
    assert result.shape[1] == 10
    assert warnings == []


def test_t03_empty_tx_id_is_auto_assigned_and_overflow_is_corrected():
    """경계: 빈 tx_id는 자동 발급되고, 과도한 active_users는 seat_count로 보정한다."""
    df = pd.DataFrame(
        {
            "tx_id": [""],
            "billing_date": ["2026-10-07"],
            "service_name": ["Figma"],
            "department": [""],
            "billing_cycle": ["월간"],
            "seat_count": ["5"],
            "active_users": ["9"],
            "billing_amount_krw": ["0"],
            "card_holder_pii": ["더미"],
        },
        dtype=str,
    )

    result, warnings = clean_billing_csv(df, CATALOG)

    assert result.loc[0, "tx_id"] == "TX-AUTO-001"
    assert result.loc[0, "department"] == "미상"
    assert result.loc[0, "active_users"] == 5
    assert result.loc[0, "billing_amount_krw"] == 0
    assert result.loc[0, "monthly_cost_krw"] == 0
    assert len(warnings) == 2
    assert {warning["reason"] for warning in warnings} == {
        "department 비어 있어 '미상'으로 보정",
        "active_users가 seat_count를 초과해 5로 보정",
    }


def test_t04_excluded_invalid_rows_are_dropped_with_warning_reasons():
    """예외: 중복, 날짜, cycle, seat, 금액 오류 행은 모두 제외되고 경고를 남긴다."""
    df = pd.DataFrame(
        {
            "tx_id": ["TX-1", "TX-1", "TX-3", "TX-4", "TX-5", "TX-6"],
            "billing_date": ["2026-01-01", "2026-01-02", "abc", "2026-01-03", "2026-01-04", "2026-01-05"],
            "service_name": ["Figma", "Figma", "Figma", "Figma", "Figma", "Figma"],
            "department": ["디자인", "디자인", "디자인", "디자인", "디자인", "디자인"],
            "billing_cycle": ["월간", "월간", "월간", "월간", "월간", "weekly"],
            "seat_count": ["5", "5", "5", "0", "5", "5"],
            "active_users": ["2", "2", "2", "2", "2", "2"],
            "billing_amount_krw": ["1000", "1000", "1000", "1000", "-500", "1000"],
            "card_holder_pii": ["더미", "더미", "더미", "더미", "더미", "더미"],
        },
        dtype=str,
    )

    result, warnings = clean_billing_csv(df, CATALOG)

    assert len(result) == 1
    assert result.iloc[0]["tx_id"] == "TX-1"
    assert {warning["reason"] for warning in warnings} >= {
        "중복 tx_id로 제외",
        "잘못된 billing_date: abc",
        "잘못된 billing_cycle: weekly",
        "seat_count <= 0 제외: 0",
        "billing_amount_krw 음수 제외: -500",
    }
    assert {warning["action"] for warning in warnings} == {"제외"}


def test_t05_missing_required_columns_raise_value_error():
    """예외: 필수 열이 빠지면 ValueError와 누락 열명을 반환한다."""
    df = pd.DataFrame(
        {
            "tx_id": ["TX-1"],
            "billing_date": ["2026-01-01"],
            "service_name": ["Figma"],
            "department": ["디자인"],
            "billing_cycle": ["월간"],
            "seat_count": ["5"],
            "active_users": ["2"],
            "billing_amount_krw": ["1000"],
        },
        dtype=str,
    )

    with pytest.raises(ValueError, match="필수 열 누락"):
        clean_billing_csv(df, CATALOG)


def test_t06_sample_integration_matches_reference_output():
    """통합: 샘플 CSV와 정답지 데이터가 정제 결과와 일치하는지 검증한다."""
    csv_path, catalog_path, answer_path = _sample_paths()

    raw_df = pd.read_csv(csv_path, dtype=str)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    answer_df = pd.read_csv(answer_path, dtype=str)

    result, _ = clean_billing_csv(raw_df, catalog)

    assert len(result) == 80

    compare_cols = [
        col for col in result.columns if col not in {"card_holder_pii", "monthly_cost_krw"}
    ]
    for col in compare_cols:
        assert result[col].astype(str).reset_index(drop=True).tolist() == answer_df[col].astype(str).reset_index(drop=True).tolist()
    assert result["tx_id"].astype(str).tolist() == answer_df["tx_id"].astype(str).tolist()


def test_t07_empty_df_missing_column_raises():
    """예외: 빈 DataFrame이라도 필수 열이 없으면 ValueError를 발생시킨다."""
    df = pd.DataFrame(
        columns=[
            "tx_id",
            "billing_date",
            "service_name",
            "department",
            "billing_cycle",
            "seat_count",
            "active_users",
            "billing_amount_krw",
        ],
        dtype=str,
    )

    with pytest.raises(ValueError, match="필수 열 누락"):
        clean_billing_csv(df, CATALOG)
