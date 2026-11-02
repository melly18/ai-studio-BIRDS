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

- 수정 내역: 커밋 eb402c9
- 테스트 결과 : pytest 3 passed


## [데이터 전처리] mask_pii_data - 2026-11-02, 작성자: 강규민
- 사용 도구: GitHub Copilot Chat
- 프롬프트:
당신은 파이썬 백엔드 개발을 돕는 어시스턴트입니다.
SaaS 결제 내역 분석 시스템의 전처리 모듈에 들어갈 함수를 구현해 주세요.

[함수 시그니처 - 변경 금지]
def mask_pii_data(df: pd.DataFrame) -> pd.DataFrame:

[입력 명세]
df: 원본 결제 내역 pandas DataFrame. 'card_holder_pii' 열이 포함될 수 있음.

[출력 명세]
원본 데이터를 훼손하지 않도록 복사본을 만들고, 'card_holder_pii' 열의 모든 값을 "[REDACTED]" 문자열로 일괄 치환한 DataFrame 반환.

[예외·경계 방침]
- 입력 DataFrame에 'card_holder_pii' 열이 없는 경우: 에러를 발생시키지 않고 원본(복사본) 그대로 반환
- 입력 DataFrame이 비어있는(행이 0개) 경우: 빈 DataFrame 반환

[제약 조건]
- pandas 라이브러리만 사용
- 타입 힌트와 docstring 필수
- 원본 DataFrame을 직접 수정하지 말고 반드시 .copy()를 사용할 것

- 생성 코드 위치: 커밋 d884114
- 코드 리딩에서 발견한 결함: 
    1) Copilot이 df.copy()를 사용해 원본 훼손을 방지하고 열 존재 여부(if "card_holder_pii" in masked_df.columns)를 확인하는 등 제약 조건을 훌륭히 준수함.
    2) 하지만 빈 데이터프레임이 들어왔을 때 아래 로직을 불필요하게 타지 않도록 `if df.empty: return df.copy()` 방어 코드를 최상단에 명시적으로 추가하여 안전성을 높이기로 판단함.
- 수정 내역: 커밋 67f656d - 빈 데이터프레임 조기 반환(Early Return) 예외 처리 명시적 추가.
- 테스트 결과: pytest 3 passed

## [quant_analysis] detect_duplicate_tags - 2026-11-02, 작성자: 장형욱
- 사용 도구: GitHub Copilot Chat
- 프롬프트:
```
당신은 파이썬 백엔드 개발을 돕는 어시스턴트입니다.
SaaS 구독 데이터 평가 모듈에 들어갈 함수를 구현해 주세요.
[함수 시그니처 — 변경 금지]
def detect_duplicate_tags(clean_df: pd.DataFrame, catalog: dict) -> list[DuplicatePair]:
[입력 명세]
clean_df: 정제된 결제 csv 데이터프레임. 다음과 같은 구조를 가짐. (이중에 service_name 만 이용  — 변경 금지)
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
catalog: SaaS 마다의 특징을 카테고리화 해 담은 딕셔너리를 모은 딕셔너리. catalog("tools")는 딕셔너리를 모은 리스트이다. 딕셔너리의 키는 다음과 같다 (catalog("tools")로써만 사용  — 변경 금지)
tool_id, service_name, aliases, category_tags, pricing_tiers (이중에 tool_id, service_name, aliases, category_tags 만 이용  — 변경 금지)
"tool_id": "figma", "service_name": "Figma", "aliases": ["피그마", "figma", "FIGMA"], "category_tags": ["design", "prototyping", "whiteboarding"]
[출력 명세]
"duplicate_pairs": DuplicatePair (리스트 안에 리스트[툴1, 툴2, 겹치는 태그])
[예외·경계 방침]
- 겹치는 태그가 없는 경우: 빈 리스트 반환
- 빈 데이터프레임이 입력된 경우, 빈 리스트 반환
- 빈 리스트 가 입력된 경우, 빈 리스트 반환
- 한 태그에 겹치는 툴이 3개 일때: 두개 씩만 비교 [[a, b, c, "category"]]가 아니라 [[a, b, "category"], [b, c, "category"]]
- 두 SaaS 끼리 겹치는 카테고리가 2개이면 [["a", "b", "category1", "category2"]]
[제약 조건]
- 표준 라이브러리와 pandas만 사용
- 타입 힌트와 docstring 필수, 가변 기본값 인자 사용 금지
[통과해야 할 테스트]
1. [{"service_name": "Notion", "seat_count": 10, "active_users": 4, "monthly_cost_krw": 150000},
{"service_name": "Jira", "seat_count": 20, "active_users": 15, "monthly_cost_krw": 200000},
{"service_name": "ClickUp", "seat_count": 5, "active_users": 3, "monthly_cost_krw": 75000}], 
[("tool_id": "notion", "service_name": "Notion", "aliases": ["노션", "notion", "NOTION"], "category_tags": ["documentation", "project_management", "knowledge_management"]), 
("tool_id": "jira", "service_name": "Jira", "aliases": ["지라", "jira", "JIRA"], "category_tags": ["project_management", "task_tracking", "development"]), 
("tool_id": "clickup", "service_name": "ClickUp", "aliases": ["클릭업", "clickup, CLICKUP], "category_tags": ["project_management", "documentation"])]
        ->  [["Notion", "Jira", "project_management"], ["Notion", "ClickUp", "project_management"], ["Jira", "ClickUp", "project_management"]]
2. [{"service_name": "Figma", "seat_count": 10, "active_users": 4, "monthly_cost_krw": 150000},
{"service_name": "Jira", "seat_count": 20, "active_users": 15, "monthly_cost_krw": 200000}, 
[("tool_id": "figma", "service_name": "Figma", "aliases": ["피그마", "figma", "FIGMA"], "category_tags": ["design", "prototyping", "whiteboarding"]), 
("tool_id": "jira", "service_name": "Jira", "aliases": ["지라", "jira", "JIRA"], "category_tags": "project_management", "task_tracking", "development")]
       ->   []
3. [{"service_name": "Figma", "seat_count": 10, "active_users": 4, "monthly_cost_krw": 150000},
{"service_name": "Jira", "seat_count": 20, "active_users": 15, "monthly_cost_krw": 200000},
{"service_name": "ClickUp", "seat_count": 5, "active_users": 3, "monthly_cost_krw": 75000}], 
[("tool_id": "figma", "service_name": "Figma", "aliases": ["피그마", "figma", "FIGMA"], "category_tags": ["design", "prototyping", "whiteboarding"]), 
("tool_id": "jira", "service_name": "Jira", "aliases": ["지라", "jira", "JIRA"], "category_tags": "project_management", "task_tracking", "development"), 
("tool_id": "clickup", "service_name": "ClickUp", "aliases": ["클릭업", "clickup, CLICKUP], "category_tags": ["project_management", "task_tracking", "documentation"])]
        ->  [["Jira", "ClickUp", "project_management", "task_tracking"]]
4. [{}], 
[("tool_id": "figma", "service_name": "Figma", "aliases": ["피그마", "figma", "FIGMA"], "category_tags": ["design", "prototyping", "whiteboarding"])]
        ->  []
5. [{"service_name": "Notion", "seat_count": 10, "active_users": 4, "monthly_cost_krw": 150000},
{"service_name": "Jira", "seat_count": 20, "active_users": 15, "monthly_cost_krw": 200000},
{"service_name": "ClickUp", "seat_count": 5, "active_users": 3, "monthly_cost_krw": 75000}], 
[]
        ->  []
```
- 생성 코드 위치: 커밋 7a3f67b
- 코드 리딩에서 발견한 결함:  

    1) 입력값중 하나인 catalog가 리스트에서 딕셔너리로 바뀌어
    catalog_tools 변수를 새로 만들어 기존의 리스트 역할을 대체하게 수정

- 수정 내역: 커밋 588c4b0
- 테스트 결과 : pytest 8 passed (이 함수에 관련된건 5건)