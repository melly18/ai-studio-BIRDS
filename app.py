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

st.title("🦅 BIRDS SaaS 비용 누수 & 중복 구독 진단 대시보드")
st.caption("스타트업 결제 내역 CSV를 업로드하면 부서별 SaaS 비용 누수와 중복 도구를 즉시 진단합니다.")

# =====================================================================
# [TODO: UI B1 - 차세연 님 작업 구역]
# 1. st.file_uploader로 CSV 업로드 받기
# 2. uploaded is None 이면 st.info 안내 메시지 출력 후 st.stop() 호출
# 3. 새로운 파일 업로드 시 backend.load_csv_with_fallback(uploaded) 및
#    backend.run_audit_from_df(raw_df)를 호출해 st.session_state.audit_result 에 저장
# 4. 잘못된 CSV(ValueError, KeyError) 발생 시 st.error 안내 후 st.stop() 방어
# =====================================================================


# =====================================================================
# [TODO: UI B2 - 박지우 님 작업 구역]
# 1. st.session_state.audit_result["clean_df"]를 가져와
#    backend.get_filter_options(clean_df)로 사이드바 필터 옵션 획득
# 2. st.sidebar.selectbox 로 부서/결제주기 필터 위젯 배치
# 3. backend.filter_and_summarize(clean_df, selected_dept, selected_cycle) 호출
# 4. st.columns(3) 및 st.metric 3종(총 월간 구독 비용, 유휴 좌석 수, 추정 낭비 금액) 출력
# =====================================================================


# =====================================================================
# [TODO: UI B3 - 김서연 님 작업 구역]
# 1. st.tabs(["📊 비용·누수 차트", "📋 정제 데이터 및 진단 상세"]) 구성
# 2. 탭1: backend.get_chart_data(filtered_df) 호출 후 st.bar_chart 출력
# 3. 탭2: st.dataframe(filtered_df) 원본 표 출력 및
#    st.expander로 중복 의심 태그(duplicate_tags) / Mock LLM 역질문 표시
# =====================================================================