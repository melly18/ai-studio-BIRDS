from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

import pandas as pd

CSV_ENCODING = "utf-8-sig"  # Excel 저장 CSV의 BOM 대응
CATALOG_ENCODING = "utf-8-sig"  # 공급사 카탈로그 JSON의 BOM 대응
CATALOG_REQUIRED_KEYS = ("meta", "tools")  # 공급사 카탈로그 최상위 필수 키
TOOL_REQUIRED_KEYS = (  # 공급사 카탈로그 도구별 필수 키
    "tool_id",
    "service_name",
    "aliases",
    "category_tags",
    "pricing_tiers",
)

def load_billing_csv(file_path: str) -> pd.DataFrame:
    """결제 내역 CSV 파일을 원본 문자열 DataFrame으로 불러온다.

    Args:
        file_path (str): 불러올 결제 내역 CSV 파일의 경로.

    Returns:
        pd.DataFrame: 모든 값을 문자열로 읽은 결제 내역 DataFrame.

    Raises:
        FileNotFoundError: 지정한 CSV 파일이 존재하지 않는 경우.
        ValueError: 인코딩 오류, 빈 파일, CSV 형식 오류인 경우.
    """
    try:
        return pd.read_csv(
            file_path,
            encoding=CSV_ENCODING,
            dtype=str,              # 타입 변환은 이후 정제 단계에서 수행
            keep_default_na=False,  # "NA" 등 문자열을 결측치로 바꾸지 않음
        )
    except (
        UnicodeDecodeError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
    ) as exc:
        raise ValueError("결제 내역 CSV를 읽을 수 없습니다.") from exc

def load_saas_catalog(catalog_path: str) -> dict[str, Any]:
    """공급사 카탈로그 JSON 파일을 읽어 필수 키를 검증하고 반환한다.

    Args:
        catalog_path (str): 불러올 공급사 카탈로그 JSON 파일의 경로.

    Returns:
        dict[str, Any]: ``meta``와 ``tools`` 키를 포함하고 필수 구조를
            만족하는 공급사 카탈로그.

    Raises:
        FileNotFoundError: 지정한 카탈로그 파일이 존재하지 않는 경우 발생.
        ValueError: JSON을 읽을 수 없거나 최상위 구조가 dict가 아니거나,
            필수 키 또는 도구 정보가 누락되거나 잘못된 형식인 경우 발생.
    """
    try:
        with open(catalog_path, encoding=CATALOG_ENCODING) as catalog_file:
            catalog = json.load(catalog_file)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("카탈로그 JSON을 읽을 수 없습니다.") from exc
    
    if not isinstance(catalog, dict):
        raise ValueError("카탈로그 최상위 구조는 dict여야 합니다.")

    for key in CATALOG_REQUIRED_KEYS:
        if key not in catalog:
            raise ValueError(f"필수 키 누락: {key}")

    if not isinstance(catalog["meta"], dict):
        raise ValueError("meta는 dict여야 합니다.")
    if not isinstance(catalog["tools"], list):
        raise ValueError("tools는 list여야 합니다.")

    for index, tool in enumerate(catalog["tools"]):
        if not isinstance(tool, dict):
            raise ValueError(f"tools[{index}]는 dict여야 합니다.")
        for key in TOOL_REQUIRED_KEYS:
            if key not in tool:
                raise ValueError(f"tools[{index}] 필수 키 누락: {key}")

    return catalog


# 모듈 상단 상수 정의 (매직 스트링 상수화 리팩터링)
PII_TARGET_COLUMN: str = "card_holder_pii"
PII_MASK_TOKEN: str = "[REDACTED]"


def mask_pii_data(df: pd.DataFrame) -> pd.DataFrame:
    """결제 내역 DataFrame의 개인정보(card_holder_pii) 컬럼을 마스킹한 복사본을 반환한다.

    Args:
        df (pd.DataFrame): 정제 전후의 결제 내역 DataFrame (컬럼: card_holder_pii 포함 가능).

    Returns:
        pd.DataFrame: 'card_holder_pii' 컬럼 값이 '[REDACTED]'로 치환된 새 DataFrame.
            빈 DataFrame이 입력되면 동일한 구조의 빈 복사본을 반환한다.

    Raises:
        TypeError: 입력된 df가 pandas DataFrame이 아닐 경우 발생.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"pd.DataFrame 타입이 필요합니다: {type(df).__name__}")

    # Guard Clause: 빈 DataFrame은 불필요한 컬럼 탐색 없이 즉시 복사본 반환
    if df.empty:
        return df.copy()

    masked_df = df.copy()
    if PII_TARGET_COLUMN in masked_df.columns:
        masked_df[PII_TARGET_COLUMN] = PII_MASK_TOKEN
    return masked_df


CLEAN_REQUIRED_COLUMNS: tuple[str, ...] = (
    "tx_id",
    "billing_date",
    "service_name",
    "department",
    "billing_cycle",
    "seat_count",
    "active_users",
    "billing_amount_krw",
    "card_holder_pii",
)
CLEAN_OUTPUT_COLUMNS: tuple[str, ...] = (
    "tx_id",
    "billing_date",
    "service_name",
    "department",
    "billing_cycle",
    "seat_count",
    "active_users",
    "billing_amount_krw",
    "card_holder_pii",
    "monthly_cost_krw",
)


def _coerce_text(value: object) -> str:
    """결측값을 빈 문자열로 바꾸고, 공백을 정리한 문자열을 반환한다."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def _warning(tx_id: str, reason: str, action: str) -> dict:
    """경고 엔트리를 생성한다."""
    return {"tx_id": str(tx_id or ""), "reason": reason, "action": action}


def parse_date(value: object) -> str:
    """날짜 문자열을 YYYY-MM-DD 형식으로 통일한다.

    다양한 입력 형식(예: YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD, 한글 날짜)을
    표준 ISO 형식으로 변환한다. 변환이 불가능하면 ValueError를 발생시킨다.
    """
    text = _coerce_text(value)
    patterns = [
        (r"^\d{4}-\d{1,2}-\d{1,2}$", "%Y-%m-%d"),
        (r"^\d{4}/\d{1,2}/\d{1,2}$", "%Y/%m/%d"),
        (r"^\d{4}\.\d{1,2}\.\d{1,2}$", "%Y.%m.%d"),
        (r"^\d{8}$", "%Y%m%d"),
        (r"^\d{4}년 \d{1,2}월 \d{1,2}일$", "%Y년 %m월 %d일"),
    ]
    for pattern, fmt in patterns:
        if re.fullmatch(pattern, text):
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
    raise ValueError("invalid date")


def normalize_cycle(value: object) -> str:
    """billing_cycle 값을 표준 월간/연간 값으로 변환한다.

    유효하지 않은 값은 ValueError를 발생시켜 상위 단계에서 제외 처리한다.
    """
    text = _coerce_text(value).casefold()
    if text in {"월간", "monthly", "month"}:
        return "월간"
    if text in {"연간", "annual", "yearly"}:
        return "연간"
    raise ValueError("invalid cycle")


def build_alias_map(catalog: dict | None) -> dict[str, str]:
    """카탈로그 alias를 표준 service_name 매핑으로 변환한다.

    각 도구의 service_name과 aliases를 lowercase 기준으로 조회 키로 만들고,
    표준 이름을 값으로 저장한다. 카탈로그가 없거나 잘못된 구조면 빈 맵을 반환한다.
    """
    mapping: dict[str, str] = {}
    if not isinstance(catalog, dict):
        return mapping
    for tool in catalog.get("tools", []):
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("service_name", "")).strip()
        aliases = [str(v).strip() for v in tool.get("aliases", [])]
        for alias in [name, *aliases]:
            if alias:
                mapping[alias.casefold()] = name
    return mapping


def to_monthly(value: int, cycle: str) -> int:
    """월간 단위 비용으로 환산한다.

    월간 결제는 그대로 유지하고, 연간 결제는 12개월 기준으로 반올림하여
    월별 비용으로 변환한다.
    """
    if cycle == "월간":
        return value
    return int((value / 12) + 0.5)


def clean_billing_csv(df: pd.DataFrame, catalog: dict[str, Any]) -> tuple[pd.DataFrame, list[dict]]:
    """결제 내역 CSV를 정제하여 표준 스키마와 경고 목록을 반환한다.

    정제 단계 요약:
        필수 열 검사 → 빈 입력 처리 → tx_id 중복 제외 → billing_date 정규화
        → service_name 표준화 → department 보정 → billing_cycle 정규화
        → seat_count 검증 → active_users 검증 → billing_amount_krw 검증
        → monthly_cost_krw 계산 → 마지막에 빈 tx_id 자동 발급

    Args:
        df (pd.DataFrame): 원본 결제 내역 DataFrame. 각 컬럼 값은 문자열로 들어온다.
        catalog (dict[str, Any]): 서비스 이름 alias 정보를 담은 공급사 카탈로그 딕셔너리.

    Returns:
        tuple[pd.DataFrame, list[dict]]: 정제된 결제 내역 DataFrame과 경고 목록의 튜플.

    Raises:
        ValueError: 필수 컬럼이 누락된 경우 발생한다.
    """
    if df is None:
        return pd.DataFrame(columns=list(CLEAN_OUTPUT_COLUMNS)), []

    # FIXED: T07 재현을 위해 필수 열 검사를 빈 입력 처리보다 먼저 수행
    missing = [col for col in CLEAN_REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"필수 열 누락: {missing[0]}")

    # 0. 빈 입력 처리
    if len(df) == 0:
        return pd.DataFrame(columns=list(CLEAN_OUTPUT_COLUMNS)), []

    work = df.copy()
    warnings: list[dict] = []
    seen_tx_ids: set[str] = set()
    alias_map = build_alias_map(catalog)

    # 1. tx_id
    for idx, row in work.iterrows():
        original_tx = _coerce_text(row["tx_id"])
        if original_tx and original_tx in seen_tx_ids:
            warnings.append(_warning(original_tx, "중복 tx_id로 제외", "제외"))
            work = work.drop(idx)
            continue
        if original_tx:
            seen_tx_ids.add(original_tx)

    work["tx_id"] = work["tx_id"].fillna("").astype(str).str.strip()

    # 2. billing_date
    for idx, row in work.iterrows():
        raw_date = _coerce_text(row["billing_date"])
        try:
            work.at[idx, "billing_date"] = parse_date(raw_date)
        except ValueError:
            warnings.append(_warning(work.at[idx, "tx_id"], f"잘못된 billing_date: {raw_date}", "제외"))
            work = work.drop(idx)

    # 3. service_name
    for idx, row in work.iterrows():
        raw_service = _coerce_text(row["service_name"])
        if raw_service == "":
            warnings.append(_warning(work.at[idx, "tx_id"], "service_name 비어 있어 제외", "제외"))
            work.drop(idx, inplace=True)
            continue
        standard_service = alias_map.get(raw_service.casefold(), raw_service)
        if standard_service != raw_service:
            warnings.append(_warning(work.at[idx, "tx_id"], f"service_name 표준화: {raw_service} -> {standard_service}", "보정"))
        else:
            # FIXED: 미등록 서비스명 유지 경고는 alias_map 미보유일 때만 기록
            if raw_service.casefold() not in alias_map:
                warnings.append(_warning(work.at[idx, "tx_id"], f"미등록 서비스명 유지: {raw_service}", "보정"))
        work.at[idx, "service_name"] = standard_service

    # 4. department
    for idx, row in work.iterrows():
        raw_department = _coerce_text(row["department"])
        if raw_department == "":
            warnings.append(_warning(work.at[idx, "tx_id"], "department 비어 있어 '미상'으로 보정", "보정"))
            work.at[idx, "department"] = "미상"
        else:
            work.at[idx, "department"] = raw_department

    # 5. billing_cycle
    for idx, row in work.iterrows():
        raw_cycle = _coerce_text(row["billing_cycle"])
        try:
            work.at[idx, "billing_cycle"] = normalize_cycle(raw_cycle)
        except ValueError:
            warnings.append(_warning(work.at[idx, "tx_id"], f"잘못된 billing_cycle: {raw_cycle}", "제외"))
            work.drop(idx, inplace=True)

    # 6. seat_count
    work["seat_count"] = pd.to_numeric(work["seat_count"], errors="coerce")
    for idx, row in work.iterrows():
        raw_seat = row["seat_count"]
        if pd.isna(raw_seat):
            warnings.append(_warning(work.at[idx, "tx_id"], f"seat_count 변환 실패: {raw_seat}", "제외"))
            work.drop(idx, inplace=True)
            continue
        seat_count = int(raw_seat)
        if seat_count <= 0:
            warnings.append(_warning(work.at[idx, "tx_id"], f"seat_count <= 0 제외: {seat_count}", "제외"))
            work.drop(idx, inplace=True)
            continue
        work.at[idx, "seat_count"] = seat_count

    # 7. active_users
    work["active_users"] = pd.to_numeric(work["active_users"], errors="coerce")
    for idx, row in work.iterrows():
        raw_active = row["active_users"]
        if pd.isna(raw_active) or _coerce_text(raw_active) == "":
            work.at[idx, "active_users"] = 0
            warnings.append(_warning(work.at[idx, "tx_id"], "active_users 비어 있어 0으로 보정", "보정"))
            continue
        active_users = int(raw_active)
        if active_users < 0:
            active_users = 0
            warnings.append(_warning(work.at[idx, "tx_id"], "active_users 음수이므로 0으로 보정", "보정"))
        if active_users > int(row["seat_count"]):
            active_users = int(row["seat_count"])
            warnings.append(_warning(work.at[idx, "tx_id"], f"active_users가 seat_count를 초과해 {row['seat_count']}로 보정", "보정"))
        work.at[idx, "active_users"] = active_users

    # 8. billing_amount_krw
    work["billing_amount_krw"] = work["billing_amount_krw"].fillna("").astype(str)
    work["billing_amount_krw"] = work["billing_amount_krw"].str.replace(",", "", regex=False)
    work["billing_amount_krw"] = work["billing_amount_krw"].str.replace("원", "", regex=False)
    work["billing_amount_krw"] = work["billing_amount_krw"].str.replace("₩", "", regex=False)
    work["billing_amount_krw"] = pd.to_numeric(work["billing_amount_krw"], errors="coerce")
    for idx, row in work.iterrows():
        raw_amount = row["billing_amount_krw"]
        if pd.isna(raw_amount) or _coerce_text(raw_amount) == "":
            warnings.append(_warning(work.at[idx, "tx_id"], "billing_amount_krw 비어 있어 제외", "제외"))
            work.drop(idx, inplace=True)
            continue
        try:
            # FIXED: 금액 파싱은 int(raw_amount)로 수행
            billing_amount_krw = int(raw_amount)
        except ValueError:
            warnings.append(_warning(work.at[idx, "tx_id"], f"billing_amount_krw 변환 실패: {raw_amount}", "제외"))
            work.drop(idx, inplace=True)
            continue
        if billing_amount_krw < 0:
            warnings.append(_warning(work.at[idx, "tx_id"], f"billing_amount_krw 음수 제외: {billing_amount_krw}", "제외"))
            work.drop(idx, inplace=True)
            continue
        work.at[idx, "billing_amount_krw"] = billing_amount_krw

    # 9. monthly_cost_krw
    for idx, row in work.iterrows():
        cycle = row["billing_cycle"]
        total = int(row["billing_amount_krw"])
        work.loc[idx, "monthly_cost_krw"] = to_monthly(total, cycle)

    # FIXED: 남은 행 중 빈 tx_id만 TX-AUTO-001부터 발급
    empty_tx = work["tx_id"].eq("")
    if empty_tx.any():
        for i, idx in enumerate(work.index[empty_tx], start=1):
            work.at[idx, "tx_id"] = f"TX-AUTO-{i:03d}"

    # FIXED: 결과 직전 숫자형 열을 int로 강제 변환
    work["seat_count"] = work["seat_count"].astype(int)
    work["active_users"] = work["active_users"].astype(int)
    work["billing_amount_krw"] = work["billing_amount_krw"].astype(int)
    work["monthly_cost_krw"] = work["monthly_cost_krw"].astype(int)

    result = work[
        [
            "tx_id",
            "billing_date",
            "service_name",
            "department",
            "billing_cycle",
            "seat_count",
            "active_users",
            "billing_amount_krw",
            "card_holder_pii",
            "monthly_cost_krw",
        ]
    ].copy()
    return result, warnings
