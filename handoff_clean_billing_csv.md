# handoff — clean_billing_csv (요약본)

Copilot에 `#file:handoff.md`로 전달한 문서(164줄)에서 핵심만 남긴 요약본이다. 진행 순서·커밋 계획 등 작업 지시는 생략했고, 절 번호는 프롬프트의 "3절·4절·5절"과 맞췄다.
작성: 박지우 (Claude 보조로 명세·테스트 케이스 정리)

## 2. 명세

```python
def clean_billing_csv(df: pd.DataFrame, catalog: dict) -> tuple[pd.DataFrame, list[dict]]:
```

- 입력: 문자열 DataFrame(필수 9열) + 카탈로그 `{"tools": [{"service_name", "aliases"}]}`
- 출력: 9열 + `monthly_cost_krw` 10열 결과, 경고 리스트 `{"tx_id", "reason", "action": "제외"|"보정"}`
- 정제 규칙: ① 중복 tx_id 제외 → ② 날짜 5형식 → `YYYY-MM-DD` → ③ alias 표준화(미등록은 경고 후 유지) → ④ 빈 부서 `미상` → ⑤ 주기 월간/연간 → ⑥ seat 0 이하 제외 → ⑦ active_users 0~seat로 보정 → ⑧ 금액 기호 제거, 음수 제외 → ⑨ 월비용(연간은 `int(금액/12+0.5)`) → 남은 행의 빈 tx_id에 `TX-AUTO-001`부터 발급
- 예외: 빈 DataFrame은 빈 결과, 필수 열 누락은 `ValueError("필수 열 누락: <열>")`

## 3. 테스트 케이스 (더미 데이터만 사용)

| ID | 구분 | 검증 내용 |
|---|---|---|
| T01 | 정상 | alias·날짜·금액 정제, 연간 1,478,400원 → 월 123,200원 |
| T02 | 경계 | 행 없는 DataFrame → 10열 빈 결과, 경고 없음 |
| T03 | 경계 | 빈 tx_id 자동 발급, 빈 부서 `미상`, active_users 초과 보정, 금액 0 유지 |
| T04 | 예외 | 중복·잘못된 날짜·seat 0·음수 금액·잘못된 주기 행 제외, 경고 5건 |
| T05 | 예외 | 필수 열 누락 → ValueError |
| T06 | 통합 | 샘플 100행 → 80행, 정답지와 일치 (PII 포함 원본은 저장소 미포함, 없으면 skip) |
| T07 | 예외 | 빈 DataFrame이라도 필수 열 누락 → ValueError (A 수정 전에는 실패) |

## 4. 코드 리딩 결과 (A·B 수정, C 유지)

| # | 발견 | 결정 |
|---|---|---|
| A | 빈 입력 검사가 필수 열 검사보다 먼저 실행됨 | 검사 순서 변경 |
| B | `parse_amount()`가 수정 후 호출되지 않음 | 삭제 |
| C | department 표기 미통일(`Data`/`데이터`) | 유지 — 정답지 기준과 일치, 팀 확인 대기 |

## 5. 첫 실행 후 수정한 결함 4건

첫 생성 코드 실행 시 `KeyError: monthly_cost_krw` 발생 → 원인 진단 후 수정.

| # | 결함 | 수정 |
|---|---|---|
| 1 | 숫자로 바뀐 금액을 `parse_amount`로 재파싱 → 전 행 제외 | `int(raw_amount)` |
| 2 | 등록된 서비스명에도 "미등록" 경고 | `alias_map`에 없을 때만 경고 |
| 3 | 자동 tx_id를 검증 전에 발급 → 번호 어긋남 | 9단계 뒤 남은 행에만 발급 |
| 4 | 숫자 열이 float로 남음 | 결과 직전 `astype(int)` |
