from pathlib import Path
import pytest
import pandas as pd
from data_processing import load_billing_csv, mask_pii_data

HERE = Path(__file__).parent
BILLING_SAMPLE = HERE / "payment_history_raw_100_sample.csv"
CATALOG_SAMPLE = HERE / "saas_catalog_30_sample.json"

BILLING_COLUMNS = [
    "tx_id",
    "billing_date",
    "service_name",
    "department",
    "billing_cycle",
    "seat_count",
    "active_users",
    "billing_amount_krw",
    "card_holder_pii",
]
TOOL_REQUIRED_KEYS = [
    "tool_id",
    "service_name",
    "aliases",
    "category_tags",
    "pricing_tiers",
]

def _tool(**overrides) -> dict:
    """필수 키를 모두 갖춘 더미 tool 하나를 만든다."""
    tool = {
        "tool_id": "dummy",
        "service_name": "Dummy",
        "aliases": ["더미"],
        "category_tags": ["design"],
        "pricing_tiers": [],
    }
    tool.update(overrides)
    return tool

def test_billing_normal_sample():
    """정상: 실제 샘플 100행이 원본 문자열 그대로 로드된다."""
    df = load_billing_csv(str(BILLING_SAMPLE))

    assert len(df) == 100
    assert list(df.columns) == BILLING_COLUMNS
    assert df.columns[0] == "tx_id"  # BOM 문자가 섞이지 않음
    assert df.iloc[0]["billing_amount_krw"] == "-385000"
    assert df.iloc[6]["billing_amount_krw"] == "1,656,000"  # 쉼표 제거 금지
    assert all(isinstance(v, str) for v in df.to_numpy().ravel())  # 전부 str


def test_billing_header_only_returns_empty_frame(tmp_path):
    """경계: 헤더만 있는 CSV는 예외 없이 컬럼만 있는 빈 DataFrame."""
    path = tmp_path / "header_only.csv"
    path.write_text(",".join(BILLING_COLUMNS) + "\n", encoding="utf-8")

    df = load_billing_csv(str(path))

    assert len(df) == 0
    assert list(df.columns) == BILLING_COLUMNS


def test_billing_file_not_found():
    """예외: 존재하지 않는 경로는 FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_billing_csv("no_such_file.csv")


def test_billing_zero_byte_file_raises_value_error(tmp_path):
    """예외: 0바이트 파일은 ValueError."""
    path = tmp_path / "empty.csv"
    path.write_bytes(b"")

    with pytest.raises(ValueError):
        load_billing_csv(str(path))


def test_billing_empty_cell_is_empty_string_not_nan(tmp_path):
    """결측 셀은 NaN이 아닌 빈 문자열이고, 값은 정제되지 않는다."""
    path = tmp_path / "empty_cell.csv"
    path.write_text(
        ",".join(BILLING_COLUMNS) + "\n"
        'TX-1,2026년 10월 4일,Canva ,,월깐,5,3,"1,000",pii\n',
        encoding="utf-8",
    )

    df = load_billing_csv(str(path))

    assert df.iloc[0]["department"] == ""  # NaN 아님
    assert df.iloc[0]["billing_date"] == "2026년 10월 4일"  # 날짜 변환 금지
    assert df.iloc[0]["service_name"] == "Canva "  # 공백 제거 금지
    assert df.iloc[0]["billing_cycle"] == "월깐"  # 오타 보정 금지


def test_billing_numeric_looking_values_stay_strings(tmp_path):
    """추가: 숫자처럼 보이는 값도 문자열 그대로 (dtype=str 지정 여부를 판정)."""
    path = tmp_path / "numeric_like.csv"
    path.write_text(
        ",".join(BILLING_COLUMNS) + "\n"
        "0001,2026-10-01,Zoom,개발,월간,05,3,270000,pii\n",
        encoding="utf-8",
    )

    df = load_billing_csv(str(path))

    assert df.iloc[0]["tx_id"] == "0001"  # 선행 0 보존
    assert df.iloc[0]["seat_count"] == "05"  # int 5로 변환 금지
    assert df.iloc[0]["billing_amount_krw"] == "270000"  # int 변환 금지
    assert all(isinstance(v, str) for v in df.to_numpy().ravel())

def test_catalog_utf8_bom_file_is_readable(tmp_path):
    """추가: BOM이 붙은 UTF-8 JSON도 읽힌다."""
    import json

    path = tmp_path / "bom.json"
    path.write_bytes(
        b"\xef\xbb\xbf" + json.dumps({"meta": {}, "tools": []}).encode("utf-8")
    )

    assert load_saas_catalog(str(path)) == {"meta": {}, "tools": []}


def test_mask_pii_normal():
    # 정상 케이스: pii 열이 존재하는 경우
    df = pd.DataFrame({
        "tx_id": ["T1", "T2"],
        "card_holder_pii": ["홍길동 / hong@test.kr / 1234", "김철수 / kim@test.kr / 5678"]
    })
    result = mask_pii_data(df)
    assert result["card_holder_pii"].iloc[0] == "[REDACTED]"
    assert result["card_holder_pii"].iloc[1] == "[REDACTED]"
    # 원본이 훼손되지 않았는지 확인
    assert df["card_holder_pii"].iloc[0] != "[REDACTED]"

def test_mask_pii_boundary_missing_column():
    # 경계/예외 케이스: pii 열이 아예 없는 경우 에러 없이 통과해야 함
    df = pd.DataFrame({"tx_id": ["T1", "T2"], "amount": [100, 200]})
    result = mask_pii_data(df)
    assert "card_holder_pii" not in result.columns
    assert result["amount"].iloc[0] == 100

def test_mask_pii_exception_empty_df():
    # 예외 케이스: 빈 데이터프레임
    df = pd.DataFrame(columns=["tx_id", "card_holder_pii"])
    result = mask_pii_data(df)
    assert len(result) == 0
    assert "card_holder_pii" in result.columns