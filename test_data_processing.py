from pathlib import Path
import pytest
import pandas as pd
from data_processing import load_billing_csv, load_saas_catalog, mask_pii_data

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

# load_billing_csv
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


# load_saas_catalog
@pytest.mark.parametrize(
    "content, expected",
    [
        ("[]", "dict"),                                    # 최상위가 list
        ('{"tools": []}', "meta"),                         # meta 누락
        ('{"meta": {}}', "tools"),                         # tools 누락
        ('{"meta": [], "tools": []}', "meta"),             # meta 타입 오류
        ('{"meta": {}, "tools": {}}', "tools"),            # tools 타입 오류
        ('{"meta": {}, "tools": ["x"]}', r"tools\[0\]"),   # tool이 dict 아님
    ],
)
def test_catalog_invalid_structure_raises(tmp_path, content, expected):
    """예외: 최상위·meta·tools·tool 구조 오류는 ValueError."""
    path = tmp_path / "invalid.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match=expected):
        load_saas_catalog(str(path))

def test_catalog_utf8_bom_allowed(tmp_path):
    """경계: BOM이 붙은 UTF-8 파일도 정상 로드된다."""
    import json

    path = tmp_path / "bom.json"
    path.write_text(json.dumps({"meta": {}, "tools": []}), encoding="utf-8-sig")

    assert load_saas_catalog(str(path)) == {"meta": {}, "tools": []}
    
def test_catalog_normal_sample():
    """정상: 실제 샘플 카탈로그 30개 도구가 원본 그대로 로드된다."""
    import json
 
    result = load_saas_catalog(str(CATALOG_SAMPLE))
 
    assert len(result["tools"]) == 30
    assert result["meta"]["catalog_version"] == "v1.0"
    assert result["tools"][0]["service_name"] == "Figma"
    with open(CATALOG_SAMPLE, encoding="utf-8") as f:
        assert result == json.load(f)  # 변환·추가 없이 원본과 동일
 
def test_catalog_empty_tools_allowed(tmp_path):
    """경계: 필수 키는 있으나 tools가 빈 리스트면 그대로 반환."""
    import json
 
    path = tmp_path / "empty_tools.json"
    path.write_text(json.dumps({"meta": {}, "tools": []}), encoding="utf-8")
 
    assert load_saas_catalog(str(path)) == {"meta": {}, "tools": []}
 
def test_catalog_missing_tool_key_raises(tmp_path):
    """예외: tools[0]에서 aliases가 빠지면 ValueError, 메시지에 aliases 포함."""
    import json
 
    tool = _tool()
    del tool["aliases"]
    path = tmp_path / "missing_aliases.json"
    path.write_text(json.dumps({"meta": {}, "tools": [tool]}), encoding="utf-8")
 
    with pytest.raises(ValueError, match="aliases"):
        load_saas_catalog(str(path))
 
def test_catalog_file_not_found():
    """예외: 존재하지 않는 경로는 FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_saas_catalog("no_such_catalog.json")
 
def test_catalog_broken_json_raises_value_error(tmp_path):
    """예외: JSON 문법 오류는 ValueError."""
    path = tmp_path / "broken.json"
    path.write_text('{"meta": {}, "tools": [', encoding="utf-8")
 
    with pytest.raises(ValueError):
        load_saas_catalog(str(path))
    

# mask_pii_data
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