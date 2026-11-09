#  BIRDS: 스타트업 업무 프로세스 기반 SaaS 정밀 감사 및 추천 AI 솔루션

> **AI 오케스트레이션 스튜디오 — 10주차 백엔드 통합 및 AI 통제 기록 아카이브**

BIRDS는 스타트업 내부 운영(Internal Operations)에서 발생하는 무분별한 SaaS 구독(Shadow IT), 유휴 좌석 누수(Seat Leakage), 기능 중복 결제를 정량적으로 감사(Audit)하고, **사전 설계된 5대 업무 프로세스(P1~P5) 및 결측 변수(Slot) 스키마**를 바탕으로 LLM이 타겟 역질문을 수행하여 최적의 SaaS 포트폴리오를 제안하는 솔루션입니다.

---

## 1. 1차 발표 피드백 반영: 시장 니즈, 기존 ERP 비교 및 서비스 설계 구체화

### 1-1. 스타트업의 실제 내부 운영 페인포인트
스타트업은 빠른 실행을 위해 개발·디자인·마케팅·경영지원 각 팀이 법인카드로 SaaS를 개별 도입합니다. 이 과정에서 **① 퇴사자·휴면 계정 미회수로 인한 유휴 좌석 과금**, **② 부서 간 동일 기능 툴 중복 결제(예: Notion·Jira·Asana 동시 구독)**, **③ 무료 Viewer로 전환 가능한 인원에게 유료 Editor 시트 부여** 등 매월 구조적인 비용 누수가 발생합니다.

### 1-2. 기존 ERP(더존·SAP·Oracle) 분석 및 BIRDS의 차별화 영역

| 비교 기준 | 기존 중소·중견 ERP (더존 WEHAGO/Amaranth 10, SAP B1, Oracle NetSuite) | BIRDS (SaaS 정밀 감사 & 프로세스 기반 추천 AI) |
| :--- | :--- | :--- |
| **핵심 목적** | 세금계산서 발행, 전표 분개, 급여·4대보험, 재고 등 **법적·재무적 사후 기록(System of Record)** | 부서별 실제 업무 워크플로우 기반 **SaaS 비용 누수 탐지 및 도구 최적화(System of Intelligence)** |
| **데이터 처리 수준** | 법인카드 결제 총액을 `지급수수료(소프트웨어)` 계정과목 하나로 뭉뚱그려 사후 집계 | 결제 CSV의 서비스 별칭(Alias)을 표준 카탈로그와 매칭해 **결제 좌석 수(`seat_count`) 대비 실사용자(`active_users`) 누수액**을 툴 단위로 정밀 산출 |
| **업무 맥락 파악** | 해당 SaaS가 어떤 업무 프로세스에 쓰이는지, 왜 중복 결제되었는지 파악 불가 | **스타트업 5대 업무 프로세스(P1~P5)** 및 **결측 변수(Missing Slot)** 설계도를 기반으로 LLM이 역질문하여 도입 맥락(외주 인원, 고객사 공유용 등)을 수집 |
| **관계 정의** | 코어 재무·인사 인프라 (P5 경영지원 영역) | 기존 ERP를 대체하는 것이 아니라, **ERP가 보지 못하는 SaaS 운영 사각지대를 보완하고 ERP 기본 모듈과 버티컬 SaaS의 중복까지 진단**하는 맞춤형 감사 레이어 |

### 1-3. 프로세스 설계 기준(`slot_schema.json` & `docs/schema.md`) 기반 LLM 역질문 아키텍처
LLM이 막연하게 자유 질문을 던지지 않도록, 기업의 내부 운영을 **5대 코어 프로세스(25개 세부 업무)**와 **공통·프로세스별 필수 확인 변수(Slot)**로 먼저 구조화했습니다.
- **P1. 개발 (`DEV`)**: 서비스 유형(`P1-S01`), 기술 스택(`P1-S02`), 외주 인력 구성(`P1-S08`), 코드 외부 전송 허용 여부(`P1-S09`) 등
- **P2. 디자인 (`DESIGN`)**: 산출물 유형(`P2-S01`), 개발/마케팅 핸드오프 방식(`P2-S04`), 비디자이너 참여 여부(`P2-S05`) 등
- **P3. 문서/PM (`DOC_PM`)**: 프로젝트 운영 방식(`P3-S02`), 외부 고객·파트너 공유 범위(`P3-S04`), 메신저 연동(`P3-S09`) 등
- **P4. 세일즈 (`SALES`)**: 판매 모델(`P4-S01`), 영업 사이클·단가(`P4-S02`), 세금계산서·ERP 연동(`P4-S11`) 등
- **P5. 경영지원 (`BACKOFFICE`)**: 회계 처리 주체(`P5-S02`), 법인카드·경비 승인 라인(`P5-S06`), 기존 ERP 보유 여부(`P5-S10`) 등

> **역질문 동작 원리:** Python 정량 엔진이 1차로 유휴 좌석과 중복 의심 도구를 탐지하면, `llm_utils.build_prompt_template()`은 현재 상태(`ConversationState`)에서 **아직 채워지지 않은 필수 변수(`missing_slots`)만 질문 후보로 제한**하여 JSON 스키마(`QuestionBatch`) 규격의 역질문을 생성합니다.

### 1-4. 비즈니스 모델 및 리텐션(Retention) 전략
- **1단계 — 일회성 정밀 감사 리포트 (도입 장벽 최소화):** 매일 접속해야 하는 무거운 대시보드 대신, 법인카드 결제 내역 CSV 1회 업로드만으로 즉시 월간 절감 가능 금액과 대표 결재용 요약(`approval_summary`)을 제공하는 **일회성 감사(One-off Audit) 모델**로 초기 고객을 확보합니다.
- **2단계 — 계약 갱신 주기(Renewal Cycle) 기반 리텐션:** 감사 과정에서 파악된 연간/월간 구독 서비스의 **계약 갱신일 D-30 시점** 및 **분기별 결산 시점**에 맞춰 자동 재진단 알림을 발송하여, 일회성 진단을 넘어 주기적인 비용 통제 파이프라인으로 리텐션을 유지합니다.

---

## 2. 10주차 백엔드 통합 워크플로우 및 아키텍처 (`pipeline.py`)

### 2-1. 전체 파이프라인 데이터 흐름도
팀 표준 데이터 계약 문서([`docs/schema.md`](./docs/schema.md))에 정의된 순서와 입출력 타입을 엄격히 준수하여 동작합니다.

```text
[원본 결제 CSV & 카탈로그 JSON]
   │
   ▼  1. 데이터 로드 (data_processing.py: load_billing_csv, load_saas_catalog)
[raw_df: DataFrame, catalog: dict]
   │
   ▼  2. 개인정보 마스킹 (data_processing.py: mask_pii_data)
[masked_df: DataFrame]  ── (경계 assert: card_holder_pii == "[REDACTED]" 검증)
   │
   ▼  3. 데이터 정제 및 표준화 (data_processing.py: clean_billing_csv)
[clean_df: DataFrame, warnings: list[dict]]
   │
   ▼  4. 정량 분석 (quant_analysis.py: calculate_seat_leakage, detect_duplicate_tags)
[seat_leakage: list[SeatLeakage], raw_duplicate_pairs: list[dict]]
   │
   ▼  5. 경계 어댑터 변환 (pipeline.py: adapt_duplicate_pairs_for_json, summarize_analysis_for_llm)
[analysis_summary: dict] ── (set -> 정렬된 list[str] 변환 및 필수 키 경계 assert 검증)
   │
   ▼  6. Mock LLM 연동 및 DTO 검증 (llm_utils.py: build_prompt_template -> call_llm_request -> parse_and_validate_json)
[최종 구조화 반환 dict (meta, clean_data, warnings, summary, llm_questions, llm_report)]

```

### 2-2. 통합 파이프라인 실행 방법 및 Fixture 실행 로그

```bash
python pipeline.py

```

```text
=================================================================
 [1] Fixture 입력 기반 백엔드 파이프라인 관통 실행 검증
=================================================================
- USE_MOCK 상태: True
- 정제 통과 행 수: 3건
- 총 월간 구독 비용: 450,000원
- 총 유휴 좌석 수: 13석
- 총 월간 낭비 금액: 130,000원
- 중복 기능 탐지 쌍: [{'tools': ['Notion', 'Slack'], 'categories': ['협업']}, {'tools': ['Jira', 'Slack'], 'categories': ['협업']}, {'tools': ['Jira', 'Notion'], 'categories': ['프로젝트관리', '협업']}]
- Mock LLM 역질문 샘플: [MOCK] 현재 이 업무에 몇 명이 함께 참여하나요?
- Mock LLM 리포트 요약: [MOCK] 최종 진단 요약

```

---

## 3. 10주차 과제 산출물 및 팀원별 역할·기여 안내

* **백엔드 통합 스크립트**: [`pipeline.py`](https://www.google.com/search?q=./pipeline.py)
* **팀 표준 데이터 스키마 및 5대 프로세스·Slot 정의서**: [`docs/schema.md`](https://www.google.com/search?q=./docs/schema.md), [`slot_schema.json`](https://www.google.com/search?q=./slot_schema.json)
* **프롬프트 템플릿 초안**: [`prompts/question_template.md`](https://www.google.com/search?q=./prompts/question_template.md)
* **AI 통제 기록 아카이브 (팀원당 2건 이상, 표준 5요소)**: [`ai_log/`](https://www.google.com/search?q=./ai_log/)
* 강규민: [`ai_log/gyumin_log.md`](https://www.google.com/search?q=./ai_log/gyumin_log.md)
* 김서연: [`ai_log/seoyeon_log.md`](https://www.google.com/search?q=./ai_log/seoyeon_log.md)
* 차세연: [`ai_log/chaseyeon_log.md`](https://www.google.com/search?q=./ai_log/chaseyeon_log.md)
* 장형욱: [`ai_log/hyungwook_log.md`](https://www.google.com/search?q=./ai_log/hyungwook_log.md)
* 박지우: [`ai_log/jiwoo_log.md`](https://www.google.com/search?q=./ai_log/jiwoo_log.md)


* **단위 및 통합 테스트 실행 로그**: [`pytest_result.log`](https://www.google.com/search?q=./pytest_result.log)
* **5주차 보안 점검표 (10주차 전 항목 마킹 및 `.env` 미커밋 확인)**: [`security_checklist.md`](https://www.google.com/search?q=./security_checklist.md)

| 담당자 | 9주차/10주차 담당 모듈 및 리팩터링 대상 | 10주차 통합 특화 역할 |
| --- | --- | --- |
| **강규민** | `mask_pii_data()` (`data_processing.py`) | `pipeline.py` 통합 오케스트레이션, 경계 어댑터 구현, 아키텍처·리텐션 설계 |
| **차세연** | `load_billing_csv()`, `load_saas_catalog()` (`data_processing.py`) | `docs/schema.md` 팀 표준 데이터 계약 및 5대 프로세스 스키마 정립 |
| **박지우** | `clean_billing_csv()` (`data_processing.py`) | 정제 모듈 구조 개선, 2차시 교차 코드 리뷰 반영 및 문서화 |
| **김서연** | `calculate_seat_leakage()` (`quant_analysis.py`) | `llm_utils.py` (Mock LLM 패턴·DTO 검증) 및 `prompts/` 템플릿 구축 |
| **장형욱** | `detect_duplicate_tags()` (`quant_analysis.py`) | `test_integration.py` 파이프라인 통합 테스트 및 보안/히스토리 감사 |

---

## 4. 2차시 교차 코드 리뷰 코멘트 반영 내역

| 번호 | 리뷰 대상 모듈 | 수신한 리뷰 코멘트 요지 | 수용/보류 판단 및 사유 | 반영 내역 및 관련 커밋 |
| --- | --- | --- | --- | --- |
| 1 | `data_processing.py` / `quant_analysis.py` | *(박지우 님 교차 리뷰 코멘트 1건 기입란)* | **수용** — *(판단 사유 기입)* | *(관련 커밋 해시 기입)* |
| 2 | `data_processing.py` / `llm_utils.py` | *(박지우 님 교차 리뷰 코멘트 2건 기입란)* | **수용/보류** — *(판단 사유 기입)* | *(관련 커밋 해시 기입)* |

---

## 5. 9주차 과제 제출 산출물 안내 (아카이브 보존)

* **팀원별 구현 함수 및 제출 체크리스트**: [`assignment_checklist.md`](https://www.google.com/search?q=./assignment_checklist.md)
* **9주차 프롬프트 원문 및 결함 수정 로그**: [`prompt_log.md`](https://www.google.com/search?q=./prompt_log.md)
* **보안 점검표**: [`security_checklist.md`](https://www.google.com/search?q=./security_checklist.md)
* **테스트 상세 실행 로그 (pytest)**: [`pytest_result.log`](https://www.google.com/search?q=./pytest_result.log)

```

---

## Step 5. [기록 5] 문서(`ai_log`, `README`, `pytest_result.log`) 분리 커밋 및 푸시

코드 커밋(`feat:`)과 문서 커밋(`docs:`)이 Git 히스토리에서 명확히 분리되도록 아래 명령어로 최종 커밋 및 푸시를 진행합니다[cite: 36, 48].

```powershell
# 1. 변경된 문서 파일 3개 스테이징
git add ai_log/gyumin_log.md README.md pytest_result.log

# 2. docs: 접두사로 분리 커밋
git commit -m "docs: 강규민 AI 통제 기록 2호 추가 및 피드백·통합 아키텍처 README 반영"

# 3. 원격 저장소에 푸시 (팀원들과 공유)
git push origin main

# 4. 노션 [기록 5] 행에 적을 최종 커밋 해시 확인
git rev-parse --short HEAD

```