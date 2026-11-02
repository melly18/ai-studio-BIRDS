# clean 함수 프롬포트

작성자: 박지우

## 사용도구
Copilot

## 프롬포트
구독 툴별 유휴 좌석 수와 월간 낭비 금액을 계산하는 함수를 quant_analysis.py에 구현해줘.

다음 조건을 정확히 지켜서 작성해라.

0. 작업 의도와 설계 rationale
- 이 함수는 정제된 결제 데이터에서 서비스별로 유휴 좌석 수와 손실 비용을 집계하는 데 사용한다.
- 원본 결제 CSV에는 monthly_cost_krw가 직접 존재하지 않을 수 있다. 그러나 유휴 좌석 낭비 계산에는 월간 기준 비용이 반드시 필요하다.
- 따라서 정제 단계에서 monthly_cost_krw를 표준화된 계산용 값으로 추가한다. 이 값은 "원본 CSV의 실제 컬럼"이라기보다 "분석을 위해 만든 정규화된 월간 비용 컬럼"으로 취급한다.
- 이렇게 해야 연간/월간 결제주기, 할인 여부, 다른 billing_cycle가 섞여 있어도 wasted_spend를 동일 기준으로 계산할 수 있다.
- 같은 서비스라도 여러 건으로 나뉘어 있더라도 한 서비스의 월간 기준 비용과 좌석 수를 종합해 계산해야 한다.

1. 파일과 함수 구조
- quant_analysis.py에 아래 구조를 포함한다.
- dataclass SeatLeakage를 정의한다.
- 함수 시그니처는 아래와 같이 반드시 유지한다.

from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class SeatLeakage:
    service_name: str
    inactive_seats: int
    wasted_spend: int


def calculate_seat_leakage(clean_df: pd.DataFrame) -> list[SeatLeakage]:
    ...

2. 입력 데이터
clean_df는 정제된 결제 CSV를 DataFrame으로 읽은 값이다. 다음 컬럼들을 포함한다.
- tx_id
- billing_date
- service_name
- department
- billing_cycle
- seat_count
- active_users
- billing_amount_krw
- card_holder_pii
- monthly_cost_krw

이 중 필수 컬럼은 아래 4개다.
- service_name
- seat_count
- active_users
- monthly_cost_krw

주의:
- monthly_cost_krw는 원래 raw 데이터에 직접 존재하지 않을 수도 있지만, 유휴 좌석 낭비 계산에는 월간 기준 단가가 반드시 필요하다.
- 정제 과정에서 이 값을 표준화해서 추가해야 한다.
- 이 컬럼은 결과 계산을 위해 존재하는 계산용 값이며, raw 데이터의 결제 주기 차이를 보정하는 역할을 한다.

3. 계산 로직
- 각 서비스별로 유휴 좌석 수를 계산한다.
- inactive_seats = seat_count - active_users
- 동일한 서비스가 여러 건으로 나뉘어 있으면 모두 합산한다.
- wasted_spend는 다음으로 계산한다.
  - 월간 좌석당 단가 = monthly_cost_krw / seat_count
  - wasted_spend = monthly_cost_krw * inactive_seats / seat_count
  - 소수점이 발생하면 반올림 후 int로 변환한다.
- 결과는 서비스가 처음 등장한 순서대로 리스트로 반환한다.
- 예를 들어, Figma가 여러 행으로 나뉘어 있어도 최종적으로 한 서비스로 묶어 계산한다.

4. 예외 처리
- 입력이 pandas DataFrame이 아니면 TypeError를 발생시켜라.
- 필수 컬럼이 누락되면 KeyError를 발생시켜라.
- 빈 DataFrame이면 []를 반환한다.
- 필수 컬럼에 결측치가 있으면 ValueError를 발생시켜라.
- seat_count, active_users, monthly_cost_krw에 음수가 있으면 ValueError를 발생시켜라.
- seat_count가 0이면 ValueError를 발생시켜라.
- active_users > seat_count이면 ValueError를 발생시켜라.

5. 기대 결과
예시 입력:
[
    {"service_name": "Figma", "seat_count": 10, "active_users": 4, "monthly_cost_krw": 150000},
    {"service_name": "Jira", "seat_count": 20, "active_users": 15, "monthly_cost_krw": 200000},
    {"service_name": "Figma", "seat_count": 5, "active_users": 3, "monthly_cost_krw": 75000}
]

기대 결과:
[
    SeatLeakage("Figma", 8, 120000),
    SeatLeakage("Jira", 5, 50000)
]

또 다른 예시:
[
    {"service_name": "Figma", "seat_count": 10, "active_users": 10, "monthly_cost_krw": 150000}
]

기대 결과:
[
    SeatLeakage("Figma", 0, 0)
]

마지막으로, active_users가 seat_count보다 큰 입력이 들어오면 ValueError가 발생해야 한다.

6. 코드 품질
- 타입 힌트와 docstring을 반드시 포함한다.
- pandas와 표준 라이브러리만 사용한다.
- 불필요한 복잡한 로직은 피하고, 함수는 직관적이고 짧게 작성한다.
- 가변 기본값 인자는 사용하지 않는다.
- 함수는 짧고 명확하게 작성한다.
- 출력 리스트는 서비스가 처음 등장한 순서대로 유지한다.

7. 테스트 기준
아래 조건을 통과하는 테스트도 함께 생각해라.
- 정상 흐름
- 빈 DataFrame
- 0 좌석
- active_users > seat_count
- 필수 컬럼 누락
- 음수 값
- 결측치 값

8. 최종 체크 포인트
- 함수는 `list[SeatLeakage]`를 반환해야 한다.
- `SeatLeakage` 객체는 `frozen=True` 형태로 정의해야 한다.
- 계산 로직은 월간 기준으로 통일되도록 구성해야 한다.
- monthly_cost_krw는 raw 데이터의 실제 값뿐 아니라 정제 단계에서 보정된 계산용 값으로 사용될 수 있음을 명확히 반영해야 한다.
- 코드와 테스트는 모두 직관적으로 이해할 수 있어야 한다.

이 조건들을 모두 만족하는 구현을 생성하라.
