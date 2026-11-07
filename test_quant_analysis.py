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
            "tx_id": "TX-0001",
            "billing_date": "2026-10-05",
            "service_name": "Figma",
            "department": "디자인",
            "billing_cycle": "월간",
            "seat_count": 10,
            "active_users": 4,
            "billing_amount_krw": 150000,
            "card_holder_pii": "[REDACTED]",
            "monthly_cost_krw": 150000
        },
        {
            "tx_id": "TX-0002",
            "billing_date": "2026-10-06",
            "service_name": "Jira",
            "department": "개발",
            "billing_cycle": "월간",
            "seat_count": 20,
            "active_users": 15,
            "billing_amount_krw": 200000,
            "card_holder_pii": "[REDACTED]",
            "monthly_cost_krw": 200000
        },
        {
            "tx_id": "TX-0003",
            "billing_date": "2026-10-07",
            "service_name": "Figma",
            "department": "마케팅",
            "billing_cycle": "연간",
            "seat_count": 5,
            "active_users": 3,
            "billing_amount_krw": 900000,
            "card_holder_pii": "[REDACTED]",
            "monthly_cost_krw": 75000
        }
    ])

    result = calculate_seat_leakage(clean_df)

    assert len(result) == 2
    assert result[0] == SeatLeakage(service_name="Figma", inactive_seats=8, wasted_spend=120000)
    assert result[1] == SeatLeakage(service_name="Jira", inactive_seats=5, wasted_spend=50000)

def test_calculate_leakage_zero_seats():  #경계 케이스 테스트: 유휴 좌석이 0인 경우
    clean_df = pd.DataFrame([
        {
            "tx_id": "TX-0001",
            "billing_date": "2026-10-05",
            "service_name": "Figma",
            "department": "디자인",
            "billing_cycle": "월간",
            "seat_count": 10,
            "active_users": 10,
            "billing_amount_krw": 150000,
            "card_holder_pii": "[REDACTED]",
            "monthly_cost_krw": 150000
        }
    ])

    result = calculate_seat_leakage(clean_df)

    assert result == [SeatLeakage(service_name="Figma", inactive_seats=0, wasted_spend=0)]

def test_calculate_leakage_excess_users():   #예외 케이스 테스트: 유휴 좌석이 음수인 경우
    clean_df = pd.DataFrame([
        {
            "tx_id": "TX-0001",
            "billing_date": "2026-10-05",
            "service_name": "Figma",
            "department": "디자인",
            "billing_cycle": "월간",
            "seat_count": 5,
            "active_users": 7,
            "billing_amount_krw": 100000,
            "card_holder_pii": "[REDACTED]",
            "monthly_cost_krw": 100000
        }
    ])

    with pytest.raises(ValueError):
        calculate_seat_leakage(clean_df)

"""
calculate_seat_leakage 함수에 대한 단위 테스트를 수행한다.
정상 2건, 경계 1건, 예외 2건을 테스트한다.
"""
from quant_analysis import detect_duplicate_tags


def test_detect_duplicate_tags_case_1():
    clean_df = pd.DataFrame(
        [
            {"service_name": "Notion"},
            {"service_name": "Jira"},
            {"service_name": "ClickUp"},
        ]
    )
    catalog = {
        "tools": [
            {
                "tool_id": "notion",
                "service_name": "Notion",
                "aliases": ["노션", "notion", "NOTION"],
                "category_tags": [
                    "documentation",
                    "project_management",
                    "knowledge_management",
                ],
            },
            {
                "tool_id": "jira",
                "service_name": "Jira",
                "aliases": ["지라", "jira", "JIRA"],
                "category_tags": [
                    "project_management",
                    "task_tracking",
                    "development",
                ],
            },
            {
                "tool_id": "clickup",
                "service_name": "ClickUp",
                "aliases": ["클릭업", "clickup", "CLICKUP"],
                "category_tags": ["project_management", "documentation"],
            },
        ]
    }

    assert detect_duplicate_tags(clean_df, catalog) == [
        {"tools": {"Notion", "Jira"}, "common_tags": {"project_management"}},
        {"tools": {"Notion", "ClickUp"}, "common_tags": {"documentation", "project_management"}},
        {"tools": {"Jira", "ClickUp"}, "common_tags": {"project_management"}},
    ]


def test_detect_duplicate_tags_case_2():
    clean_df = pd.DataFrame(
        [{"service_name": "Figma"}, {"service_name": "Jira"}]
    )
    catalog = {
        "tools": [
            {
                "tool_id": "figma",
                "service_name": "Figma",
                "aliases": ["피그마", "figma", "FIGMA"],
                "category_tags": ["design", "prototyping", "whiteboarding"],
            },
            {
                "tool_id": "jira",
                "service_name": "Jira",
                "aliases": ["지라", "jira", "JIRA"],
                "category_tags": [
                    "project_management",
                    "task_tracking",
                    "development",
                ],
            },
        ]
    }

    assert detect_duplicate_tags(clean_df, catalog) == []


def test_detect_duplicate_tags_case_3():
    clean_df = pd.DataFrame(
        [
            {"service_name": "Figma"},
            {"service_name": "Jira"},
            {"service_name": "ClickUp"},
        ]
    )
    catalog = {
        "tools": [
            {
                "tool_id": "figma",
                "service_name": "Figma",
                "aliases": ["피그마", "figma", "FIGMA"],
                "category_tags": ["design", "prototyping", "whiteboarding"],
            },
            {
                "tool_id": "jira",
                "service_name": "Jira",
                "aliases": ["지라", "jira", "JIRA"],
                "category_tags": [
                    "project_management",
                    "task_tracking",
                    "development",
                ],
            },
            {
                "tool_id": "clickup",
                "service_name": "ClickUp",
                "aliases": ["클릭업", "clickup", "CLICKUP"],
                "category_tags": [
                    "project_management",
                    "task_tracking",
                    "documentation",
                ],
            },
        ]
    }

    assert detect_duplicate_tags(clean_df, catalog) == [
        {"tools": {"Jira", "ClickUp"}, "common_tags": {"project_management", "task_tracking"}}
    ]


def test_detect_duplicate_tags_case_4():
    clean_df = pd.DataFrame()
    catalog = {
        "tools": [
            {
                "tool_id": "figma",
                "service_name": "Figma",
                "aliases": ["피그마", "figma", "FIGMA"],
                "category_tags": ["design", "prototyping", "whiteboarding"],
            }
        ]
    }

    assert detect_duplicate_tags(clean_df, catalog) == []


def test_detect_duplicate_tags_case_5():
    clean_df = pd.DataFrame(
        [
            {"service_name": "Notion"},
            {"service_name": "Jira"},
            {"service_name": "ClickUp"},
        ]
    )

    assert detect_duplicate_tags(clean_df, {"tools": []}) == []