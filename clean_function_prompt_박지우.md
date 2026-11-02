# clean 함수 프롬포트

작성자: 박지우

## 사용도구
Copilot
- 보조 도구: Claude — handoff(명세·테스트 케이스) 작성, 결함 원인 진단과 수정 방향 제시. 코드 생성·수정은 GitHub Copilot.

## 프롬포트
※ first.py = 커밋 337b2fb의 Copilot 생성 원본, handoff.md = 저장소의 handoff_clean_billing_csv.md
```
결제내역 CSV를 정제하는 함수를 data_processing.py에 구현하라.

[함수 시그니처 - 변경 금지]
def clean_billing_csv(df: pd.DataFrame, catalog: dict) -> tuple[pd.DataFrame, list[dict]]:

[입력 명세]
- df: dtype=str로 읽은 결제내역 DataFrame. 필수 열 9개:
  tx_id, billing_date, service_name, department, billing_cycle, seat_count, active_users, billing_amount_krw, card_holder_pii
- catalog: {"tools": [{"service_name": "Figma", "aliases": ["피그마", "figma"]}, ...]}

[출력 명세]
- (result, warnings)
- result: 입력 9개 열 + monthly_cost_krw(int), 총 10열
- warnings: {"tx_id": str, "reason": str, "action": "제외" | "보정"}의 list

[정제 규칙 - 아래 순서대로]
1. tx_id 중복이면 뒤의 행 제외. 빈 tx_id는 TX-AUTO-001부터 자동 발급
2. billing_date: YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD, YYYYMMDD, YYYY년 M월 D일 → YYYY-MM-DD. 실패 시 제외
3. service_name: catalog alias를 표준 이름으로 변환(대소문자 무시). 빈값 제외, 미등록 이름은 유지하고 경고
4. department: 빈값이면 "미상"으로 보정
5. billing_cycle: 월간/monthly/month → 월간, 연간/annual/yearly → 연간. 그 외 제외
6. seat_count: 숫자 변환 실패 또는 0 이하 제외
7. active_users: 빈값·음수는 0, seat_count 초과 시 seat_count로 보정
8. billing_amount_krw: 쉼표·원·₩ 제거 후 정수 변환. 빈값·음수 제외, 0은 유지
9. monthly_cost_krw: 월간은 그대로, 연간은 int(금액 / 12 + 0.5)

[예외 및 경계 방침]
- 빈 DataFrame이면 10열짜리 빈 DataFrame과 []를 반환
- 필수 열이 없으면 ValueError("필수 열 누락: <열이름>")
- 제외·보정이 일어날 때마다 warnings에 기록

[제약 조건]
- pandas와 표준 라이브러리만 사용
- 타입 힌트와 docstring 포함, 가변 기본값 인자 사용 금지
- card_holder_pii는 값을 바꾸지 않고 그대로 전달(마스킹은 mask_pii_data 담당)

[통과해야 할 테스트]
1. 피그마 / 2026/10/05 / "180,000원" → Figma / 2026-10-05 / 180000
2. slack / annual / 1478400 → Slack / 연간 / monthly_cost_krw 123200
3. card_holder_pii 열이 없는 입력 → ValueError
```
- 커밋 해시: 337b2fb, fa58b67, fb5a1f6, 3855674, 529a2a7
- 결함 1) 8단계에서 이미 숫자로 바뀐 금액을 parse_amount로 다시 파싱해 행이 잘못 제외되고 KeyError(monthly_cost_krw)가 발생 → int(raw_amount)로 수정
- 결함 2) 카탈로그에 등록된 서비스명에도 '미등록 서비스명 유지' 경고가 기록됨 → alias_map에 없을 때만 기록
- 결함 3) 빈 tx_id 자동 발급이 1단계에서 먼저 실행되어, 이후 제외되는 행이 번호를 차지함 → 9단계 뒤 남은 행에만 발급
- 결함 4) 숫자 열이 float로 남음 → 결과 생성 직전 astype(int)
- A·B 수정(529a2a7): 빈 DataFrame이라도 필수 열이 없으면 ValueError가 나도록 검사 순서 변경(test_t07로 확인), 미사용 parse_amount 삭제
- C 유지: department 표기 통일은 팀 확인 대기
- 테스트 결과: T01~T07 7 passed (T06 통합 테스트는 로컬 샘플 데이터로 실행, PII 포함 원본은 저장소 미포함 → 저장소만 받으면 T06 skip)
