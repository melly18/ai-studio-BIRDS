"""12주차: 업로드 전 필수 열 안내·템플릿 CSV 백엔드 함수 테스트 (정상/경계/예외)."""

import io

import backend
import core.data_processing as dp


def test_required_columns_guide_matches_validation_schema():
    """정상: 안내 표의 열 목록이 실제 검증 기준(CLEAN_REQUIRED_COLUMNS)과 순서까지 일치."""
    guide = backend.get_required_columns_guide()

    assert list(guide.columns) == ["열 이름", "설명", "예시"]
    assert guide["열 이름"].tolist() == list(dp.CLEAN_REQUIRED_COLUMNS)
    assert len(guide) == 9
    assert (guide["설명"] != "").all()
    assert (guide["예시"] != "").all()


def test_template_csv_header_and_bom():
    """경계: 템플릿은 BOM 포함 UTF-8이며, 헤더 + 예시 1행으로만 구성된다."""
    data = backend.get_template_csv_bytes()

    assert data.startswith(b"\xef\xbb\xbf")
    lines = data.decode("utf-8-sig").strip().splitlines()
    assert len(lines) == 2
    assert lines[0].split(",") == list(dp.CLEAN_REQUIRED_COLUMNS)


def test_template_csv_example_pii_is_fictional():
    """예외 방지: 예시 PII는 가상 값(example.com / 0000 카드번호)만 사용한다."""
    text = backend.get_template_csv_bytes().decode("utf-8-sig")

    assert "example.com" in text
    assert "0000-0000-0000-0000" in text


def test_template_csv_roundtrip_through_loader():
    """정상: 내려받은 템플릿을 그대로 업로드해도 로더가 필수 열 누락 없이 읽는다."""
    df = backend.load_csv_with_fallback(io.BytesIO(backend.get_template_csv_bytes()))

    missing = [c for c in dp.CLEAN_REQUIRED_COLUMNS if c not in df.columns]
    assert missing == []
    assert len(df) == 1
