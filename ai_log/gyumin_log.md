## [2026-11-07] mask_pii_data() Docstring 위치 오류 수정 및 상수화 리팩터링 (담당: 강규민)
- **대상 모듈**: `data_processing.py` / **관련 커밋**: `v0.9-stable` -> `7128f45`
- **초기 프롬프트(요지)**: `mask_pii_data()`에 데이터 계약(타입 힌트 및 Args/Returns Docstring)을 적용하고, 매직 스트링 상수화 및 Guard Clause 리팩터링을 수행하라.
- **AI 생성 결과(요지)**: 상수 분리 및 Docstring을 추가했으나, 빈 스키마(`df.columns.empty`) 입력 시 `ValueError`를 발생시키는 코드를 함께 생성함.
- **발견한 문제(취약점·오류·품질)**:
  1. [기존 코드 품질 문제] 9주차에 `if df.empty:` 방어 코드를 함수 첫 줄에 삽입하면서 기존 Docstring이 조건문 아래로 밀려나 파이썬 `__doc__`으로 인식되지 않는 문제와 `"card_holder_pii"`, `"[REDACTED]"` 매직 스트링 하드코딩 확인.
  2. [AI 생성 코드 계약 충돌] AI가 임의로 추가한 `df.columns.empty` 예외 발생 로직은 기존 단위 테스트(`test_mask_pii_exception_empty_df`: 빈 DataFrame 반환 계약)를 깨뜨릴 위험이 있음을 코드 리딩으로 발견.
- **수정 보완 내역**: Docstring을 함수 최상단으로 복원하여 입출력 계약을 명시하고, `PII_TARGET_COLUMN`·`PII_MASK_TOKEN` 상수로 추출함. 빈 DataFrame 입력 시 예외 대신 빈 복사본을 조기 반환(Guard Clause)하도록 유지.
- **검증 및 판단 메모**: `pytest -k "mask" -vv` 3/3 PASSED 확인 후 `refactor:` 단독 커밋 완료. AI에게 리팩터링을 맡길 때 기존 경계값 테스트 계약을 임의로 바꾸지 않도록 통제해야 함을 확인.