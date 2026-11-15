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

# 1. 입력: 파일 업로드
uploaded = st.file_uploader("결제 내역 CSV를 드래그 앤 드롭하세요", type="csv")

# 2. 가드: 업로드 전이면 안내 후 중단
if uploaded is None:
    # 파일을 지운 경우 이전 결과가 남지 않도록 상태 초기화
    st.session_state.audit_result = None
    st.session_state.uploaded_file_id = None
    st.info("결제 내역 CSV 파일을 업로드하면 SaaS 비용 진단이 시작됩니다.")
    st.stop()

# 3. 처리: 새 파일일 때만 백엔드 파이프라인 실행 (필터 조작 등 Rerun 시 재연산 방지)
if st.session_state.uploaded_file_id != uploaded.file_id:
    try:
        with st.spinner("결제 내역을 분석하는 중입니다..."):
            raw_df = backend.load_csv_with_fallback(uploaded)  # cp949 재시도 포함
            st.session_state.audit_result = backend.run_audit_from_df(raw_df)
        st.session_state.uploaded_file_id = uploaded.file_id
    except (ValueError, KeyError) as exc:
        st.session_state.audit_result = None
        st.session_state.uploaded_file_id = None
        st.error(f"CSV 파일을 처리할 수 없습니다. 필수 컬럼과 형식을 확인해 주세요.\n\n상세: {exc}")
        st.stop()
    except FileNotFoundError:
        st.session_state.audit_result = None
        st.session_state.uploaded_file_id = None
        st.error("분석에 필요한 SaaS 카탈로그 파일을 찾을 수 없습니다. 관리자에게 문의하세요.")
        st.stop()

# 4. 결과 안내: 정상 업로드·검토 완료 표시 (Rerun 후에도 유지)
result = st.session_state.audit_result
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


# =====================================================================
# [TODO: UI B3 - 김서연 님 작업 구역]
# 1. st.tabs(["📊 비용·누수 차트", "📋 정제 데이터 및 진단 상세"]) 구성
# 2. 탭1: backend.get_chart_data(filtered_df) 호출 후 st.bar_chart 출력
# 3. 탭2: st.dataframe(filtered_df) 원본 표 출력 및
#    st.expander로 중복 의심 태그(duplicate_tags) / Mock LLM 역질문 표시
# =====================================================================