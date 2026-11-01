## [quant_analysis] calculate_seat_leakage - 2026-11-01, 작성자: 김서연
- 사용 도구: GitHub Copilot Chat
- 프롬프트:
```
구독 툴별 유휴 좌석과 낭비된 금액을 계산하는 함수를 quant_analysis.py에 구현하라.

[함수 시그니처 - 변경 금지]
def calculate_seat_leakage(clean_df: pd.DataFrame) -> seat_leakage: list[SeatLeakage]:

[입력 명세]
clean_df: 정제된 결제 csv. 다음과 같은 구조를 가짐.
|컬럼명|데이터 타입|설명|예시|
|---|---|---|---|
|tx_id|str|거래 ID|TX-0001|
|billing_date|date|결제일|2026-10-05|
|service_name|str|툴 이름|Figma|
|department|str|결제 부서|디자인|
|billing_cycle|str|결제 주기|월간|
|seat_count|int|결제 좌석 수|10|
|active_users|int|실사용자 수|4|
|billing_amount_krw|int|1회 결제 금액|150000|
|card_holder_pii|str|개인정보, [REDACTED]|[REDACTED]|
|monthly_cost_krw|int|월간 환산 결제 금액|150000|

[출력 명세]
seat_leakage: 툴 이름과 계산된 유휴 좌석, 낭비 금액을 SeatLeakage의 list로 반환한다.
SeatLeakage(dataclass)은 다음으로 구성됨.
service_name(str);툴 이름, inactive_seats(int);유휴 좌석, wasted_spend(int);월간 낭비 금액

[요구사항]
1. 유휴 좌석 수를 계산한다.
2. 월간 좌석당 단가를 계산한다.
3. 월간 낭비되는 금액을 계산한다.

[예외 및 경계 방침]
- 동일한 툴에 대한 계산은 모두 종합되어야 함. 즉, 한 툴에 대해 여러 결제 건이 존재한다면 각 계산 결과를 하나의 SeatLeakage로 합산해야 함.
- 실사용자가 결제 좌석보다 많은 경우, ValueError 발생
- 결제 좌석 수가 0인 경우, ValueError 발생
- 음수 데이터가 입력된 경우, ValueError 발생
- 필수 컬럼(service_name, seat_count, active_users, monthly_cost_krw)이 하나 이상 누락된 경우, KeyError를 발생
- 빈 데이터프레임이 입력된 경우, 빈 리스트 반환
- 결측치가 포함된 경우, ValueError 발생

[제약 조건]
- pandas와 표준 라이브러리만 사용
- 타입 힌트와 docstring 필수, 가변 기본값 인자 사용 금지

[통과해야 할 테스트]
1. [{"service_name": "Figma", "seat_count": 10, "active_users": 4, "monthly_cost_krw": 150000},
{"service_name": "Jira", "seat_count": 20, "active_users": 15, "monthly_cost_krw": 200000},
{"service_name": "Figma", "seat_count": 5, "active_users": 3, "monthly_cost_krw": 75000}]
        ->  [SeatLeakage("Figma", 8, 120000), SeatLeakage("Jira", 5, 50000)]
2. [{"service_name": "Figma", "seat_count": 10, "active_users": 10, "monthly_cost_krw": 150000}]
       ->   [SeatLeakage("Figma", 0, 0)]
3. seat_count = 5, active_users = 7 포함 입력 -> ValueError 발생
```
- 생성 코드 위치: 커밋 afacc85
- 코드 리딩에서 발견한 결함:  

    1) 입력이 DataFrame이 아닐 때 예외 발생이 없음  
    명세에는 작성하지 않았지만 필수적인 예외라고 생각하여 TypeError를 일으키도록 수정.
    2) 결측치를 확인할 때, 모든 컬럼을 확인함  
    계산에 필요한 필수 컬럼에만 결측치가 없으면 된다고 생각하여 수정.
    3) 낭비 금액을 계산할 때 불필요한 연산이 보임  
    낭비 금액과 유휴 좌석 컬럼을 동시에 생성하다 보니 inactive_seats를 활용하지 못해 중복되는 계산이 발생.  
    이에 생성을 두 개로 나누어 유휴 좌석 컬럼을 활용할 수 있도록 수정.

    추가적으로 팀원들의 함수 리딩을 돕기 위해 간단한 주석을 작성함.

- 수정 내역: 커밋 d4e5f6a
- 테스트 결과 : pytest 3 passed