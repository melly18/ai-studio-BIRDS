"""추천 워크플로를 위한 구조화된 프롬프트 생성 유틸리티."""

import json
import re
from typing import Any, Literal, TypedDict, TypeVar, cast, get_args, get_origin, get_type_hints, is_typeddict


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


DTO = TypeVar("DTO")
_JSON_SCHEMAS = (QuestionBatch, CompanyContext, FinalReport)


def _validate_typed_dict_keys(value: Any, schema: Any, path: str) -> None:
    if is_typeddict(schema):
        if not isinstance(value, dict):
            raise TypeError(f"{path} must be an object")

        required_keys = schema.__required_keys__
        allowed_keys = schema.__annotations__
        missing_keys = required_keys - value.keys()
        extra_keys = value.keys() - allowed_keys.keys()
        if missing_keys:
            raise ValueError(
                f"{path} is missing required keys: {sorted(missing_keys)!r}"
            )
        if extra_keys:
            raise ValueError(
                f"{path} contains unsupported keys: {sorted(extra_keys)!r}"
            )

        annotations = get_type_hints(schema)
        for key, annotation in annotations.items():
            if key in value:
                _validate_typed_dict_keys(value[key], annotation, f"{path}.{key}")
        return

    origin = get_origin(schema)
    args = get_args(schema)
    if origin is list and args:
        if not isinstance(value, list):
            return
        for index, item in enumerate(value):
            _validate_typed_dict_keys(item, args[0], f"{path}[{index}]")
    elif origin is dict and len(args) == 2:
        if not isinstance(value, dict):
            return
        for key, item in value.items():
            _validate_typed_dict_keys(item, args[1], f"{path}[{key!r}]")


def parse_and_validate_json(raw_response: str, schema: type[DTO]) -> DTO:
    """LLM 응답에서 JSON 객체를 추출하고 지정된 DTO의 키 구조를 검증한다.

    Args:
        raw_response: 일반 JSON 또는 마크다운 코드 펜스로 감싼 JSON 문자열.
        schema: 허용된 출력 DTO 타입인 ``QuestionBatch``, ``CompanyContext``
            또는 ``FinalReport``.

    Returns:
        지정된 DTO 구조를 따르는 파싱된 JSON 객체.

    Raises:
        ValueError: 입력 문자열이 아니거나 JSON이 유효하지 않거나, 필수 키가
            없거나 허용되지 않은 키가 포함된 경우.
        TypeError: 스키마가 허용된 DTO 타입이 아니거나 JSON 최상위 값이 객체가
            아닌 경우.
    """
    if not isinstance(raw_response, str):
        raise ValueError("raw_response must be a string")
    if not isinstance(schema, type) or schema not in _JSON_SCHEMAS:
        raise TypeError(
            "schema must be QuestionBatch, CompanyContext, or FinalReport"
        )

    json_text = re.sub(
        r"^\s*```(?:json)?\s*|\s*```\s*$",
        "",
        raw_response.strip(),
        flags=re.IGNORECASE,
    )
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as error:
        raise ValueError("raw_response does not contain valid JSON") from error

    if not isinstance(parsed, dict):
        raise TypeError("JSON response must be an object")

    _validate_typed_dict_keys(parsed, schema, "response")
    return cast(DTO, parsed)


_PURPOSES = {"question", "context", "report"}

_COMMON_INSTRUCTIONS = """\
당신은 기업의 업무 프로세스와 SaaS 도구를 분석해 질문, 기업 맥락, 추천 리포트를
구조화하는 분석 보조자다. 이 프로젝트의 목적은 사용자의 직접 답변과 Python에서
계산한 분석 결과를 근거로, 업무에 맞는 도구 도입·유지·교체 판단을 돕는 것이다.

입력 데이터에 없는 사실, 수치, 기능, 의도, 비용을 추측하지 마라. 사용자 입력이나
분석 결과에 근거하지 않은 값을 확정하지 마라. 확실하지 않은 내용은 누락하거나
확인 필요 사항으로 남겨라. CSV는 Python에서 집계한 요약 데이터만 사용한다.

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
- candidate_tools와 pricing_simulation에 있는 툴만 사용한다.
- 비용과 절감액은 Python 계산값을 그대로 사용하며, 새로 계산하거나 변경하지 않는다.
- must_keep 도구는 해지·교체 대상으로 제안하지 않는다.
- contract_warnings가 있는 툴은 해당 주의 문구를 포함한다.
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
    """프롬프트 입력을 JSON으로 직렬화하고 지원하지 않는 값을 명확히 보고한다.

    Args:
        value: JSON으로 변환할 상태 또는 추가 분석 데이터.
        name: 오류 메시지에 표시할 입력 이름.

    Returns:
        들여쓰기와 키 정렬이 적용된 JSON 문자열.

    Raises:
        TypeError: 값에 JSON으로 직렬화할 수 없는 객체가 포함된 경우.
    """
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=None)
    except (TypeError, ValueError) as error:
        raise TypeError(
            f"{name} must contain only JSON-serializable values"
        ) from error


def build_prompt_template(
    purpose: PromptPurpose,
    state: ConversationState,
    extra_data: dict | None = None,
) -> str:
    """목적별 작업 지침과 현재 데이터를 포함한 LLM 프롬프트를 생성한다.

    Args:
        purpose: 생성 목적이다. ``question``, ``context``, ``report`` 중 하나여야
            한다.
        state: 현재 대화에서 정리된 상태다. 원본 대화가 아니라 슬롯, 이력,
            프로세스 등의 구조화된 데이터를 담는다. ``question_history``와
            ``answer_history``는 프롬프트에 포함하지 않는다.
        extra_data: Python에서 미리 계산한 분석 요약 데이터다. ``None``이면
            빈 객체로 처리한다.

    Returns:
        현재 상태와 추가 분석 데이터, 목적별 JSON 출력 형식을 포함한 프롬프트
        문자열.

    Raises:
        ValueError: ``purpose``가 허용된 값이 아니거나, ``context`` 또는
            ``report`` 목적에서 상태와 추가 데이터가 모두 비어 있는 경우.
        TypeError: ``state`` 또는 ``extra_data``의 타입이 올바르지 않거나,
            입력 데이터가 JSON으로 직렬화되지 않는 경우.
    """
    if not isinstance(purpose, str) or purpose not in _PURPOSES:
        raise ValueError(
            f"purpose must be one of 'question', 'context', or 'report'; got {purpose!r}"
        )
    if not isinstance(state, dict):
        raise TypeError("state must be a ConversationState-compatible dict")
    if extra_data is not None and not isinstance(extra_data, dict):
        raise TypeError("extra_data must be a dict or None")
    prompt_state = {
        key: value
        for key, value in state.items()
        if key not in {"question_history", "answer_history"}
    }
    if purpose in {"context", "report"} and not prompt_state and extra_data is None:
        raise ValueError(
            f"purpose={purpose!r} requires state or extra_data"
        )

    serialized_state = _serialize_json(prompt_state, "state")
    serialized_extra_data = _serialize_json(
        {} if extra_data is None else extra_data,
        "extra_data",
    )
    missing_fields = [
        field
        for field in ("process_codes", "filled_slots", "missing_slots")
        if field not in prompt_state
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

USE_MOCK = True

def _call_llm_request_mock(prompt: str) -> str:
    if "PROMPT_PURPOSE=question" in prompt:
        return json.dumps(
            {
                "round_number": 1,
                "questions": [
                    {
                        "question": "[MOCK] 현재 이 업무에 몇 명이 함께 참여하나요?",
                        "slot_id": "[MOCK] C-01",
                        "category": "[MOCK] 팀 규모",
                        "priority": "[MOCK] required",
                    }
                ],
                "can_finish_now": False,
            },
            ensure_ascii=False,
        )
    if "PROMPT_PURPOSE=context" in prompt:
        return json.dumps(
            {
                 "process_code": "[MOCK] P3",
                "summary": "[MOCK] 문서와 프로젝트 관리 업무의 현재 상태를 정리했습니다.",
                "filled_slots": {},
                "missing_slots": ["[MOCK] C-01", "[MOCK] C-02", "[MOCK] C-03", "[MOCK] C-04"],
                "workflow_summary": "[MOCK] 문서와 프로젝트 태스크를 함께 관리합니다.",
                "bottleneck_memo": "[MOCK] 병목 정보가 아직 충분하지 않습니다.",
                "culture_notes": "",
                "must_keep": ["[MOCK] Notion"],
            },
            ensure_ascii=False,
        )
    if "PROMPT_PURPOSE=report" in prompt:
        return json.dumps(
            {
                "summary": "[MOCK] 최종 진단 요약",
                "candidate_sets": [
                    {
                        "set_id": 1,
                        "title": "[MOCK] 균형형",
                        "fit_percent": 94,
                        "monthly_cost_krw": 0,
                        "monthly_saving_krw": 0,
                        "matching_reasons": [],
                        "tradeoffs": [],
                        "recommendations": [],
                        "approval_summary": "[MOCK] 대표 결재용 요약",
                    }
                ],
            },
            ensure_ascii=False,
        )

def call_llm_request(prompt: str) -> str:
    """
    요청된 프롬프트를 LLM에 전달하고 응답을 반환한다. 현재는 모의 응답을 반환하도록 설정되어 있다.
    Args:
        prompt (str): LLM에 전달할 프롬프트 문자열.
    Returns:
        str: LLM의 응답 문자열.
    Raises:
        AssertionError: prompt가 문자열이 아닌 경우.
        AssertionError: prompt에 '출력 형식:'이 포함되어 있지 않은 경우.
    """
    assert isinstance(prompt, str), f"prompt must be a string, not {type(prompt)}"
    assert "출력 형식:" in prompt, f"prompt must contain '출력 형식:' to indicate expected JSON output"
    if USE_MOCK:
        return _call_llm_request_mock(prompt)
    return "Not Ready for real LLM request"  #13주차 구현 예정