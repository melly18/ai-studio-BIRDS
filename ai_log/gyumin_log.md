## [2026-11-07] mask_pii_data() Docstring 위치 오류 수정 및 상수화 리팩터링 (담당: 강규민)
- **대상 모듈**: `data_processing.py` / **관련 커밋**: `v0.9-stable` -> `7128f45`
- **초기 프롬프트(요지)**: `mask_pii_data()`에 데이터 계약(타입 힌트 및 Args/Returns Docstring)을 적용하고, 매직 스트링 상수화 및 Guard Clause 리팩터링을 수행하라.
- **AI 생성 결과(요지)**: 상수 분리 및 Docstring을 추가했으나, 빈 스키마(`df.columns.empty`) 입력 시 `ValueError`를 발생시키는 코드를 함께 생성함.
- **발견한 문제(취약점·오류·품질)**:
  1. [기존 코드 품질 문제] 9주차에 `if df.empty:` 방어 코드를 함수 첫 줄에 삽입하면서 기존 Docstring이 조건문 아래로 밀려나 파이썬 `__doc__`으로 인식되지 않는 문제와 `"card_holder_pii"`, `"[REDACTED]"` 매직 스트링 하드코딩 확인.
  2. [AI 생성 코드 계약 충돌] AI가 임의로 추가한 `df.columns.empty` 예외 발생 로직은 기존 단위 테스트(`test_mask_pii_exception_empty_df`: 빈 DataFrame 반환 계약)를 깨뜨릴 위험이 있음을 코드 리딩으로 발견.
- **수정 보완 내역**: Docstring을 함수 최상단으로 복원하여 입출력 계약을 명시하고, `PII_TARGET_COLUMN`·`PII_MASK_TOKEN` 상수로 추출함. 빈 DataFrame 입력 시 예외 대신 빈 복사본을 조기 반환(Guard Clause)하도록 유지.
- **검증 및 판단 메모**: `pytest -k "mask" -vv` 3/3 PASSED 확인 후 `refactor:` 단독 커밋 완료. AI에게 리팩터링을 맡길 때 기존 경계값 테스트 계약을 임의로 바꾸지 않도록 통제해야 함을 확인.

## [2026-11-09] pipeline.py 모듈 통합 시 경계 타입(set) 직렬화 충돌 해결 및 어댑터 적용 (담당: 강규민)
- **대상 모듈**: `pipeline.py` / **관련 커밋**: `<리팩터링_커밋해시>` -> `8331c85`
- **초기 프롬프트(요지)**: `data_processing.py`, `quant_analysis.py`, `llm_utils.py`의 함수 시그니처를 컨텍스트로 제공하고, `[로드 -> 마스킹 -> 정제 -> 정량 분석 -> Mock LLM 호출 및 검증]` 전체를 연결하는 `run_pipeline()` 오케스트레이션 스크립트를 작성하라.
- **AI 생성 결과(요지)**: `detect_duplicate_tags()`의 반환값을 그대로 `extra_data` 딕셔너리에 담아 `build_prompt_template("report", state, extra_data)`에 전달하는 단순 연결(glue) 코드를 생성함.
- **발견한 문제(취약점·오류·품질)**:
  1. [모듈 경계 반환 형식 불일치] `quant_analysis.detect_duplicate_tags()`는 각 중복 쌍의 `"tools"`와 `"common_tags"` 값을 파이썬 `set` 타입으로 반환하는 반면, `llm_utils.build_prompt_template()` 내부의 `_serialize_json()`은 `json.dumps()`를 수행하여 `set` 수신 시 `TypeError: extra_data must contain only JSON-serializable values`가 발생함을 발견.
  2. [데이터 처리 순서 불일치] AI 초안은 `clean_billing_csv()` 실행 후 `mask_pii_data()`를 호출했으나, 팀 표준 스키마(`docs/schema.md`)는 원본 로드 직후 `mask_pii_data()`로 개인정보를 먼저 마스킹한 뒤 `clean_billing_csv()`로 넘기도록 규정하고 있음.
- **수정 보완 내역**:
  1. 상대 모듈(`quant_analysis.py`)을 직접 수정하면 해당 모듈의 단위 테스트가 깨지므로, `pipeline.py` 내에 어댑터 함수(`adapt_duplicate_pairs_for_json`)를 구현하여 `set` 데이터를 정렬된 `list[str]`로 변환 후 LLM 모듈에 전달하도록 수정.
  2. `docs/schema.md` 순서(`load -> mask_pii_data -> clean_billing_csv`)로 파이프라인을 재정렬하고, 각 경계 지점마다 `assert` 문을 배치하여 마스킹 여부(`card_holder_pii == "[REDACTED]"`)와 요약 dict 필수 키 누락을 즉시 검증하도록 방어 로직 강화.
- **검증 및 판단 메모**: 고정 fixture(`make_fixture()`) 및 100건 샘플 CSV 관통 실행 성공, `pytest -vv` 전체 통과 확인 후 `feat:` 커밋 완료. 개별 단위 테스트를 통과한 모듈이라도 통합 경계에서 직렬화 타입 불일치가 발생할 수 있으며, 어댑터 함수가 책임 소재를 보존하는 가장 안전한 해결책임을 확인.

---

## [2026-11-15] Streamlit 백엔드 파사드(`backend.py`) 분리 및 상태 초기화 설계 (담당: 강규민)

* **대상 모듈**: `backend.py`, `app.py` / **관련 커밋**: `c2b4590`
* **초기 프롬프트(요지)**: 10주차 데이터 정제·분석 모듈을 Streamlit 앱에서 호출하려고 함. CSV 업로드 후 부서별 필터링, KPI 계산, 차트 데이터를 집계하는 UI 코드를 작성하라.
* **AI 생성 결과(요지)**: `app.py` 내부에 pandas의 `df[df["department"] == ...]` 연산을 직접 삽입하고, 매 Rerun마다 `st.session_state.audit_result = None`으로 무조건 초기화하는 코드를 생성함.
* **발견한 문제(취약점·오류·품질)**:
1. [아키텍처 위반] UI 파일(`app.py`) 안에 데이터 가공(pandas) 로직이 혼재되어 11주차 핵심 평가 기준인 'UI-백엔드 분리'를 위반함.
2. [상태 관리 오류] 초기화 관용구(`if "키" not in st.session_state:`) 누락으로, 사이드바 필터를 조작할 때마다 전체 스크립트가 Rerun 되며 이전 분석 결과가 날아가는 버그 확인.
* **수정 보완 내역**: UI 내부의 pandas 연산을 완전히 제거하고 `backend.py`(파사드 헬퍼 모듈)를 신설해 로직을 위임함. `app.py` 최상단에 `if "audit_result" not in st.session_state:` 조건문을 적용하여 상태가 보존되도록 리팩터링함.
* **검증 및 판단 메모**: 기존 백엔드 `pytest` 46건 통과 확인 및 `streamlit run app.py` 브라우저 정상 렌더링 검증 후 커밋 완료. Streamlit 특유의 Rerun 모델에서는 AI에게 UI 생성을 맡길 때 상태 보존(`session_state`) 여부를 반드시 의심하고 통제해야 함을 확인함.

## [2026-11-15] backend.py 내 AI 환각(존재하지 않는 함수) 호출 수정 및 직렬화 어댑터 적용 (담당: 강규민)
- **대상 모듈**: `backend.py` / **관련 커밋**: `7cf9c2f` -> `75d73d5`
- **초기 프롬프트(요지)**: `backend.py`의 `run_audit_from_df()` 내부에서 10주차에 구현한 `llm_utils.py`를 호출하여 역질문(`llm_questions`)과 최종 리포트(`llm_report`) 결과를 반환하도록 연결하라.
- **AI 생성 결과(요지)**: `if hasattr(llm, "generate_Clarifying_questions"):` 조건문과 함께 존재하지 않는 `llm.generate_Clarifying_questions()` 함수를 호출하는 코드를 생성함.
- **발견한 문제(취약점·오류·품질)**:
  1. [존재하지 않는 함수 환각 및 침묵하는 실패] AI가 `llm_utils.py`의 실제 시그니처를 확인하지 않고 가상의 함수(`generate_Clarifying_questions`)를 생성했으며, 이를 `hasattr()` 조건문으로 감싸두어 런타임 에러(`AttributeError`)조차 나지 않고 빈 딕셔너리(`{}`)만 반환하는 구조가 됨. 초안 작성 시 AI 출력에 의존해 해당 부분을 미처 걸러내지 못했으나, 팀원과의 코드 리뷰 과정에서 실제 모듈 명세와 대조하며 뒤늦게 결함을 발견함.
  2. [JSON 직렬화 충돌 위험] `detect_duplicate_tags()` 결과에 포함된 `set` 타입을 그대로 `build_prompt_template()`에 넘기면 `TypeError`가 발생할 위험 확인.
- **수정 보완 내역**: `hasattr()` 및 가상 함수 호출을 제거하고, `llm_utils.py`의 실제 3단계 함수(`build_prompt_template` -> `call_llm_request` -> `parse_and_validate_json`)와 DTO 스키마(`QuestionBatch`, `FinalReport`)를 명시적으로 호출하도록 수정함. 또한 `_to_json_safe()` 재귀 어댑터를 추가해 `set`을 정렬된 `list`로 변환 후 전달하도록 보완함.
- **검증 및 판단 메모**: `pytest` 전체 통과(`46 passed, 1 skipped`) 확인 후 `fix:` 커밋 완료. AI가 생성한 연동 코드에서 `hasattr` 같은 방어 구문이 오히려 AI 환각(존재하지 않는 함수 호출)을 숨겨 테스트를 통과시킬 수 있음을 체감했으며, AI 생성 코드일수록 실제 모듈의 함수명과 입출력 계약을 직접 교차 검증해야 함을 배움.

---

## [2026-11-23] 12주차 `st.session_state` 키 정리 표 및 데이터 흐름 구조도 제작·검증 (담당: 강규민)
- **대상 산출물**: `docs/session_state_design.md`, `docs/state_flow_diagram.png` / **관련 커밋**: `7194b51`
- **초기 프롬프트(요지)**: 최신 `app.py`, `backend.py`, `core/llm_utils.py` 코드를 컨텍스트로 제공하고, ① 앱이 사용하는 모든 `st.session_state` 키의 5열 정리 표(키 이름·자료형·초기화 위치·읽는 곳·쓰는 곳), ② 대표 이용 흐름과 13주차 Claude API 교체 지점(점선 박스)이 포함된 Mermaid 데이터 흐름 구조도를 작성하라.
- **AI 생성 결과(요지)**: 10개 상태 키 정리 표와 `0단계→6단계` Mermaid 흐름도 코드를 생성함.
- **발견한 문제(취약점·오류·품질)**:
  1. [마크다운 표 열 밀림 오류] 자료형 열에 `` `dict | None` ``, `` `str | None` ``처럼 파이프(`|`) 기호를 그대로 사용해, VS Code 미리보기에서 5개 행(`audit_result`, `uploaded_file_id`, `detected_encoding`, `chat_state`, `chat_audit_context`)의 열이 한 칸씩 밀리는 렌더링 결함 발견.
  2. [실제 코드 흐름과의 불일치] AI 초안 구조도는 `confirm_chat_restart()` 팝업에서 `'새로 시작하기'` 클릭 시 3단계('진단 시작하기' 대기 화면)로 복귀한다고 표현했으나, 실제 `app.py`는 팝업 내부에서 `backend.initialize_chat()`을 즉시 실행 후 `st.rerun()`하여 4단계(첫 질문 답변 화면)로 직행함. 또한 파일 제거(`uploaded is None` → 0단계 대기)와 다른 파일 직접 교체(`uploaded_file_id` 변경 → 1단계 분석 직행)의 경로가 구분되지 않았음.
  3. [구조도 배치 역전 및 텍스트 잘림] 1차 Mermaid 코드에서는 장거리 역방향 화살표로 인해 `0. 최초 접속`이 중앙에 배치되고 `13주차 LLM 교체 지점`이 최상단으로 밀렸으며, 다크 모드에서 `S6` 박스 글자색 대비가 깨짐. 2차 수정 후 추출한 PNG에서도 1번(`detected_encoding`), 2번(`get_chart_data / get_duplicate_table`), 6번(`(st.stop)`) 박스 하단 텍스트가 잘리는 현상 확인.
- **수정 보완 내역**:
  1. `docs/session_state_design.md`의 5개 행 자료형 표기를 `` `dict` / `None` ``, `` `str` / `None` ``으로 변경해 10개 행 전체 정렬 복구.
  2. `app.py` 실제 분기 기준으로 `5. 진단 기록 초기화 → 4. 사용자 답변/스킵` 직행 화살표로 수정하고, 파일 교체(1단계)와 파일 제거(6단계)를 분리 표현함.
  3. `%%{init: {'flowchart': {'wrappingWidth': 360}}}%%` 지정, 노드별 `fill`/`stroke`/`color` 명시, 박스 텍스트 압축 후 `mermaid.live`에서 PNG를 재추출해 `docs/state_flow_diagram.png`에 반영.
- **검증 및 판단 메모**: 백엔드/UI Python 코드는 수정하지 않아 별도 `pytest` 재실행 대상은 없으며, VS Code 마크다운 미리보기와 추출 PNG 육안 검수로 표 10행 정렬·텍스트 잘림 없음·13주차 교체 지점(`backend.get_ai_reply()`, `core/llm_utils.py: call_llm_request()`) 점선 박스 표기를 최종 확인함. 문서·다이어그램도 AI 출력을 그대로 커밋하면 렌더링 깨짐이나 코드와의 미세 불일치가 숨어들기 때문에, 실제 소스 코드 1:1 대조와 결과물 육안 검증이 필수임을 확인함.