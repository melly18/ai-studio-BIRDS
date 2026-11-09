import pytest
import json

from llm_utils import build_prompt_template
from llm_utils import parse_and_validate_json, QuestionBatch, CompanyContext, SlotValue


def test_build_prompt_template_normal():
    state = {  "round_number": 1,
            "process_codes": ["P3"],
            "filled_slots": {
                "C-01": {
                    "value": "6~20명",
                    "source": "user",
                    "evidence": "팀은 12명이라고 답변함",
                    "round_number": 1
                }
            }, 
            "missing_slots": ["C-02", "C-03", "P3-S01"],
            "skipped_slots": [],
            "question_history": [],
            "answer_history": []
        }
    extra_data = {"summary": "Some summary data"}

    # Test with purpose 'question'
    prompt = build_prompt_template("question", state, extra_data)
    assert isinstance(prompt, str)
    assert "PROMPT_PURPOSE=question" in prompt
    assert "출력 형식:" in prompt
    assert "missing_slots" in prompt
    assert "filled_slots" in prompt
    assert "question_history" not in prompt
    assert "answer_history" not in prompt

    # Test with purpose 'context'
    prompt = build_prompt_template("context", state, extra_data)
    assert isinstance(prompt, str)
    assert "PROMPT_PURPOSE=context" in prompt
    assert "출력 형식:" in prompt
    assert "question_history" not in prompt
    assert "answer_history" not in prompt

    # Test with purpose 'report'
    prompt = build_prompt_template("report", state, extra_data)
    assert isinstance(prompt, str)
    assert "PROMPT_PURPOSE=report" in prompt
    assert "출력 형식:" in prompt
    assert "question_history" not in prompt
    assert "answer_history" not in prompt

def test_build_prompt_template_invalid_purpose():
    state = {"process_codes": [], "filled_slots": {}, "missing_slots": []}
    extra_data = {"summary": "Some summary data"}

    with pytest.raises(ValueError):
        build_prompt_template("analysis", state, extra_data)

def test_build_prompt_template_none_input():
    state = {}
    extra_data = None

    with pytest.raises(ValueError):
        build_prompt_template("context", state, extra_data)

def test_build_prompt_template_edge():
    state = {}
    extra_data = None

    prompt = build_prompt_template("question", state, extra_data)
    assert isinstance(prompt, str)
    assert "PROMPT_PURPOSE=question" in prompt
    assert "출력 형식:" in prompt
    assert "주의: 현재 상태에 다음 필드가 없어 질문 생성에 사용할 수 없다" in prompt

# Test JSON parsing and validation

def test_parse_and_validate_json_normal():
    raw_response = json.dumps({
                "round_number": 1,
                "questions": [
                    {
                        "question": "[MOCK] 현재 이 업무에 몇 명이 함께 참여하나요?",
                        "slot_id": "[MOCK] C-01",
                        "category": "[MOCK] 팀 규모",
                        "priority": "required",
                    }
                ],
                "can_finish_now": False,
            })
    schema = QuestionBatch
    result = parse_and_validate_json(raw_response, schema)
    assert result == {
                "round_number": 1,
                "questions": [
                    {
                        "question": "[MOCK] 현재 이 업무에 몇 명이 함께 참여하나요?",
                        "slot_id": "[MOCK] C-01",
                        "category": "[MOCK] 팀 규모",
                        "priority": "required",
                    }
                ],
                "can_finish_now": False,
            }


def test_parse_and_validate_json_wrong_schema():
    raw_response = json.dumps({
                    "round_number": 1,
                    "questions": [
                        {
                            "question": "[MOCK] 현재 이 업무에 몇 명이 함께 참여하나요?",
                            "slot_id": "[MOCK] C-01",
                            "category": "[MOCK] 팀 규모",
                            "priority": "required",
                        }
                    ],
                    "can_finish_now": False,
                })
    schema = CompanyContext

    with pytest.raises(ValueError):
        result = parse_and_validate_json(raw_response, schema)

def test_parse_and_validate_json_invalid_dto():
    raw_response = json.dumps({
                    "round_number": 1,
                    "questions": [
                        {
                            "question": "[MOCK] 현재 이 업무에 몇 명이 함께 참여하나요?",
                            "slot_id": "[MOCK] C-01",
                            "category": "[MOCK] 팀 규모",
                            "priority": "required",
                        }
                    ],
                    "can_finish_now": False,
                })
    schema = SlotValue

    with pytest.raises(TypeError):
        result = parse_and_validate_json(raw_response, schema)

def test_parse_and_validate_json_codefence():
    raw_response = json.dumps({
                    "round_number": 1,
                    "questions": [
                        {
                            "question": "[MOCK] 현재 이 업무에 몇 명이 함께 참여하나요?",
                            "slot_id": "[MOCK] C-01",
                            "category": "[MOCK] 팀 규모",
                            "priority": "required",
                        }
                    ],
                    "can_finish_now": False,
                })
    raw_response_with_codefence = f"```\n{raw_response}\n```"
    schema = QuestionBatch
    result = parse_and_validate_json(raw_response_with_codefence, schema)
    assert result == {
                    "round_number": 1,
                    "questions": [
                        {
                            "question": "[MOCK] 현재 이 업무에 몇 명이 함께 참여하나요?",
                            "slot_id": "[MOCK] C-01",
                            "category": "[MOCK] 팀 규모",
                            "priority": "required",
                        }
                    ],
                    "can_finish_now": False,
                }