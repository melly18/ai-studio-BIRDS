"""BIRDS 11주차 Streamlit UI 전용 백엔드 래퍼(Facade) 모듈.

UI(app.py)와 데이터 가공 로직을 철저히 분리하기 위해,
파일 로딩, 정제/마스킹 파이프라인 실행, 사이드바 필터링, KPI 산출,
차트용 데이터 집계 함수 제공.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, IO
import pandas as pd

import core.data_processing as dp
import core.quant_analysis as qa
import core.llm_utils as llm

# 실행 위치(cwd)와 무관하게 data 폴더의 카탈로그를 사용
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
DEFAULT_CATALOG_PATH = str(DATA_DIR / "saas_catalog_30_sample.json")

# 정제 스키마(data_processing.CLEAN_OUTPUT_COLUMNS) 기준 컬럼명
COST_COL = "monthly_cost_krw"
SERVICE_COL = "service_name"


def load_csv_with_encoding(uploaded_file: IO[bytes]) -> tuple[pd.DataFrame, str]:
    """업로드된 CSV 파일 객체를 읽어 (DataFrame, 실제 사용된 인코딩)을 반환.

    UTF-8(BOM 포함)로 먼저 읽고, 실패하면 cp949로 재시도한다.

    Args:
        uploaded_file: st.file_uploader가 반환한 UploadedFile 객체.

    Returns:
        (로드된 원본 pandas DataFrame, "utf-8" 또는 "cp949").

    Raises:
        ValueError: 파일이 비어 있거나 CSV 파싱에 실패한 경우.
    """
    # 10주차 load_billing_csv와 동일하게 모든 값을 문자열로 읽음
    read_kwargs = {"dtype": str, "keep_default_na": False}
    try:
        try:
            return pd.read_csv(uploaded_file, encoding="utf-8", **read_kwargs), "utf-8"
        except UnicodeDecodeError:
            uploaded_file.seek(0)  # 파일 포인터를 처음으로 되돌린 뒤 재시도
            return pd.read_csv(uploaded_file, encoding="cp949", **read_kwargs), "cp949"
    except (
        UnicodeDecodeError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
    ) as exc:
        raise ValueError(f"CSV 파일을 읽을 수 없습니다: {exc}") from exc


def load_csv_with_fallback(uploaded_file: IO[bytes]) -> pd.DataFrame:
    """업로드된 CSV 파일 객체를 읽어 DataFrame으로 반환 (cp949 재시도 포함).

    하위 호환용 래퍼. 인코딩 정보가 필요하면 load_csv_with_encoding()을 사용한다.

    Raises:
        ValueError: 파일이 비어 있거나 CSV 파싱에 실패한 경우.
    """
    return load_csv_with_encoding(uploaded_file)[0]


# 업로드 전 안내용 필수 열 설명·예시 (열 목록 자체는 dp.CLEAN_REQUIRED_COLUMNS가 단일 기준)
# 예시 PII는 반드시 가상 값만 사용 (배포 보안 3계명)
_REQUIRED_COLUMN_GUIDE: dict[str, tuple[str, str]] = {
    "tx_id": ("결제 거래 ID", "TX-0001"),
    "billing_date": ("결제일 (YYYY-MM-DD)", "2026-10-01"),
    "service_name": ("SaaS 서비스명", "Slack"),
    "department": ("사용 부서", "마케팅"),
    "billing_cycle": ("결제 주기 (월간/연간)", "월간"),
    "seat_count": ("구매 좌석 수", "10"),
    "active_users": ("실제 활성 사용자 수", "7"),
    "billing_amount_krw": ("결제 금액 (원)", "385000"),
    "card_holder_pii": (
        "카드 소유자 정보 (업로드 후 자동 마스킹)",
        "홍길동 / hong@example.com / 0000-0000-0000-0000",
    ),
}


def get_required_columns_guide() -> pd.DataFrame:
    """업로드 전 화면에 표시할 필수 열 안내 표(열 이름/설명/예시) 반환."""
    rows = [
        {
            "열 이름": col,
            "설명": _REQUIRED_COLUMN_GUIDE.get(col, ("", ""))[0],
            "예시": _REQUIRED_COLUMN_GUIDE.get(col, ("", ""))[1],
        }
        for col in dp.CLEAN_REQUIRED_COLUMNS
    ]
    return pd.DataFrame(rows, columns=["열 이름", "설명", "예시"])


def get_template_csv_bytes() -> bytes:
    """필수 열 헤더 + 가상 예시 1행으로 구성된 템플릿 CSV 바이트 반환.

    Excel에서 한글이 깨지지 않도록 UTF-8 BOM(utf-8-sig)으로 인코딩한다.
    """
    columns = list(dp.CLEAN_REQUIRED_COLUMNS)
    example = {col: _REQUIRED_COLUMN_GUIDE.get(col, ("", ""))[1] for col in columns}
    template_df = pd.DataFrame([example], columns=columns)
    return template_df.to_csv(index=False).encode("utf-8-sig")


def _call_with_supported_args(func: Any, *args: Any) -> Any:
    """모듈 함수의 파라미터 개수에 맞춰 안전하게 호출하는 내부 어댑터."""
    sig = inspect.signature(func)
    param_count = len(sig.parameters)
    return func(*args[:param_count])


def _to_json_safe(value: Any) -> Any:
    """set 등 JSON 직렬화가 불가능한 타입을 재귀적으로 변환."""
    if isinstance(value, set):
        return sorted(str(item) for item in value)
    if isinstance(value, dict):
        return {str(k): _to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(item) for item in value]
    return value


def run_audit_from_df(
    raw_df: pd.DataFrame,
    catalog_path: str = DEFAULT_CATALOG_PATH,
) -> dict[str, Any]:
    """업로드된 원본 DataFrame을 받아 10주차 백엔드 파이프라인 전체 실행.

    Args:
        raw_df: 업로드된 원본 결제 내역 DataFrame.
        catalog_path: 표준 SaaS 카탈로그 JSON 경로.

    Returns:
        정제된 DataFrame(clean_df), 누수 분석(seat_leakage), 중복 분석(duplicate_tags),
        Mock LLM 결과(llm_questions, llm_report)를 담은 딕셔너리.

    Raises:
        ValueError: 입력 데이터가 비어 있거나 필수 컬럼이 누락된 경우.
        KeyError: 스키마 필수 컬럼이 존재하지 않는 경우.
    """
    if raw_df is None or raw_df.empty:
        raise ValueError("업로드된 CSV에 데이터가 없습니다.")

    catalog = dp.load_saas_catalog(catalog_path)

    # 1. PII 마스킹 및 데이터 정제 (표준 스키마 순서 준수)
    masked_raw_df = dp.mask_pii_data(raw_df)
    cleaned_df, clean_warnings = _call_with_supported_args(
        dp.clean_billing_csv, masked_raw_df, catalog
    )
    masked_df = dp.mask_pii_data(cleaned_df)

    if masked_df.empty:
        raise ValueError("정제 조건을 통과한 유효한 결제 내역이 없습니다.")

    # 2. 정량 분석 (유휴 좌석 누수 및 중복 기능 태그 탐지)
    seat_leakage = _call_with_supported_args(
        qa.calculate_seat_leakage, masked_df, catalog
    )
    duplicate_tags = _call_with_supported_args(
        qa.detect_duplicate_tags, masked_df, catalog
    )

    # 3. Mock LLM 진단 연동 (llm_utils.py 실제 시그니처 호출)
    initial_state: dict[str, Any] = {
        "process_codes": ["P1", "P2", "P3", "P4", "P5"],
        "filled_slots": {},
        "missing_slots": ["C-01", "C-02", "C-03", "C-04"],
    }
    extra_data: dict[str, Any] = _to_json_safe(
        {
            "seat_leakage": seat_leakage,
            "duplicate_tags": duplicate_tags,
        }
    )

    question_prompt = llm.build_prompt_template(
        "question", initial_state, extra_data
    )
    question_raw = llm.call_llm_request(question_prompt)
    llm_questions = llm.parse_and_validate_json(
        question_raw, llm.QuestionBatch
    )

    report_prompt = llm.build_prompt_template(
        "report", initial_state, extra_data
    )
    report_raw = llm.call_llm_request(report_prompt)
    llm_report = llm.parse_and_validate_json(
        report_raw, llm.FinalReport
    )

    return {
        "clean_df": masked_df,
        "clean_warnings": clean_warnings,
        "row_count": int(len(masked_df)),
        "warning_count": len(clean_warnings),
        "seat_leakage": seat_leakage,
        "duplicate_tags": duplicate_tags,
        "llm_questions": llm_questions,
        "llm_report": llm_report,
    }


def get_filter_options(clean_df: pd.DataFrame) -> dict[str, list[str]]:
    """사이드바 selectbox에 표시할 필터 옵션 목록 반환."""
    dept_col = "department" if "department" in clean_df.columns else None
    cycle_col = "billing_cycle" if "billing_cycle" in clean_df.columns else None

    departments = (
        ["전체"] + sorted(clean_df[dept_col].dropna().astype(str).unique().tolist())
        if dept_col
        else ["전체"]
    )
    billing_cycles = (
        ["전체"] + sorted(clean_df[cycle_col].dropna().astype(str).unique().tolist())
        if cycle_col
        else ["전체"]
    )

    return {
        "departments": departments,
        "billing_cycles": billing_cycles,
    }


def filter_and_summarize(
    clean_df: pd.DataFrame,
    department: str = "전체",
    billing_cycle: str = "전체",
) -> dict[str, Any]:
    """사이드바 필터 조건에 맞춰 DataFrame을 필터링하고 상단 KPI 지표 계산."""
    view_df = clean_df.copy()

    if department != "전체" and "department" in view_df.columns:
        view_df = view_df[view_df["department"] == department]

    if billing_cycle != "전체" and "billing_cycle" in view_df.columns:
        view_df = view_df[view_df["billing_cycle"] == billing_cycle]

    total_cost = int(view_df[COST_COL].sum()) if not view_df.empty else 0

    wasted_seats = 0
    wasted_cost = 0
    if "seat_count" in view_df.columns and "active_users" in view_df.columns:
        unused = (view_df["seat_count"] - view_df["active_users"]).clip(lower=0)
        wasted_seats = int(unused.sum())
        safe_seats = view_df["seat_count"].replace(0, pd.NA)
        unit_cost = (view_df[COST_COL] / safe_seats).fillna(0)
        wasted_cost = int((unused * unit_cost).sum())

    return {
        "filtered_df": view_df,
        "total_cost": total_cost,
        "wasted_seats": wasted_seats,
        "wasted_cost": wasted_cost,
        "row_count": int(len(view_df)),
    }


def get_chart_data(filtered_df: pd.DataFrame) -> pd.DataFrame:
    """st.bar_chart 시각화를 위해 서비스별 구독 비용과 낭비 금액 집계 DataFrame 반환."""
    if filtered_df.empty:
        return pd.DataFrame(columns=["서비스명", "월간 구독 비용(원)", "월간 추정 낭비 금액(원)"])
    
    calculated_df = filtered_df.assign(
        wasted_spend=(
            filtered_df[COST_COL]
            * (filtered_df["seat_count"] - filtered_df["active_users"])
            / filtered_df["seat_count"]
        ).round().astype(int)
    )

    chart_df = (
        calculated_df.groupby(SERVICE_COL, as_index=False)[[COST_COL, "wasted_spend"]]
        .sum()
        .rename(columns={
            SERVICE_COL: "서비스명", COST_COL: "월간 구독 비용(원)",
            "wasted_spend": "월간 추정 낭비 금액(원)"})
        .sort_values(by=["월간 추정 낭비 금액(원)", "월간 구독 비용(원)"], ascending=False)
    )
    return chart_df

def get_duplicate_table(
        filtered_df: pd.DataFrame,
        catalog_path: str = DEFAULT_CATALOG_PATH
        ) -> pd.DataFrame:
    """선택된 필터에 대한 중복 의심 태그를 DataFrame으로 반환."""
    catalog = dp.load_saas_catalog(catalog_path)
    duplicate_tags = _call_with_supported_args(
            qa.detect_duplicate_tags, filtered_df, catalog
        )
    if not duplicate_tags:
        return pd.DataFrame(columns=["서비스명1", "서비스명2", "중복 기능"])
    
    formatted_data = []
    for item in duplicate_tags:
        service1, service2 = item["tools"]
        common_tags = item.get("common_tags", [])
        formatted_data.append({
            "서비스명1": service1,
            "서비스명2": service2,
            "중복 기능": ", ".join(common_tags) if common_tags else "없음"
        })
    
    return pd.DataFrame(formatted_data)

def rename_columns_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame의 컬럼명을 UI 표시용 한글로 변경."""
    rename_map = {
        "tx_id": "결제 거래 ID",
        "billing_date": "결제일",
        "service_name": "서비스명",
        "department": "부서",
        "billing_cycle": "결제 주기",
        "seat_count": "구매 좌석 수",
        "active_users": "실제 사용자 수",
        "billing_amount_krw": "결제 금액(원)",
        "card_holder_pii": "결제 개인정보(마스킹됨)",
        "monthly_cost_krw": "월간 구독 비용(원)"
    }
    return df.rename(columns=rename_map)


def get_ai_reply(
    messages: dict[str, Any],
    audit_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """llm_utils를 호출해 현재 상태에 맞는 다음 질문 목록을 반환한다."""
    if not isinstance(messages, dict):
        raise TypeError("messages must be a dict")
    state = messages.get("state")
    if not isinstance(state, dict):
        raise TypeError("messages['state'] must be a dict")

    missing_slots = list(state.get("missing_slots", []))
    filled_slots = dict(state.get("filled_slots", {}))
    skipped_slots = list(state.get("skipped_slots", []))
    if not missing_slots:
        return []

    prompt_state = dict(state)
    prompt_state["filled_slots"] = filled_slots
    prompt_state["missing_slots"] = missing_slots
    prompt_state["skipped_slots"] = skipped_slots
    prompt = llm.build_prompt_template(
        "question",
        prompt_state,
        audit_context or {},
    )
    batch = llm.parse_and_validate_json(
        llm.call_llm_request(prompt),
        llm.QuestionBatch,
    )

    returned_items = batch.get("questions", [])
    questions: list[dict[str, Any]] = []
    for index, item in enumerate(returned_items):
        if index >= len(missing_slots):
            break
        questions.append({
            "question": str(item["question"]),
            "slot_id": str(missing_slots[index]),
            "category": str(item.get("category", "추가 정보")),
            "priority": str(item.get("priority", "optional")),
        })
    return questions


def initialize_chat(
    audit_result: dict[str, Any],
    session_id: str,
) -> dict[str, Any]:
    """audit_result의 llm_questions를 초기 ConversationState로 변환한다."""
    llm_questions = audit_result.get("llm_questions", {})
    question_items = llm_questions.get("questions", []) if isinstance(llm_questions, dict) else []
    questions: list[dict[str, Any]] = []
    for index, item in enumerate(question_items):
        if not isinstance(item, dict) or not item.get("question"):
            continue
        questions.append({
            "question": str(item["question"]),
            "slot_id": str(item.get("slot_id", f"C-{index + 1:02d}")),
            "category": str(item.get("category", "추가 정보")),
            "priority": str(item.get("priority", "optional")),
        })

    state: dict[str, Any] = {
        "session_id": session_id,
        "round_number": int(llm_questions.get("round_number", 1)) if isinstance(llm_questions, dict) else 1,
        "process_codes": ["P1", "P2", "P3", "P4", "P5"],
        "filled_slots": {},
        "missing_slots": [item["slot_id"] for item in questions],
        "skipped_slots": [],
        "question_history": [
            {
                "slot_id": item["slot_id"],
                "question": item["question"],
                "round_number": int(llm_questions.get("round_number", 1)) if isinstance(llm_questions, dict) else 1,
            }
            for item in questions
        ],
        "answer_history": [],
        "can_finish_now": bool(llm_questions.get("can_finish_now", False)) if isinstance(llm_questions, dict) else False,
        "current_questions": questions,
        "end_reason": None,
    }
    chat_history = (
        [{"role": "assistant", "content": questions[0]["question"]}]
        if questions
        else []
    )
    audit_context = _to_json_safe({
        "seat_leakage": audit_result.get("seat_leakage", []),
        "duplicate_tags": audit_result.get("duplicate_tags", []),
    })
    return {
        "state": state,
        "questions": questions,
        "chat_history": chat_history,
        "audit_context": audit_context,
    }


def submit_chat_answer(
    state: dict[str, Any],
    answer: str,
    question: dict[str, Any],
    audit_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """한 질문의 답변과 상태를 누적 갱신한다."""
    next_state = dict(state)
    next_state["filled_slots"] = dict(next_state.get("filled_slots", {}))
    next_state["missing_slots"] = list(next_state.get("missing_slots", []))
    next_state["answer_history"] = list(next_state.get("answer_history", []))
    next_state["question_history"] = list(next_state.get("question_history", []))
    next_state["current_questions"] = list(next_state.get("current_questions", []))

    slot_id = str(question["slot_id"])
    cleaned_answer = answer.strip()
    round_number = int(next_state.get("round_number", 1))
    next_state["filled_slots"][slot_id] = {
        "value": cleaned_answer,
        "source": "user",
        "evidence": cleaned_answer,
        "round_number": round_number,
    }
    next_state["missing_slots"] = [
        slot for slot in next_state["missing_slots"] if slot != slot_id
    ]
    next_state["answer_history"].append({
        "slot_id": slot_id,
        "answer": cleaned_answer,
        "round_number": round_number,
    })
    next_state["question_history"].append({
        "slot_id": slot_id,
        "question": question["question"],
        "round_number": round_number,
    })
    next_state["current_questions"] = [
        item for item in next_state["current_questions"] if item["slot_id"] != slot_id
    ]
    next_state["round_number"] = round_number + 1
    next_question = next_state["current_questions"][0] if next_state["current_questions"] else None
    if next_question is None:
        refill = get_ai_reply(
            {
                "messages": [{"role": "user", "content": cleaned_answer}],
                "state": next_state,
            },
            audit_context,
        )
        if refill:
            next_state["current_questions"] = refill
            next_question = refill[0]
        else:
            next_state["end_reason"] = "completed"
    return {
        "state": next_state,
        "finished": not next_state["current_questions"],
        "next_question": next_question,
    }


def skip_chat_question(
    state: dict[str, Any],
    question: dict[str, Any],
    audit_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """한 질문을 스킵하고 상태를 누적 갱신한다."""
    next_state = dict(state)
    next_state["skipped_slots"] = list(next_state.get("skipped_slots", []))
    next_state["missing_slots"] = list(next_state.get("missing_slots", []))
    next_state["current_questions"] = list(next_state.get("current_questions", []))
    next_state["question_history"] = list(next_state.get("question_history", []))

    slot_id = str(question["slot_id"])
    if slot_id not in next_state["skipped_slots"]:
        next_state["skipped_slots"].append(slot_id)
    next_state["missing_slots"] = [
        slot for slot in next_state["missing_slots"] if slot != slot_id
    ]
    next_state["current_questions"] = [
        item for item in next_state["current_questions"] if item["slot_id"] != slot_id
    ]
    next_state["question_history"].append({
        "slot_id": slot_id,
        "question": question["question"],
        "round_number": int(next_state.get("round_number", 1)),
    })
    next_state["round_number"] = int(next_state.get("round_number", 1)) + 1
    next_question = next_state["current_questions"][0] if next_state["current_questions"] else None
    if next_question is None:
        refill = get_ai_reply(
            {
                "messages": [{"role": "system", "content": "사용자가 질문을 스킵했습니다."}],
                "state": next_state,
            },
            audit_context,
        )
        if refill:
            next_state["current_questions"] = refill
            next_question = refill[0]
        else:
            next_state["end_reason"] = "completed"
    return {
        "state": next_state,
        "finished": not next_state["current_questions"],
        "next_question": next_question,
    }


def skip_whole_chat(state: dict[str, Any]) -> dict[str, Any]:
    """전체 챗봇 상호작용을 종료한다."""
    next_state = dict(state)
    next_state["can_finish_now"] = True
    next_state["user_requested_finish"] = True
    next_state["current_questions"] = []
    next_state["end_reason"] = "skipped"
    return {"state": next_state, "finished": True}


def reset_chat(audit_result: dict[str, Any], session_id: str) -> dict[str, Any]:
    """대화 상태와 이력을 처음 상태로 되돌린다."""
    return initialize_chat(audit_result, session_id)