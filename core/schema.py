from typing import Any, Literal, TypedDict

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