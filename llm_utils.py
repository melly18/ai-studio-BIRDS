import json
import re
from typing import Any, Literal, TypedDict, TypeVar, cast, get_args, get_origin, get_type_hints, is_typeddict

from prompts.template import(
    _PURPOSES,
    _COMMON_INSTRUCTIONS,
    _QUESTION_INSTRUCTIONS,
    _CONTEXT_INSTRUCTIONS,
    _REPORT_INSTRUCTIONS,
)

from docs.schema import(
    SlotValue,
    QuestionItem,
    QuestionBatch,
    ConversationState,
    CompanyContext,
    FinalReport,
)

DTO = TypeVar("DTO")
_JSON_SCHEMAS = (QuestionBatch, CompanyContext, FinalReport)

PromptPurpose = Literal["question", "context", "report"]


def _validate_typed_dict_keys(value: Any, schema: Any, path: str) -> None:
    """
    지정된 TypedDict 스키마에 따라 JSON 객체의 키 구조를 재귀적으로 검증한다.
    Args:
        value: 검증할 JSON 객체.
        schema: 허용된 TypedDict 스키마.
        path: 검증할 값의 경로.
    Returns:
        None
    Raises:
        ValueError: 필수 키가 없거나 허용되지 않은 키가 포함된 경우.
        TypeError: 스키마가 허용된 TypedDict 타입이 아니거나 JSON 최상위 값이 객체가
            아닌 경우.
    """
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
        # 재귀적으로 각 키의 값에 대해 타입 검증 수행
        for key, annotation in annotations.items():
            if key in value:
                _validate_typed_dict_keys(value[key], annotation, f"{path}.{key}")
        return

    origin = get_origin(schema)
    args = get_args(schema)
    if origin is Literal:
        # 허용된 Literal 값 중 하나인지 확인
        if not any(
            type(value) is type(expected) and value == expected
            for expected in args
        ):
            raise ValueError(
                f"{path} must be one of {args!r}; got {value!r}"
            )
    elif origin is list and args:
        if not isinstance(value, list):
            raise TypeError(f"{path} must be a list")
        # 재귀적으로 list 내의 각 항목에 대해 타입 검증 수행
        for index, item in enumerate(value):
            _validate_typed_dict_keys(item, args[0], f"{path}[{index}]")
    elif origin is dict and len(args) == 2:
        if not isinstance(value, dict):
            raise TypeError(f"{path} must be an object")
        # 재귀적으로 dict 내의 각 항목에 대해 타입 검증 수행
        for key, item in value.items():
            _validate_typed_dict_keys(item, args[1], f"{path}[{key!r}]")
    else:
        if isinstance(schema, type) and schema is not Any:
            if not isinstance(value, schema):
                raise TypeError(f"{path} must be of type {schema.__name__}")

def parse_and_validate_json(raw_response: str, schema: type[DTO]) -> DTO:
    """LLM 응답에서 JSON 객체를 추출하고 지정된 DTO의 키 구조를 검증한다.

    Args:
        raw_response: 일반 JSON 또는 마크다운 코드 펜스로 감싼 JSON 문자열.
        schema: 허용된 출력 DTO 타입인 ``QuestionBatch``, ``CompanyContext``
            또는 ``FinalReport``.

    Returns:
        지정된 DTO 구조를 따르는 파싱된 JSON 객체.

    Raises:
        ValueError: raw_response가 유효한 JSON이 아니거나, 지정된 DTO 스키마에
            맞지 않는 경우.
        TypeError: schema가 허용된 DTO 타입이 아니거나, raw_response가 문자열이
            아닌 경우.
    """
    if not isinstance(raw_response, str):
        raise ValueError("raw_response must be a string")
    if not isinstance(schema, type) or schema not in _JSON_SCHEMAS:
        schema_names = ", ".join([s.__name__ for s in _JSON_SCHEMAS])
        raise TypeError(f"schema must be one of: {schema_names}")

    # JSON 코드 펜스 방어
    match = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        raw_response,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        json_text = match.group(1).strip()
    else:
        json_text = raw_response.strip()
    
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as error:
        raise ValueError("raw_response does not contain valid JSON") from error

    if not isinstance(parsed, dict):
        raise TypeError("JSON response must be an object")

    # 파싱된 JSON을 지정된 DTO 스키마에 따라 검증
    _validate_typed_dict_keys(parsed, schema, "response")
    return cast(DTO, parsed)


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
    # question_history와 answer_history를 제외한 상태만 프롬프트에 포함
    prompt_state = {
        key: value
        for key, value in state.items()
        if key not in {"question_history", "answer_history"}
    }
    # context 또는 report 목적에서 상태와 추가 데이터가 모두 비어 있는 경우 오류 발생
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
    """
    모의 LLM 응답을 생성한다. 실제 LLM 호출은 아직 구현되지 않았다.
    Args:
        prompt (str): LLM에 전달할 프롬프트 문자열.
    Returns:
        str: LLM의 모의 응답 문자열.
    """
    if "PROMPT_PURPOSE=question" in prompt:
        return json.dumps(
            {
                "round_number": 1,
                "questions": [
                    {
                        "question": "[MOCK] 현재 이 업무에 몇 명이 함께 참여하나요?",
                        "slot_id": "[MOCK] C-01",
                        "category": "[MOCK] 팀 규모",
                        "priority": "required",      #파싱 함수 로직을 위한 mock 제거
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