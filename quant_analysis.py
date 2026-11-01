from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SeatLeakage:
    """서비스의 유휴 좌석 수와 추정 월간 낭비 금액."""

    service_name: str  #툴 이름
    inactive_seats: int  #유휴 좌석 수
    wasted_spend: int   #낭비 금액


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