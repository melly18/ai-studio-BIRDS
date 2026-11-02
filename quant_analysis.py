from dataclasses import dataclass

import pandas as pd

import pylance


@dataclass(frozen=True)
class SeatLeakage:
    """서비스의 유휴 좌석 수와 추정 월간 낭비 금액."""

    service_name: str  #툴 이름
    inactive_seats: int  #유휴 좌석 수
    wasted_spend: int   #낭비 금액


DuplicatePair = list[str]


def calculate_seat_leakage(clean_df: pd.DataFrame) -> list[SeatLeakage]:
    """서비스별 유휴 좌석 수와 월간 낭비 금액을 계산한다.

    각 행은 하나의 결제 기록으로 처리한다. 동일한 서비스에 여러 결제 기록이
    있으면 유휴 좌석 수와 낭비 금액을 모든 기록에 대해 합산한다.

    Args:
        clean_df: 필수 컬럼을 포함하는 정제된 결제 기록 데이터프레임.

    Returns:
        ``clean_df``에 서비스가 처음 나타나는 순서의 ``SeatLeakage`` 목록.

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

    records = clean_df.assign(   #유휴 좌석 컬럼 생성
        inactive_seats=clean_df["seat_count"] - clean_df["active_users"]
    )
    records = records.assign(   #낭비 금액 컬럼 생성(좌석당 단가 * 유휴 좌석 수)
        wasted_spend=(
            records["monthly_cost_krw"]
            * records["inactive_seats"]
            / records["seat_count"]
        ).round().astype(int)
    )

    aggregated = records.groupby("service_name", sort=False)[   #툴 별로 합산
        ["inactive_seats", "wasted_spend"]
    ].sum()

    return [    #list[SeatLeakage] 형태로 반환
        SeatLeakage(
            service_name=service_name,
            inactive_seats=int(values["inactive_seats"]),
            wasted_spend=int(values["wasted_spend"]),
        )
        for service_name, values in aggregated.iterrows()
    ]


def detect_duplicate_tags(clean_df: pd.DataFrame, catalog: dict) -> list[DuplicatePair]:
    """사용 중인 SaaS 중 공통 카테고리 태그를 가진 쌍을 찾는다.

    ``clean_df``에서는 ``service_name``만 사용하며, 서비스명 또는 카탈로그의
    별칭으로 카탈로그 항목을 식별한다. 결과의 서비스명은 카탈로그의
    ``service_name``이고, 공통 태그는 카탈로그에 정의된 순서를 따른다.

    Args:
        clean_df: ``service_name`` 컬럼을 포함하는 정제된 결제 데이터프레임.
        catalog: ``tools`` 키에 SaaS 카탈로그 목록을 담은 딕셔너리.

    Returns:
        ``[서비스명1, 서비스명2, 공통태그...]`` 형식의 중복 서비스 쌍 목록.
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

    matched_catalog = []
    seen_service_names = set()
    for item in catalog_tools:
        if not isinstance(item, dict):
            continue

        service_name = item.get("service_name")
        if not isinstance(service_name, str) or not service_name.strip():
            continue

        canonical_name = service_name.strip()
        canonical_key = canonical_name.casefold()
        aliases = item.get("aliases", [])
        if isinstance(aliases, str):
            aliases = [aliases]
        if not isinstance(aliases, (list, tuple, set)):
            aliases = []

        names = {canonical_key}
        names.update(
            alias.strip().casefold()
            for alias in aliases
            if isinstance(alias, str) and alias.strip()
        )
        if used_names.isdisjoint(names) or canonical_key in seen_service_names:
            continue

        tags = item.get("category_tags", [])
        if isinstance(tags, str):
            tags = [tags]
        if not isinstance(tags, (list, tuple, set)):
            tags = []
        normalized_tags = []
        for tag in tags:
            if isinstance(tag, str) and tag not in normalized_tags:
                normalized_tags.append(tag)

        matched_catalog.append((canonical_name, normalized_tags))
        seen_service_names.add(canonical_key)

    duplicate_pairs = []
    for index, (first_name, first_tags) in enumerate(matched_catalog):
        for second_name, second_tags in matched_catalog[index + 1:]:
            second_tag_set = set(second_tags)
            common_tags = [
                tag for tag in first_tags
                if tag in second_tag_set
            ]
            if common_tags:
                duplicate_pairs.append([first_name, second_name, *common_tags])

    return duplicate_pairs
