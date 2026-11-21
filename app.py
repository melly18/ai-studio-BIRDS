"""BIRDS SaaS 비용 누수 및 중복 구독 진단 대시보드 (Streamlit UI)."""

import streamlit as st

import backend

# [규칙 1] 페이지 기본 환경 설정은 반드시 첫 번째 Streamlit 명령이어야 함
st.set_page_config(
    page_title="BIRDS - SaaS 비용 최적화 대시보드",
    page_icon="🦅",
    layout="wide",
)

# [규칙 2] st.session_state 표준 초기화 프로토콜 (Rerun 시 데이터 유실 및 재연산 방지)
if "audit_result" not in st.session_state:
    st.session_state.audit_result = None

if "uploaded_file_id" not in st.session_state:
    st.session_state.uploaded_file_id = None

# 업로드 파일을 실제로 읽은 인코딩("utf-8"/"cp949"). 필터 Rerun 후에도 경고 유지용
if "detected_encoding" not in st.session_state:
    st.session_state.detected_encoding = None

# 사이드바 필터 위젯(key)의 기본값. 파일 교체 시 이 값으로 되돌린다.
FILTER_DEFAULTS = {"dept_filter": "전체", "cycle_filter": "전체"}
for _key, _default in FILTER_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default

st.title("🦅 BIRDS SaaS 비용 누수 & 중복 구독 진단 대시보드")
st.caption("스타트업 결제 내역 CSV를 업로드하면 부서별 SaaS 비용 누수와 중복 도구를 즉시 진단합니다.")

# =====================================================================
# [TODO: UI B1 - 차세연 님 작업 구역]
# 1. st.file_uploader로 CSV 업로드 받기
# 2. uploaded is None 이면 st.info 안내 메시지 출력 후 st.stop() 호출
# 3. 새로운 파일 업로드 시 backend.load_csv_with_encoding(uploaded) 및
#    backend.run_audit_from_df(raw_df)를 호출해 st.session_state.audit_result 에 저장
# 4. 잘못된 CSV(ValueError, KeyError) 발생 시 st.error 안내 후 st.stop() 방어
# =====================================================================

def reset_upload_state() -> None:
    """업로드 상태 리셋 (3단계 프로토콜의 '쓰기').

    최초 1회 초기화는 상단 `if "키" not in st.session_state:` 블록이 담당하고,
    이 함수는 파일 교체·제거·처리 실패 이벤트 시 이전 결과와 필터 선택을 비우는 용도다.
    반드시 사이드바 selectbox 생성 전에 호출해야 한다(위젯 생성 후 key 변경 시 예외).
    """
    st.session_state.audit_result = None
    st.session_state.uploaded_file_id = None
    st.session_state.detected_encoding = None
    for key, default in FILTER_DEFAULTS.items():
        st.session_state[key] = default

# 1. 입력: 파일 업로드
uploaded = st.file_uploader("결제 내역 CSV를 드래그 앤 드롭하세요", type="csv")

# 2. 가드: 업로드 전이면 안내 후 중단
if uploaded is None:
    reset_upload_state()  # 파일을 지운 경우 이전 결과가 남지 않도록 리셋
    st.info("결제 내역 CSV 파일을 업로드하면 SaaS 비용 진단이 시작됩니다.")
    with st.expander("📋 CSV 필수 열 9종 및 예시 형식", expanded=True):
        st.dataframe(
            backend.get_required_columns_guide(),
            hide_index=True,
            width="stretch",
        )
        st.caption("첫 행은 위 열 이름 헤더여야 하며, UTF-8 또는 CP949 인코딩을 지원합니다.")
        st.download_button(
            "⬇️ 템플릿 CSV 다운로드",
            data=backend.get_template_csv_bytes(),
            file_name="billing_template.csv",
            mime="text/csv",
        )
    st.stop()

# 3. 처리: 새 파일일 때만 백엔드 파이프라인 실행 (필터 조작 등 Rerun 시 재연산 방지)
if st.session_state.uploaded_file_id != uploaded.file_id:
    reset_upload_state()  # 파일 교체 시 이전 결과·필터(dept/cycle)를 먼저 리셋
    try:
        with st.spinner("결제 내역을 분석하는 중입니다..."):
            raw_df, encoding = backend.load_csv_with_encoding(uploaded)  # cp949 재시도 포함
            st.session_state.audit_result = backend.run_audit_from_df(raw_df)
        st.session_state.uploaded_file_id = uploaded.file_id
        st.session_state.detected_encoding = encoding
    except (ValueError, KeyError) as exc:
        reset_upload_state()
        st.error(f"CSV 파일을 처리할 수 없습니다. 필수 컬럼과 형식을 확인해 주세요.\n\n상세: {exc}")
        st.stop()
    except FileNotFoundError:
        reset_upload_state()
        st.error("분석에 필요한 SaaS 카탈로그 파일을 찾을 수 없습니다. 관리자에게 문의하세요.")
        st.stop()

# 4. 결과 안내: 정상 업로드·검토 완료 표시 (Rerun 후에도 유지)
result = st.session_state.audit_result
if st.session_state.detected_encoding == "cp949":
    st.warning("인코딩을 CP949로 감지하여 읽었습니다.")
st.success(
    f"✅ '{uploaded.name}' 업로드 완료 · 검토 완료 — "
    f"유효 결제 내역 {result['row_count']:,}건 "
    f"(정제 중 제외·보정 {result['warning_count']:,}건)"
)


# =====================================================================
# [TODO: UI B2 - 박지우 님 작업 구역]
# 1. st.session_state.audit_result["clean_df"]를 가져와
#    backend.get_filter_options(clean_df)로 사이드바 필터 옵션 획득
# 2. st.sidebar.selectbox 로 부서/결제주기 필터 위젯 배치
# 3. backend.filter_and_summarize(clean_df, selected_dept, selected_cycle) 호출
# 4. st.columns(3) 및 st.metric 3종(총 월간 구독 비용, 유휴 좌석 수, 추정 낭비 금액) 출력
# =====================================================================
clean_df = st.session_state.audit_result["clean_df"]
options = backend.get_filter_options(clean_df)

selected_dept = st.sidebar.selectbox(
    "부서 선택",
    options["departments"],
    key="dept_filter",
)
selected_cycle = st.sidebar.selectbox(
    "결제 주기",
    options["billing_cycles"],
    key="cycle_filter",
)

summary = backend.filter_and_summarize(clean_df, selected_dept, selected_cycle)
filtered_df = summary["filtered_df"]

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("총 월간 구독 비용", f"{summary['total_cost']:,}원")

with col2:
    st.metric("유휴 좌석 수", f"{summary['wasted_seats']:,}")

with col3:
    st.metric("월간 추정 낭비 금액", f"{summary['wasted_cost']:,}원")


# =====================================================================
# [TODO: UI B3 - 김서연 님 작업 구역]
# 1. st.tabs(["📊 비용·누수 차트", "📋 정제 데이터 및 진단 상세"]) 구성
# 2. 탭1: backend.get_chart_data(filtered_df) 호출 후 st.bar_chart 출력
# 3. 탭2: st.dataframe(filtered_df) 원본 표 출력 및
#    st.expander로 중복 의심 태그(duplicate_tags) / Mock LLM 역질문 표시
# =====================================================================

chart_tab, detail_tab = st.tabs(
    ["📊 비용·누수 차트", "📋 정제 데이터 및 진단 상세"]
)

with chart_tab:
    chart_data = backend.get_chart_data(filtered_df)
    if chart_data.empty:
        st.info("선택한 필터에 해당하는 차트 데이터가 없습니다.")
    else:
        if len(chart_data) > 10:
            show_all = st.toggle(f"전체 {len(chart_data)}개 서비스 모두 보기", value=False)
            display_data = chart_data if show_all else chart_data.head(10)
        else:
            display_data = chart_data

        st.bar_chart(
                    display_data,
                    x="서비스명",
                    y=["월간 구독 비용(원)", "월간 추정 낭비 금액(원)"],
                    y_label="금액(원)",
                    color=["blue", "red"],
                    horizontal=True,
                    sort=False,
                    stack=False,
                )

with detail_tab:
    st.subheader("전체 결제 내역")
    st.caption("모든 결제 내역에 대한 월별 지출액 항목(monthly_cost_krw)이 추가되었습니다.")
    if filtered_df.empty:
        st.info("선택한 필터에 해당하는 결제 내역이 없습니다.")
    else:
        st.dataframe(filtered_df, use_container_width=True)

    duplicate_tags = backend.get_duplicate_table(filtered_df)
    with st.expander(f"기능 중복 의심 {len(duplicate_tags)}건"):
        if duplicate_tags.empty:
            st.info("현재 이용 중인 서비스 간 기능 중복이 없습니다.")
        else:
            st.dataframe(duplicate_tags, use_container_width=True)

    with st.expander("상세 진단을 위한 AI 어시스턴트"):
        questions = result["llm_questions"]["questions"]
        if questions:
            for question in questions:
                st.markdown(f"**{question['question']}**")
        else:
            st.info("현재 질문드릴 사항이 없습니다.")

        if st.button("진단하러 가기"):
            st.info("LLM 챗봇 UI는 다음 작업에서 연결됩니다.")