## [2026-11-08] load_billing_csv() 리팩터링 (담당: 차세연)
- **대상 모듈**: data_processing.py / **관련 커밋**: ac64aef -> fb16d6f
- **초기 프롬프트(요지)**: load_billing_csv() 함수에 Args:, Returns:, Raises:가 포함된 docstring을 작성하라. 다른 함수는 절대 건들지 않는다. 함수에 파일이 없거나 깨졌을 때 None을 반환하며 에러를 삼키는 코드가 있다면 즉시 FileNotFoundError나 ValueError를 raise하도록 수정하라.
- **AI 생성 결과(요지)**: `load_billing_csv()`에 Args/Returns/Raises를 갖춘 docstring을 추가함. `except FileNotFoundError: raise`를 추가함.
- **발견한 문제(취약점·오류·품질)**: 계약 위반이나 동작 변경은 발견되지 않음. 품질상 `except FileNotFoundError: raise`는 `FileNotFoundError`가 이미 그대로 전파되므로 동작상 불필요한 구문이라고 판단함.
- **수정 보완 내역**: 불필요한 `except FileNotFoundError: raise`를 제거함.
- **검증 및 판단 메모**: `pytest -k "billing" -vv test_data_processing.py` 결과 4/4 PASSED 확인. `FileNotFoundError`는 docstring의 Raises와 단위 테스트로 계약을 보장하므로 코드상 명시적 `raise`는 불필요하다고 판단함.

## [2026-11-08] load_saas_catalog() 리팩터링 (담당: 차세연)
- **대상 모듈**: data_processing.py / **관련 커밋**: fb16d6f -> 12f4f63
- **초기 프롬프트(요지)**: 매직 값 상수화를 적용하도록 요청함. 인코딩 문자열(`"utf-8-sig"`), 최상위 필수 키(`"meta"`, `"tools"`), 도구별 필수 키를 각각 모듈 상단 상수(`CATALOG_ENCODING`, `CATALOG_REQUIRED_KEYS`, `TOOL_REQUIRED_KEYS`)로 분리하되 키의 순서와 값은 기존과 동일하게 유지하도록 지시함. 또한 다른 함수는 절대 건들지 않을 것을 명시함.
- **AI 생성 결과(요지)**: 요청한 상수 3종(`CATALOG_ENCODING`, `CATALOG_REQUIRED_KEYS`, `TOOL_REQUIRED_KEYS`)을 모듈 상단에 분리하고 함수 내부 참조를 상수로 교체함. 키 순서, 예외 메시지, 검증 순서, 시그니처는 원본과 동일하게 유지됨.
- **발견한 문제(취약점·오류·품질)**: 계약 위반이나 동작 변경은 발견되지 않음. 품질상 아쉬운 점으로 1. `CSV_ENCODING`과 `CATALOG_ENCODING`의 값 중복, 2. `tools[i]`가 dict가 아닐 때 "필수 키 누락: tool_id"로 출력되는 부정확한 메시지를 발견함.
- **수정 보완 내역**: 상수화 결과는 그대로 채택. 인코딩 상수는 형식별 독립 변경 가능성을 고려해 분리 유지. 2의 부정확한 메시지는 수정해 이후 `fix:`로 커밋함.
- **검증 및 판단 메모**: `pytest -k "catalog" -vv test_data_processing.py` 결과 12/12 PASSED 확인. 금지 사항을 명시한 제약형 프롬프트로 계약이 유지됨을 확인함.