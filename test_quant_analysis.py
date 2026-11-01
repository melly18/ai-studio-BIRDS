import pytest
import pandas as pd

"""
calculate_seat_leakage 함수에 대한 단위 테스트를 수행한다.
정상 1건, 경계 1건, 예외 1건을 테스트한다.
"""
from quant_analysis import SeatLeakage, calculate_seat_leakage

def test_calculate_leakage_normal():   #정상 케이스 테스트
    clean_df = pd.DataFrame([
        {
            "service_name": "Figma",
            "seat_count": 10,
            "active_users": 4,
            "monthly_cost_krw": 150000
        },
        {
            "service_name": "Jira",
            "seat_count": 20,
            "active_users": 15,
            "monthly_cost_krw": 200000
        },
        {
            "service_name": "Figma",
            "seat_count": 5,
            "active_users": 3,
            "monthly_cost_krw": 75000
        }
    ])

    result = calculate_seat_leakage(clean_df)

    assert len(result) == 2
    assert result[0] == SeatLeakage("Figma", 8, 120000)
    assert result[1] == SeatLeakage("Jira", 5, 50000)

def test_calculate_leakage_zero_seats():  #경계 케이스 테스트: 유휴 좌석이 0인 경우
    clean_df = pd.DataFrame([
        {
            "service_name": "Figma",
            "seat_count": 10,
            "active_users": 10,
            "monthly_cost_krw": 150000
        }
    ])

    result = calculate_seat_leakage(clean_df)

    assert result == [SeatLeakage("Figma", 0, 0)]

def test_calculate_leakage_excess_users():   #예외 케이스 테스트: 유휴 좌석이 음수인 경우
    clean_df = pd.DataFrame([
        {
            "service_name": "Figma",
            "seat_count": 5,
            "active_users": 7,
            "monthly_cost_krw": 100000
        }
    ])

    with pytest.raises(ValueError):
        calculate_seat_leakage(clean_df)