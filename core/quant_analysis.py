from itertools import combinations
from typing import TypedDict

import pandas as pd


class SeatLeakage(TypedDict):
    """서비스의 유휴 좌석 수와 추정 월간 낭비 금액."""

    service_name: str  #툴 이름
    inactive_seats: int  #유휴 좌석 수
    wasted_spend: int   #낭비 금액


class DuplicatePair(TypedDict):
    """공통 카테고리 태그를 가진 두 SaaS와 공통 태그 집합."""

    tools: set[str]
    common_tags: set[str]


def calculate_seat_leakage(clean_df: pd.DataFrame) -> list[SeatLeakage]:
    """서비스별 유휴 좌석 수와 월간 낭비 금액을 계산한다.

    각 행은 하나의 결제 기록으로 처리한다. 동일한 서비스에 여러 결제 기록이
    있으면 유휴 좌석 수와 낭비 금액을 모든 기록에 대해 합산한다.

    Args:
        clean_df: 필수 컬럼을 포함하는 정제된 결제 기록 데이터프레임.

    Returns:
        ``clean_df``에 서비스가 처음 나타나는 순서의 ``SeatLeakage`` 리스트.

    Raises:
        TypeError: 입력이 pandas DataFrame이 아닌 경우.
        KeyError: 필수 컬럼이 누락된 경우.
        ValueError: 결측치 또는 유효하지 않은 값이 포함된 경우.
    """
    if not isinstance(clean_df, pd.DataFrame):    #입력이 df가 아닐 때 에러 발생
        raise TypeError("Input must be a pandas DataFrame")
    
    required_columns = {   #꼭 필요한 컬럼들
        "service_name",
        "seat_count",
        "active_users",
        "monthly_cost_krw",
    }
    missing_columns = required_columns.difference(clean_df.columns)   #필요 컬럼이 모두 있는지 확인
    if missing_columns:
        raise KeyError(f"Missing required columns: {sorted(missing_columns)}")

    if clean_df.empty:   #빈 df라면 빈 리스트 반환
        return []

    if clean_df[list(required_columns)].isna().any().any():   #필요 컬럼들의 결측치 확인
        raise ValueError("Input data must not contain missing values")

    numeric_columns = ["seat_count", "active_users", "monthly_cost_krw"]  #이상치 확인 필요한 숫자형 컬럼들
    if (clean_df[numeric_columns] < 0).any().any():   #음수 포함시 에러 발생
        raise ValueError("Seat counts, active users, and costs must not be negative")

    if (clean_df["seat_count"] == 0).any():   #seat_count가 0인 경우 에러 발생(0으로는 나눌 수 없음)
        raise ValueError("seat_count must be greater than zero")

    if (clean_df["active_users"] > clean_df["seat_count"]).any():   #active_users가 seat_count보다 큰 경우 에러 발생(유휴 좌석 음수)
        raise ValueError("active_users cannot exceed seat_count")

    calculated_df = clean_df.assign(   #유휴 좌석 컬럼 생성
        inactive_seats=clean_df["seat_count"] - clean_df["active_users"]
    )
    calculated_df = calculated_df.assign(   #낭비 금액 컬럼 생성(좌석당 단가 * 유휴 좌석 수)
        wasted_spend=(
            calculated_df["monthly_cost_krw"]
            * calculated_df["inactive_seats"]
            / calculated_df["seat_count"]
        ).round().astype(int)
    )

    leakage_report = (
        calculated_df.groupby("service_name", sort=False)[
            ["inactive_seats", "wasted_spend"]
        ]
        .sum()
        .reset_index()
    )

    return leakage_report.to_dict("records")


def _extract_string_list(raw_value: object) -> list[str]:
    """문자열 또는 시퀀스에서 유효한 문자열 목록을 중복 없이 추출한다."""
    if isinstance(raw_value, str):
        raw_value = [raw_value]
    if not isinstance(raw_value, (list, tuple, set)):
        return []
    return list(
        dict.fromkeys(
            item for item in raw_value if isinstance(item, str) and item.strip()
        )
    )


def detect_duplicate_tags(clean_df: pd.DataFrame, catalog: dict) -> list[DuplicatePair]:
    """사용 중인 SaaS 중 공통 카테고리 태그를 가진 쌍을 찾는다.

    ``clean_df``에서는 ``service_name``만 사용하며, 서비스명 또는 카탈로그의
    별칭으로 카탈로그 항목을 식별한다. 결과의 서비스명은 카탈로그의
    ``service_name``이다.

    Args:
        clean_df: ``service_name`` 컬럼을 포함하는 정제된 결제 데이터프레임.
        catalog: ``tools`` 키에 SaaS 카탈로그 목록을 담은 딕셔너리.

    Returns:
        ``{"tools": {서비스명1, 서비스명2}, "common_tags": {공통태그...}}`` 형식의
        ``DuplicatePair`` 리스트.
        공통 태그가 없거나 입력 데이터 또는 카탈로그가 비어 있으면 빈 목록을
        반환한다.

    Raises:
        TypeError: ``clean_df``가 pandas DataFrame이 아닌 경우.
        KeyError: 비어 있지 않은 ``clean_df``에 ``service_name``이 없는 경우.
    """
    if not isinstance(clean_df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame")

    if clean_df.empty or not catalog or not catalog.get("tools"):
        return []

    if "service_name" not in clean_df.columns:
        raise KeyError("Missing required column: service_name")

    catalog_tools = catalog["tools"]
    used_names = {
        value.strip().casefold()
        for value in clean_df["service_name"]
        if isinstance(value, str) and value.strip()
    }

    matched_catalog: list[tuple[str, set[str]]] = []
    seen_service_names: set[str] = set()
    for item in catalog_tools:
        if not isinstance(item, dict):
            continue

        service_name = item.get("service_name")
        if not isinstance(service_name, str) or not service_name.strip():
            continue

        canonical_name = service_name.strip()
        canonical_key = canonical_name.casefold()
        if canonical_key in seen_service_names:
            continue

        aliases = _extract_string_list(item.get("aliases", []))
        names = {canonical_key, *(alias.strip().casefold() for alias in aliases)}
        if used_names.isdisjoint(names):
            continue

        normalized_tags = set(_extract_string_list(item.get("category_tags", [])))
        matched_catalog.append((canonical_name, normalized_tags))
        seen_service_names.add(canonical_key)

    duplicate_pairs: list[DuplicatePair] = []
    for (first_name, first_tags), (second_name, second_tags) in combinations(
        matched_catalog, 2
    ):
        common_tags = first_tags & second_tags
        if common_tags:
            duplicate_pairs.append(
                {"tools": {first_name, second_name}, "common_tags": common_tags}
            )

    return duplicate_pairs
