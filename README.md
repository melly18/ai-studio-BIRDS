# 🦅 BIRDS: 스타트업 업무 프로세스 기반 SaaS 정밀 감사 및 추천 AI 솔루션

> **AI 오케스트레이션 스튜디오 — 10주차(백엔드 통합) & 11주차(대시보드 앱) 최종 산출물**

BIRDS는 스타트업 내부 운영(Internal Operations)에서 발생하는 무분별한 SaaS 구독(Shadow IT), 유휴 좌석 누수(Seat Leakage), 기능 중복 결제를 정량적으로 감사(Audit)하고, **사전 설계된 5대 업무 프로세스(P1~P5) 및 결측 변수(Slot) 스키마**를 바탕으로 LLM이 타겟 역질문을 수행하여 최적의 SaaS 포트폴리오를 제안하는 솔루션입니다.

---

## 1. 프로젝트 비즈니스 모델 및 1차 피드백 반영

### 1-1. 스타트업의 실제 내부 운영 페인포인트
스타트업은 빠른 실행을 위해 개발·디자인·마케팅·경영지원 각 팀이 법인카드로 SaaS를 개별 도입합니다. 이 과정에서 **① 퇴사자·휴면 계정 미회수로 인한 유휴 좌석 과금**, **② 부서 간 동일 기능 툴 중복 결제(예: Notion·Jira·Asana 동시 구독)**, **③ 무료 Viewer로 전환 가능한 인원에게 유료 Editor 시트 부여** 등 매월 구조적인 비용 누수가 발생합니다.

### 1-2. 기존 ERP(더존·SAP·Oracle) 분석 및 BIRDS의 차별화 영역

| 비교 기준 | 기존 중소·중견 ERP (더존 WEHAGO, SAP B1 등) | BIRDS (SaaS 정밀 감사 & 프로세스 기반 추천 AI) |
| :--- | :--- | :--- |
| **핵심 목적** | 세금계산서, 전표, 급여 등 **법적·재무적 사후 기록(System of Record)** | 실제 업무 워크플로우 기반 **SaaS 비용 누수 탐지 및 최적화(System of Intelligence)** |
| **데이터 처리 수준** | 법인카드 결제 총액을 `지급수수료(소프트웨어)` 계정 하나로 사후 집계 | 결제 별칭(Alias)을 카탈로그와 매칭해 **결제 좌석(`seat_count`) 대비 실사용자(`active_users`) 누수액** 정밀 산출 |
| **업무 맥락 파악** | 해당 SaaS가 어떤 업무 프로세스에 쓰이는지 파악 불가 | **5대 업무 프로세스(P1~P5)** 및 **결측 변수(Slot)** 설계도를 기반으로 LLM이 도입 맥락 역질문 |
| **관계 정의** | 코어 재무·인사 인프라 | ERP가 보지 못하는 SaaS 운영 사각지대를 보완하고 ERP 모듈과 버티컬 SaaS의 중복까지 진단 |

### 1-3. 프로세스 설계 기준(`slot_schema.json` & `docs/schema.md`) 기반 역질문 아키텍처
LLM이 막연하게 자유 질문을 던지지 않도록 기업 내부 운영을 **5대 코어 프로세스(25개 세부 업무)**와 **필수 확인 변수(Slot)**로 구조화했습니다. (P1. 개발, P2. 디자인, P3. 문서/PM, P4. 세일즈, P5. 경영지원)
> **역질문 동작 원리:** Python 정량 엔진이 1차로 유휴 좌석과 중복 의심 도구를 탐지하면, Mock LLM 모듈(`llm_utils.build_prompt_template()`)은 현재 상태에서 **아직 채워지지 않은 필수 변수(`missing_slots`)만 질문 후보로 제한**하여 JSON 규격의 역질문을 생성합니다.

---

## 2. [10주차] 백엔드 통합 파이프라인 아키텍처 (`pipeline.py`)

팀 표준 데이터 계약 문서([`docs/schema.md`](./docs/schema.md))에 정의된 순서와 입출력 타입을 엄격히 준수하여 동작합니다.

```text
[원본 결제 CSV & 카탈로그 JSON]
   │
   ▼  1. 데이터 로드 (data_processing.py: load_csv_with_fallback)
[raw_df: DataFrame, catalog: dict]
   │
   ▼  2. 개인정보 마스킹 및 정제 (data_processing.py: mask_pii_data -> clean_billing_csv -> mask_pii_data)
[clean_df: DataFrame]  ── (경계 assert: card_holder_pii == "[REDACTED]" 방어)
   │
   ▼  3. 정량 분석 (quant_analysis.py: calculate_seat_leakage, detect_duplicate_tags)
[seat_leakage, raw_duplicate_pairs]
   │
   ▼  4. Mock LLM 연동 및 DTO 검증 (llm_utils.py: build_prompt_template -> call_llm_request -> parse_and_validate_json)
[최종 구조화 반환 dict (clean_df, seat_leakage, duplicate_tags, llm_questions, llm_report)]

```

---

## 3. [11주차] 대시보드 프로토타입 실행 가이드 (`app.py`)

### 3-1. 앱 실행 방법 (Streamlit 구동)

가상 환경 활성화 및 의존성 패키지 설치 후, 터미널에서 다음 명령어를 실행하여 웹 브라우저에서 대시보드를 구동합니다.

```bash
# 1. 의존성 패키지 설치
pip install -r requirements.txt

# 2. 대시보드 웹 앱 실행 (반드시 python app.py가 아닌 streamlit run 명령어 사용)
streamlit run app.py

```

### 3-2. UI와 백엔드 로직의 철저한 분리 원칙 적용

`app.py` 내부에는 `pandas`의 데이터 집계, 그룹화(`groupby`), 직접 필터링 연산이 단 한 줄도 포함되어 있지 않습니다. 모든 데이터 가공(인코딩 예외 처리 포함), 분석, 지표 산출 작업은 파사드 역할을 하는 **`backend.py`** 모듈로 격리했습니다. UI(`app.py`)는 오직 백엔드 함수를 호출하여 화면 위젯에 배치하는 뷰(View)의 역할만 수행합니다.

### 3-3. Streamlit 상태 관리 (`st.session_state`) 설계 의도

매 Rerun마다 백엔드의 무거운 파이프라인이 재호출되는 비효율을 방지하기 위해 3단계 상태 관리 프로토콜을 적용했습니다.

* **`st.session_state.uploaded_file_id`**: 업로더 객체의 고유 ID를 보관해 동일 파일에 대한 재연산을 건너뛰는 캐시 키 역할을 합니다.
* **`st.session_state.audit_result`**: 신규 CSV 업로드 시에만 `backend.run_audit_from_df`를 실행해 분석 결과를 영구 보존하고, 이후 가벼운 필터링과 UI 렌더링에만 재사용합니다.

---

## 4. 팀원별 기여 내역 및 11주차 릴레이 협업

11주차 대시보드 구현은 Git 충돌 방지와 UI-로직 분리 원칙 준수를 위해 `backend.py` 래퍼 구성 후 3명의 UI 작업자가 바통을 터치하는 릴레이(Waterfall) 방식으로 진행되었습니다.

| 담당자 | 10주차 파이프라인 통합 역할 | 11주차 Streamlit UI 릴레이 기여 파트 |
| --- | --- | --- |
| **강규민** | `pipeline.py` 통합 오케스트레이션, 경계 어댑터 구현 | **[A1 백엔드 래퍼]** `backend.py` 파사드 설계, JSON 직렬화 어댑터 보완 및 `app.py` 3단계 상태 초기화 골격 세팅 |
| **차세연** | `docs/schema.md` 팀 표준 데이터 계약 및 스키마 정립 | **[B1 파일 입력/예외]** 업로더 구현, 인코딩 재시도(`cp949`), 필수 컬럼 누락 에러 방어(Guard) |
| **박지우** | 데이터 정제 모듈 리팩터링, 교차 리뷰 반영 및 문서화 | **[B2 필터/지표 연동]** `backend` 호출 기반 사이드바 연동(부서/결제주기) 및 핵심 KPI 3종 `st.metric` 출력 |
| **김서연** | `llm_utils.py` Mock LLM 연동 구조 및 프롬프트 템플릿 구축 | **[B3 시각화/상세 표]** 비용/낭비 금액 다중 `st.bar_chart` 구현, 중복 의심 표·LLM 역질문 탭 구성 |
| **장형욱** | `test_integration.py` 파이프라인 통합 테스트 및 보안 감사 | **[C1 검증/보안 점검]** 3대 예외 시나리오 브라우저 렌더링 검증 캡처 및 주차별 보안 점검 완료 |

---

## 5. 10주차 & 11주차 과제 제출 산출물 링크

* **11주차 대시보드 메인 (UI)**: [`app.py`](https://www.google.com/search?q=./app.py)
* **11주차 백엔드 파사드 (UI 연동 래퍼)**: [`backend.py`](https://www.google.com/search?q=./backend.py)
* **11주차 수동 검증 시나리오 캡처**: `screenshots/week11/` 폴더 내 첨부
* **10주차 백엔드 통합 스크립트**: [`pipeline.py`](https://www.google.com/search?q=./pipeline.py)
* **팀 표준 데이터 스키마 및 프로세스 정의서**: [`docs/schema.md`](https://www.google.com/search?q=./docs/schema.md), [`slot_schema.json`](https://www.google.com/search?q=./slot_schema.json)
* **AI 통제 기록 아카이브**: [`ai_log/`](https://www.google.com/search?q=./ai_log/) (강규민, 김서연, 차세연, 장형욱, 박지우)
* **9~10주차 프롬프트 원문 및 결함 수정 로그**: [`prompt_log.md`](https://www.google.com/search?q=./prompt_log.md)
* **단위 및 통합 테스트 상세 실행 로그 (46 passed)**: [`pytest_result.log`](https://www.google.com/search?q=./pytest_result.log)
* **통합 보안 점검표 (5~11주차)**: [`security_checklist.md`](https://www.google.com/search?q=./security_checklist.md)
* **팀원별 구현 함수 및 제출 체크리스트**: [`assignment_checklist.md`](https://www.google.com/search?q=./assignment_checklist.md)

---

## 6. 교차 코드 리뷰 코멘트 반영 내역 (10주차 워크숍)

| 번호 | 리뷰 대상 모듈 | 수신한 리뷰 코멘트 요지 | 수용/보류 판단 및 사유 | 반영 내역 및 관련 커밋 |
| --- | --- | --- | --- | --- |
| 2 | `core/quant_analysis.py` | *1) 반환 스키마·docstring 불일치, 2) 태그 순서 유실, 3) 3중 중첩 완화* | **부분 수용 (1·3번 수용, 2번 보류)** — 1·3번 반영(`TypedDict`·docstring 동기화 및 `combinations` 리팩터링). 2번은 현 `dict/set` 구조 호환성 유지를 위해 보류 | *커밋 해시: 000cff9* |