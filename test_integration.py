import pytest
import pandas as pd

"""
pipeline.py 함수에 대한 단위 테스트를 수행한다.
정상 1건, 경계 1건, 예외 1건을 테스트한다.
"""

from pipeline import adapt_duplicate_pairs_for_json, summarize_analysis_for_llm, run_pipeline_from_data
from quant_analysis import SeatLeakage

def test_adapt_duplicate_pairs_for_json_case_1():
    raw_pairs = [
        {"tools": {"Notion", "Jira"}, "categories": {"project_management"}},
        {"tools": {"Notion", "ClickUp"}, "categories": {"documentation", "project_management"}},
        {"tools": {"Jira", "ClickUp"}, "categories": {"project_management"}},
    ]

    result = adapt_duplicate_pairs_for_json(raw_pairs)
    assert sorted(result[0]["tools"]) == sorted(["Notion", "Jira"])
    assert sorted(result[0]["categories"]) == sorted(["project_management"])
    assert sorted(result[1]["tools"]) == sorted(["Notion", "ClickUp"])
    assert sorted(result[1]["categories"]) == sorted(["documentation", "project_management"])
    assert sorted(result[2]["tools"]) == sorted(["Jira", "ClickUp"])
    assert sorted(result[2]["categories"]) == sorted(["project_management"])

def test_adapt_duplicate_pairs_for_json_case_2():
    raw_pairs = []

    assert adapt_duplicate_pairs_for_json(raw_pairs) == []

def test_summarize_analysis_for_llm_case_1():
    clean_df = pd.DataFrame(
        {
            "billing_date": ["2026-10-05", "2026-10-06"],
            "service_name": ["Figma", "Slack"],
            "billing_cycle": ["월간", "연간"],
            "billing_amount_krw": [180000, 1478400],
            "monthly_cost_krw": [180000, 123200],
        }
    )
    warnings = []
    seat_leakage = [
        SeatLeakage(service_name="Figma", inactive_seats=8, wasted_spend=120000),
        SeatLeakage(service_name="Jira", inactive_seats=5, wasted_spend=50000)
    ]
    duplicate_pairs = [
        {"tools": ["Notion", "Jira"], "common_tags": ["project_management"]},
        {"tools": ["Notion", "ClickUp"], "common_tags": ["documentation", "project_management"]},
        {"tools": ["Jira", "ClickUp"], "common_tags": ["project_management"]},
    ]

    assert summarize_analysis_for_llm(clean_df, warnings, seat_leakage, duplicate_pairs) == {
        "valid_transaction_count": 2,
        "warning_count": 0,
        "total_monthly_cost_krw": 303200,
        "total_inactive_seats": 13,
        "total_wasted_spend_krw": 170000,
        "seat_leakage": [
        SeatLeakage(service_name="Figma", inactive_seats=8, wasted_spend=120000),
        SeatLeakage(service_name="Jira", inactive_seats=5, wasted_spend=50000)
    ],
        "duplicate_pairs": [
        {"tools": ["Notion", "Jira"], "common_tags": ["project_management"]},
        {"tools": ["Notion", "ClickUp"], "common_tags": ["documentation", "project_management"]},
        {"tools": ["Jira", "ClickUp"], "common_tags": ["project_management"]},
    ],
    }

def test_run_pipeline_from_data_case_1():
    raw_df = pd.DataFrame(
        {
            "tx_id": ["TX-001", "TX-002", "TX-003"],
            "billing_date": ["2026-11-01", "2026-11-02", "2026-11-03"],
            "service_name": ["Slack", "Notion", "Jira"],
            "department": ["개발팀", "기획팀", "개발팀"],
            "billing_cycle": ["월간", "월간", "연간"],
            "seat_count": ["20", "15", "10"],
            "active_users": ["12", "15", "5"],
            "billing_amount_krw": ["200,000원", "150000", "1200000"],
            "card_holder_pii": ["김철수(1234-5678)", "이영희", "박민수"],
        }
    )
    catalog = catalog = {
        "meta": {"version": "1.0", "description": "fixture catalog"},
        "tools": [
            {
                "tool_id": "T-01",
                "service_name": "Slack",
                "aliases": ["슬랙"],
                "category_tags": ["협업", "메신저"],
                "pricing_tiers": [{"tier": "Pro", "monthly_krw": 10000}],
            },
            {
                "tool_id": "T-02",
                "service_name": "Notion",
                "aliases": ["노션"],
                "category_tags": ["협업", "문서", "프로젝트관리"],
                "pricing_tiers": [{"tier": "Plus", "monthly_krw": 10000}],
            },
            {
                "tool_id": "T-03",
                "service_name": "Jira",
                "aliases": ["지라"],
                "category_tags": ["협업", "프로젝트관리", "이슈트래킹"],
                "pricing_tiers": [{"tier": "Standard", "monthly_krw": 10000}],
            },
        ],
    }
    initial_state = None

    result = run_pipeline_from_data(raw_df, catalog, initial_state)
    assert result["clean_data"] == [
            {
                'tx_id': 'TX-001',
                'billing_date': '2026-11-01',
                'service_name': 'Slack',
                'department': '개발팀',
                'billing_cycle': '월간',
                'seat_count': 20,
                'active_users': 12,
                'billing_amount_krw': 200000,
                'card_holder_pii': '[REDACTED]',
                'monthly_cost_krw': 200000,
            },
            {
                'tx_id': 'TX-002',
                'billing_date': '2026-11-02',
                'service_name': 'Notion',
                'department': '기획팀',
                'billing_cycle': '월간',
                'seat_count': 15,
                'active_users': 15,
                'billing_amount_krw': 150000,
                'card_holder_pii': '[REDACTED]',
                'monthly_cost_krw': 150000,
            },
            {
                'tx_id': 'TX-003',
                'billing_date': '2026-11-03',
                'service_name': 'Jira',
                'department': '개발팀',
                'billing_cycle': '연간',
                'seat_count': 10,
                'active_users': 5,
                'billing_amount_krw': 1200000,
                'card_holder_pii': '[REDACTED]',
                'monthly_cost_krw': 100000,
            },
        ]
    assert result["warnings"] == []
    assert result["summary"] == {
            'valid_transaction_count': 3,
            'warning_count': 0,
            'total_monthly_cost_krw': 450000,
            'total_inactive_seats': 13,
            'total_wasted_spend_krw': 130000,
            'seat_leakage': [
                {
                    'service_name': 'Slack',
                    'inactive_seats': 8,
                    'wasted_spend': 80000,
                },
                {
                    'service_name': 'Notion',
                    'inactive_seats': 0,
                    'wasted_spend': 0,
                },
                {
                    'service_name': 'Jira',
                    'inactive_seats': 5,
                    'wasted_spend': 50000,
                },
            ],
            'duplicate_pairs': [
                {
                    'tools': ['Notion','Slack'],
                    'categories': ['협업'],
                },
                {
                    'tools': ['Jira','Slack'],
                    'categories': ['협업'],
                },
                {
                    'tools': ['Jira','Notion'],
                    'categories': ['프로젝트관리','협업'],
                },
            ],
        }

def test_run_pipeline_from_data_case_2():
    raw_df = pd.DataFrame(
       columns=[
            "tx_id",
            "billing_date",
            "service_name",
            "department",
            "billing_cycle",
            "seat_count",
            "active_users",
            "billing_amount_krw",
            "card_holder_pii",
        ],
        dtype=str,
    )
    catalog = catalog = {
        "meta": {"version": "1.0", "description": "fixture catalog"},
        "tools": [
            {
                "tool_id": "T-01",
                "service_name": "Slack",
                "aliases": ["슬랙"],
                "category_tags": ["협업", "메신저"],
                "pricing_tiers": [{"tier": "Pro", "monthly_krw": 10000}],
            },
            {
                "tool_id": "T-02",
                "service_name": "Notion",
                "aliases": ["노션"],
                "category_tags": ["협업", "문서", "프로젝트관리"],
                "pricing_tiers": [{"tier": "Plus", "monthly_krw": 10000}],
            },
            {
                "tool_id": "T-03",
                "service_name": "Jira",
                "aliases": ["지라"],
                "category_tags": ["협업", "프로젝트관리", "이슈트래킹"],
                "pricing_tiers": [{"tier": "Standard", "monthly_krw": 10000}],
            },
        ],
    }
    initial_state = None

    assert run_pipeline_from_data(raw_df, catalog, initial_state) == {
        "meta": {
                    "use_mock": True,
                    "process_codes": ["P1", "P3", "P5"],
                },
        "clean_data": [],
        "warnings": [],
        "summary": {
            'valid_transaction_count': 0,
            'warning_count': 0,
            'total_monthly_cost_krw': 0,
            'total_inactive_seats': 0,
            'total_wasted_spend_krw': 0,
            'seat_leakage': [],
            'duplicate_pairs': [],
        },
        "llm_questions": {
            'round_number': 1,
            'questions': [
                {
                    'question': '[MOCK] 현재 이 업무에 몇 명이 함께 참여하나요?',
                    'slot_id': '[MOCK] C-01',
                    'category': '[MOCK] 팀 규모',
                    'priority': 'required',
                },
            ],
            'can_finish_now': False,
        },
        "llm_report": {
            'summary': '[MOCK] 최종 진단 요약',
            'candidate_sets': [
                {
                    'set_id': 1,
                    'title': '[MOCK] 균형형',
                    'fit_percent': 94,
                    'monthly_cost_krw': 0,
                    'monthly_saving_krw': 0,
                    'matching_reasons': [],
                    'tradeoffs': [],
                    'recommendations': [],
                    'approval_summary': '[MOCK] 대표 결재용 요약',
                },
            ],
        }
    }