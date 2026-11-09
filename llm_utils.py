"""Utilities for constructing structured prompts for the recommendation workflow."""

from __future__ import annotations

import json
from typing import Any, Literal, TypedDict


PromptPurpose = Literal["question", "context", "report"]


class SlotValue(TypedDict):
    value: Any
    source: Literal["user", "csv", "analysis", "llm"]
    evidence: str
    round_number: int


class QuestionItem(TypedDict):
    question: str
    slot_id: str
    category: str
    priority: Literal["required", "conditional", "optional"]


class QuestionBatch(TypedDict):
    round_number: int
    questions: list[QuestionItem]
    can_finish_now: bool


class ConversationState(TypedDict, total=False):
    session_id: str
    round_number: int
    process_codes: list[str]
    process_candidates: list[dict[str, Any]]
    filled_slots: dict[str, SlotValue]
    missing_slots: list[str]
    skipped_slots: list[str]
    question_history: list[dict[str, Any]]
    answer_history: list[dict[str, Any]]
    workflow_summary: str
    bottleneck_memo: str
    culture_notes: str
    must_keep: list[str]
    can_finish_now: bool
    user_requested_finish: bool


class CompanyContext(TypedDict):
    process_codes: list[str]
    summary: str
    filled_slots: dict[str, Any]
    missing_slots: list[str]
    workflow_summary: str
    bottleneck_memo: str
    culture_notes: str
    must_keep: list[str]


class FinalReport(TypedDict):
    summary: str
    candidate_sets: list[dict[str, Any]]


_PURPOSES = {"question", "context", "report"}

_COMMON_INSTRUCTIONS = """\
당신은 기업의 업무 프로세스와 SaaS 도구를 분석해 질문, 기업 맥락, 추천 리포트를
구조화하는 분석 보조자다. 이 프로젝트의 목적은 사용자의 직접 답변과 Python에서
계산한 분석 결과를 근거로, 업무에 맞는 도구 도입·유지·교체 판단을 돕는 것이다.

입력 데이터에 없는 사실, 수치, 기능, 의도, 비용을 추측하지 마라. 사용자 입력이나
분석 결과에 근거하지 않은 값을 확정하지 마라. 확실하지 않은 내용은 누락하거나
확인 필요 사항으로 남겨라. 원본 CSV 전체를 요구하거나 프롬프트에 포함하지 말고,
개인정보와 불필요한 거래 상세를 LLM에 전달하지 마라. CSV는 Python에서 집계한
요약 데이터만 사용한다.

아래의 CURRENT_STATE는 원본 대화가 아니라 애플리케이션이 현재까지 정리한 상태다.
CURRENT_EXTRA_DATA도 Python이 이미 계산한 추가 분석 결과다. 두 영역을 원본 대화의
발화나 새로운 사실로 혼동하지 마라. 모든 응답은 JSON 객체 하나만 출력하라. JSON
밖의 설명·마크다운·코드 펜스를 출력하지 마라.
"""

_QUESTION_INSTRUCTIONS = """\
작업 목적: 다음 라운드에서 사용자에게 물을 질문 묶음을 생성한다.
- 질문은 3~5개 생성한다. 단, 질문할 수 있는 missing_slots가 3개 미만이면
  존재하는 슬롯만 질문하며, 없는 슬롯을 억지로 만들지 마라.
- missing_slots에 있는 슬롯만 질문 대상으로 삼는다.
- filled_slots와 skipped_slots에 있는 슬롯은 다시 묻지 않는다.
- slot_schema가 제공되면 슬롯 정의, category(슬롯 이름), priority를 따른다.
- 각 slot_id는 제공된 slot_schema에 실제로 존재하는 값만 사용한다.
- 정확도나 충족률은 계산하지 않는다. 정확도 계산은 이후 Python 코드가 담당한다.

출력 형식:
{
  "round_number": 1,
  "questions": [
    {
      "question": "질문 내용",
      "slot_id": "C-01",
      "category": "팀 규모",
      "priority": "required"
    }
  ],
  "can_finish_now": false
}
"""

_CONTEXT_INSTRUCTIONS = """\
작업 목적: 현재까지의 정리된 데이터와 Python 분석 요약으로 기업 맥락을 분석한다.
- process_codes는 여러 개일 수 있다.
- CSV의 서비스 목록만으로 프로세스를 확정하지 않는다.
- CSV와 정량 분석 결과는 초기 단서로만 사용한다.
- 사용자의 직접 답변을 가장 우선적인 근거로 사용한다.
- 사용자가 답하지 않은 값은 filled_slots에 넣지 않는다.
- 추정값은 확정값처럼 저장하지 않는다.
- 중복 의심 도구를 즉시 해지 대상으로 단정하지 않는다.
- workflow_summary, bottleneck_memo, culture_notes는 사용자 답변에 근거해 작성한다.
- must_keep에는 사용자가 반드시 유지해야 한다고 밝힌 도구만 넣는다.
- 아직 필요한 슬롯은 missing_slots에 남긴다.

출력 형식:
{
  "process_codes": ["P1", "P3"],
  "summary": "기업 상황 요약",
  "filled_slots": {},
  "missing_slots": [],
  "workflow_summary": "업무 흐름",
  "bottleneck_memo": "병목과 반복 작업",
  "culture_notes": "조직 성향과 도입 저항",
  "must_keep": ["Slack"]
}
"""

_REPORT_INSTRUCTIONS = """\
작업 목적: 현재까지의 정리된 상태와 분석 결과를 사용해 최종 추천 리포트를 구성한다.
- 후보 세트는 최대 3개까지 생성한다.
- candidate_tools와 pricing_simulation에 있는 도구만 사용한다.
- 비용과 절감액은 Python 계산값을 그대로 사용하며, 새로 계산하거나 변경하지 않는다.
- must_keep 도구는 해지·교체 대상으로 제안하지 않는다.
- contract_warnings가 있는 도구는 해당 주의 문구를 포함한다.
- 각 후보 세트에 장점, matching_reasons, tradeoffs, recommendations를 포함한다.
- 근거가 없는 수치와 기능을 만들어내지 않는다.

출력 형식:
{
  "summary": "최종 진단 요약",
  "candidate_sets": [
    {
      "set_id": 1,
      "title": "균형형",
      "fit_percent": 94,
      "monthly_cost_krw": 0,
      "monthly_saving_krw": 0,
      "matching_reasons": [],
      "tradeoffs": [],
      "recommendations": [],
      "approval_summary": "대표 결재용 요약"
    }
  ]
}
"""


def _serialize_json(value: Any, name: str) -> str:
    """Serialize a prompt input and expose unsupported values as a clear error."""
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    except (TypeError, ValueError) as error:
        raise TypeError(
            f"{name} must contain only JSON-serializable values"
        ) from error


def build_prompt_template(
    purpose: PromptPurpose,
    state: ConversationState,
    extra_data: dict | None = None,
) -> str:
    """Build a purpose-specific prompt with serialized workflow state and analysis."""
    if not isinstance(purpose, str) or purpose not in _PURPOSES:
        raise ValueError(
            f"purpose must be one of 'question', 'context', or 'report'; got {purpose!r}"
        )
    if not isinstance(state, dict):
        raise TypeError("state must be a ConversationState-compatible dict")
    if extra_data is not None and not isinstance(extra_data, dict):
        raise TypeError("extra_data must be a dict or None")
    if purpose in {"context", "report"} and not state and extra_data is None:
        raise ValueError(
            f"purpose={purpose!r} requires state or extra_data"
        )

    serialized_state = _serialize_json(state, "state")
    serialized_extra_data = _serialize_json(
        {} if extra_data is None else extra_data,
        "extra_data",
    )
    missing_fields = [
        field
        for field in ("process_codes", "filled_slots", "missing_slots")
        if field not in state
    ]
    state_note = ""
    if purpose == "question" and missing_fields:
        state_note = (
            "\n주의: 현재 상태에 다음 필드가 없어 질문 생성에 사용할 수 없다: "
            f"{', '.join(missing_fields)}. 없는 값은 추측하지 마라.\n"
        )

    instructions = {
        "question": _QUESTION_INSTRUCTIONS,
        "context": _CONTEXT_INSTRUCTIONS,
        "report": _REPORT_INSTRUCTIONS,
    }[purpose]
    return (
        f"PROMPT_PURPOSE={purpose}\n\n"
        f"{_COMMON_INSTRUCTIONS}\n"
        f"{state_note}\n"
        "CURRENT_STATE (정리된 상태 JSON):\n"
        f"{serialized_state}\n\n"
        "CURRENT_EXTRA_DATA (Python 계산 요약 JSON):\n"
        f"{serialized_extra_data}\n\n"
        f"{instructions}"
    )