import pytest
import pandas as pd
from data_processing import mask_pii_data

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