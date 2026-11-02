from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

def load_billing_csv(file_path: str) -> pd.DataFrame:
    """결제 내역 CSV 파일을 원본 문자열 DataFrame으로 불러온다."""
    try:
        return pd.read_csv(
            file_path,
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False,
        )
    except (
        UnicodeDecodeError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
    ) as exc:
        raise ValueError("결제 내역 CSV를 읽을 수 없습니다.") from exc


def mask_pii_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: # 코드 리딩 후 빈 데이터프레임 방어 로직
        return df.copy()
    
    """Return a copy of the payment data with cardholder PII redacted."""
    masked_df = df.copy()
    if "card_holder_pii" in masked_df.columns:
        masked_df["card_holder_pii"] = "[REDACTED]"
    return masked_df


def _warning(tx_id: str, reason: str, action: str) -> dict:
    return {"tx_id": str(tx_id or ""), "reason": reason, "action": action}


def parse_date(value) -> str:
    """날짜 문자열을 YYYY-MM-DD 형식으로 통일한다."""
    text = str(value).strip()
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


def normalize_cycle(value) -> str:
    """billing_cycle 값을 표준 월간/연간 값으로 변환한다."""
    text = str(value).strip().casefold()
    if text in {"월간", "monthly", "month"}:
        return "월간"
    if text in {"연간", "annual", "yearly"}:
        return "연간"
    raise ValueError("invalid cycle")


def build_alias_map(catalog: dict | None) -> dict[str, str]:
    """catalog의 alias를 표준 service_name 맵으로 만든다."""
    mapping = {}
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
    """월별 비용으로 환산한다."""
    if cycle == "월간":
        return value
    return int((value / 12) + 0.5)


def clean_billing_csv(df: pd.DataFrame, catalog: dict) -> tuple[pd.DataFrame, list[dict]]:
    required_cols = [
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
    empty_columns = [
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

    if df is None:
        return pd.DataFrame(columns=empty_columns), []

    # FIXED: T07 재현을 위해 필수 열 검사를 빈 입력 처리보다 먼저 수행
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"필수 열 누락: {missing[0]}")

    # 0. 빈 입력 처리
    if len(df) == 0:
        return pd.DataFrame(columns=empty_columns), []

    work = df.copy()
    warnings: list[dict] = []
    seen_tx_ids: set[str] = set()
    auto_index = 1
    alias_map = build_alias_map(catalog)

    # 1. tx_id
    for idx, row in work.iterrows():
        original_tx = "" if pd.isna(row["tx_id"]) else str(row["tx_id"]).strip()
        if original_tx and original_tx in seen_tx_ids:
            warnings.append(_warning(original_tx, "중복 tx_id로 제외", "제외"))
            work.drop(idx, inplace=True)
            continue
        if original_tx:
            seen_tx_ids.add(original_tx)

    work["tx_id"] = work["tx_id"].fillna("").astype(str).str.strip()

    # 2. billing_date
    for idx, row in work.iterrows():
        raw_date = "" if pd.isna(row["billing_date"]) else str(row["billing_date"]).strip()
        try:
            work.at[idx, "billing_date"] = parse_date(raw_date)
        except ValueError:
            warnings.append(_warning(work.at[idx, "tx_id"], f"잘못된 billing_date: {raw_date}", "제외"))
            work.drop(idx, inplace=True)

    # 3. service_name
    for idx, row in work.iterrows():
        raw_service = "" if pd.isna(row["service_name"]) else str(row["service_name"]).strip()
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
        raw_department = "" if pd.isna(row["department"]) else str(row["department"]).strip()
        if raw_department == "":
            warnings.append(_warning(work.at[idx, "tx_id"], "department 비어 있어 '미상'으로 보정", "보정"))
            work.at[idx, "department"] = "미상"
        else:
            work.at[idx, "department"] = raw_department

    # 5. billing_cycle
    for idx, row in work.iterrows():
        raw_cycle = "" if pd.isna(row["billing_cycle"]) else str(row["billing_cycle"]).strip()
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
        if pd.isna(raw_active) or str(raw_active).strip() == "":
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
        if pd.isna(raw_amount) or str(raw_amount).strip() == "":
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
        work.at[idx, "monthly_cost_krw"] = to_monthly(total, cycle)

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