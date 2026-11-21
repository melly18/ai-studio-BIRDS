"""12주차: CSV 인코딩 감지(load_csv_with_encoding) 및 하위 호환 래퍼 테스트 (정상/경계/예외)."""

import io
from pathlib import Path

import pandas as pd
import pytest

import backend

TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "test_data"


def _open_bytes(name: str) -> io.BytesIO:
    return io.BytesIO((TEST_DATA_DIR / name).read_bytes())


def test_load_csv_with_encoding_utf8():
    """정상: UTF-8(BOM 포함) 파일은 'utf-8'로 감지되고 BOM이 컬럼명에 남지 않는다."""
    df, encoding = backend.load_csv_with_encoding(_open_bytes("test_normal.csv"))

    assert encoding == "utf-8"
    assert "tx_id" in df.columns


def test_load_csv_with_encoding_cp949_fallback():
    """경계: CP949 파일은 UTF-8 실패 후 'cp949'로 재시도되어 한글이 정상 복원된다."""
    df, encoding = backend.load_csv_with_encoding(_open_bytes("test_cp949.csv"))

    assert encoding == "cp949"
    assert "마케팅" in df["department"].tolist()


def test_load_csv_with_encoding_empty_file_raises():
    """예외: 빈 파일은 ValueError로 변환되어 UI의 st.error 경로로 전달된다."""
    with pytest.raises(ValueError):
        backend.load_csv_with_encoding(io.BytesIO(b""))


def test_load_csv_with_fallback_backward_compatible():
    """하위 호환: 기존 래퍼는 여전히 DataFrame 하나만 반환한다."""
    df = backend.load_csv_with_fallback(_open_bytes("test_cp949.csv"))

    assert isinstance(df, pd.DataFrame)
    assert "마케팅" in df["department"].tolist()
