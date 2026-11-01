from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SeatLeakage:
    """서비스의 유휴 좌석 수와 추정 월간 낭비 금액."""

    service_name: str
    inactive_seats: int
    wasted_spend: int


def calculate_seat_leakage(clean_df: pd.DataFrame) -> list[SeatLeakage]:
    """서비스별 유휴 좌석 수와 월간 낭비 금액을 계산한다.

    각 행은 하나의 결제 기록으로 처리한다. 동일한 서비스에 여러 결제 기록이
    있으면 유휴 좌석 수와 낭비 금액을 모든 기록에 대해 합산한다.

    Args:
        clean_df: 필수 컬럼을 포함하는 정제된 결제 기록 데이터프레임.

    Returns:
        ``clean_df``에 서비스가 처음 나타나는 순서의 ``SeatLeakage`` 목록.

    Raises:
        KeyError: 필수 컬럼이 누락된 경우.
        ValueError: 결측치 또는 유효하지 않은 값이 포함된 경우.
    """
    required_columns = {
        "service_name",
        "seat_count",
        "active_users",
        "monthly_cost_krw",
    }
    missing_columns = required_columns.difference(clean_df.columns)
    if missing_columns:
        raise KeyError(f"Missing required columns: {sorted(missing_columns)}")

    if clean_df.empty:
        return []

    if clean_df.isna().any().any():
        raise ValueError("Input data must not contain missing values")

    numeric_columns = ["seat_count", "active_users", "monthly_cost_krw"]
    if (clean_df[numeric_columns] < 0).any().any():
        raise ValueError("Seat counts, active users, and costs must not be negative")

    if (clean_df["seat_count"] == 0).any():
        raise ValueError("seat_count must be greater than zero")

    if (clean_df["active_users"] > clean_df["seat_count"]).any():
        raise ValueError("active_users cannot exceed seat_count")

    records = clean_df.assign(
        inactive_seats=clean_df["seat_count"] - clean_df["active_users"],
        wasted_spend=(
            clean_df["monthly_cost_krw"]
            * (clean_df["seat_count"] - clean_df["active_users"])
            / clean_df["seat_count"]
        ).round().astype(int),
    )

    aggregated = records.groupby("service_name", sort=False)[
        ["inactive_seats", "wasted_spend"]
    ].sum()
    return [
        SeatLeakage(
            service_name=service_name,
            inactive_seats=int(values["inactive_seats"]),
            wasted_spend=int(values["wasted_spend"]),
        )
        for service_name, values in aggregated.iterrows()
    ]