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