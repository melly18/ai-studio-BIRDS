## 7주차 시그니처 변경 내용
1. 신규 함수 추가: load_saas_catalog()
- 추가 사유: 공급사 카탈로그 JSON 파일을 읽어 필수 키를 검증하고 dict로 반환하는 함수를 추가함.

2. 시그니처 변경: clean_billing_csv()
- 변경 전: (DataFrame) 
- 변경 후: (DataFrame, catalog: dict)
- 변경 사유: 카탈로그 딕셔너리를 입력 받아 service_name을 카탈로그 표준명으로 통일해야 함.

3. 시그니처 변경: detect_duplicate_tags()
- 변경 전: (DataFrame) 
- 변경 후: (DataFrame, catalog: dict)
- 변경 사유: 카탈로그 딕셔너리를 입력 받아 딕셔너리 내 category_tags로 중복 태그 산출해야 함.


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


## [데이터 전처리] clean_billing_csv - 2026-11-02, 작성자: 박지우

### 사용도구
Copilot
- 보조 도구: Claude — handoff(명세·테스트 케이스) 작성, 결함 원인 진단과 수정 방향 제시. 코드 생성·수정은 GitHub Copilot.

### 프롬포트
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



## [data_processing] load_billing_csv() - 2026-11-02, 작성자: 차세연
- 사용 도구: GitHub Copilot Chat
- 프롬프트:
```
당신은 파이썬 백엔드 개발을 돕는 어시스턴트입니다.
SaaS 구독 비용 분석 시스템의 데이터 로딩 계층 중, 결제 내역 CSV를 읽어 원본 DataFrame으로 반환하는 함수를 구현해 주세요.
이 함수는 data_processing.py 파일 상단에 추가됩니다. 같은 파일의 기존 함수(mask_pii_data, parse_date, clean_billing_csv 등)는 절대 수정하지 마세요.

[함수 시그니처 — 변경 금지]
def load_billing_csv(file_path: str) -> pd.DataFrame:

[입력 명세]
file_path: 결제 내역 CSV 경로. 예: "payment_history_raw_100_sample.csv"
파일은 UTF-8 또는 UTF-8 BOM, 쉼표 구분, 첫 줄 헤더입니다. 컬럼 9개:
tx_id, billing_date, service_name, department, billing_cycle,
seat_count, active_users, billing_amount_krw, card_holder_pii

[출력 명세]
- 파일 헤더를 컬럼명으로, 각 행을 한 건으로 가진 pd.DataFrame
- 모든 값은 문자열(str)로 읽을 것. 결측 셀은 NaN이 아닌 빈 문자열 ""
- 컬럼 순서와 이름은 파일 헤더 그대로이고, BOM 문자가 첫 컬럼명에 섞이면 안 됨
- 행 수는 파일의 데이터 행 수와 동일

[예외·경계 방침]
- 파일이 없음: FileNotFoundError (pandas가 발생시키는 것을 그대로 전파, 직접 catch하지 말 것)
- 0바이트 파일 또는 헤더 없음(pandas.errors.EmptyDataError): ValueError 발생, 원인 예외를 `from`으로 연결
- 디코딩 실패(UnicodeDecodeError) 또는 파싱 실패(pandas.errors.ParserError): ValueError 발생, 원인 예외를 `from`으로 연결
- 헤더만 있고 데이터 행이 0개: 예외 없이 컬럼만 있는 빈 DataFrame 반환
- 필수 컬럼 존재 여부는 이 함수에서 검증하지 않음

[제약 조건]
- pandas 사용 가능. pd.read_csv에 encoding="utf-8-sig", dtype=str, keep_default_na=False 를 사용할 것
- 데이터 정제 금지: 컬럼명 변경, 타입 변환, 금액의 쉼표 제거, 날짜 변환, 중복 제거, 정렬, 결측치 처리, PII 마스킹을 하지 말 것 (정제는 다른 함수의 책임)
- 시그니처 변경 금지. 가변 기본값 인자 사용 금지
- 타입 힌트와 docstring 필수. docstring에는 Raises 항목을 포함할 것
- 함수 구현만 출력하고, 테스트 코드는 작성하지 말 것
- 필요한 import가 있으면 함수 코드와 분리해서 따로 알려 주고, 기존 import는 제거하지 말 것

[통과해야 할 테스트]
1. 샘플 "payment_history_raw_100_sample.csv" 로드 시: len(df) == 100, 컬럼이 위 9개와 순서까지 동일, 첫 컬럼명 == "tx_id", 첫 행 billing_amount_krw == "-385000", 7번째 행 billing_amount_krw == "1,656,000" (문자열 그대로), 모든 값이 str
2. 헤더만 있는 CSV: 예외 없이 len(df) == 0 이고 컬럼명이 헤더와 동일
3. 존재하지 않는 경로 "no_such_file.csv": FileNotFoundError
4. 0바이트 파일: ValueError
```
- 생성 코드 위치: 커밋 2ab8303
- 코드 리딩에서 발견한 결함: 없음
- 수정 내역: 커밋 ba46cad
- 테스트 결과: pytest 4 passed

## [data_processing] load_saas_catalog() - 2026-11-02, 작성자: 차세연
- 사용 도구: GitHub Copilot Chat
- 프롬프트:
```
당신은 파이썬 백엔드 개발을 돕는 어시스턴트입니다.
SaaS 구독 비용 분석 시스템의 데이터 로딩 계층 중, 공급사 카탈로그 JSON을 읽어 필수 키를 검증한 뒤 dict로 반환하는 함수를 구현해 주세요.
이 함수는 data_processing.py 파일 상단에 추가됩니다. 같은 파일의 기존 함수(build_alias_map, clean_billing_csv 등)는 절대 수정하지 마세요.

[함수 시그니처 — 변경 금지]
def load_saas_catalog(catalog_path: str) -> dict[str, Any]:

[입력 명세]
catalog_path: 카탈로그 JSON 경로. 예: "saas_catalog_30_sample.json"
JSON 구조(요약):
{
  "meta": {"catalog_version": "v1.0", ...},
  "tools": [
    {"tool_id": "figma", "service_name": "Figma", "aliases": ["피그마", "figma", "FIGMA"],
     "category_tags": ["design", "prototyping"],
     "pricing_tiers": [{"tier_name": "Starter", "price_monthly_per_seat_krw": 0, ...}]},
    ...
  ]
}

[출력 명세]
- 검증을 통과한 JSON 내용을 담은 dict. 원본 그대로이며 키 추가, 값 변환, 정렬을 하지 않음
- 필수 키: 최상위 "meta"(dict), "tools"(list). tools의 각 원소(dict)는 "tool_id", "service_name", "aliases", "category_tags", "pricing_tiers" 를 모두 가져야 함

[예외·경계 방침]
- 파일이 없음: FileNotFoundError (open이 발생시키는 것을 그대로 전파, 직접 catch하지 말 것)
- JSON 문법 오류: ValueError 발생, json.JSONDecodeError를 `from`으로 연결
- 최상위가 dict가 아님: ValueError
- 최상위 필수 키("meta", "tools") 누락: ValueError, 메시지 형식 "필수 키 누락: {키 이름}"
- "meta"가 dict가 아니거나 "tools"가 list가 아님: ValueError
- tools 원소가 dict가 아니거나 필수 키가 누락됨: ValueError, 메시지 형식 "tools[{인덱스}] 필수 키 누락: {키 이름}" (필수 키 순서대로 검사해 처음 발견한 누락 키를 보고)
- tools가 빈 리스트인 경우: 예외 없이 그대로 반환 (허용)
- pricing_tiers 내부 값, aliases 원소 타입 등 그 외 하위 구조는 검증하지 않음

[제약 조건]
- 표준 라이브러리만 사용 (json 사용, pandas 사용 금지 — 이 함수는 pandas와 무관)
- 파일은 encoding="utf-8-sig"로 열 것
- 데이터 변환 금지: 값 정규화, 기본값 채우기, 키 추가를 하지 말 것
- 시그니처 변경 금지. 가변 기본값 인자 사용 금지
- 타입 힌트와 docstring 필수. docstring에는 Raises 항목을 포함할 것
- 함수 구현만 출력하고, 테스트 코드는 작성하지 말 것
- 필요한 import(json, typing.Any 등)가 있으면 함수 코드와 분리해서 따로 알려 주고, 기존 import는 제거하지 말 것

[통과해야 할 테스트]
1. 샘플 "saas_catalog_30_sample.json" 로드 시: len(result["tools"]) == 30, result["meta"]["catalog_version"] == "v1.0", result["tools"][0]["service_name"] == "Figma", 결과가 json.load로 직접 읽은 값과 == 동일
2. {"meta": {}, "tools": []} : 예외 없이 동일한 dict 반환
3. tools[0]에서 "aliases"가 빠진 JSON: ValueError 발생, 메시지에 "aliases" 포함
4. 존재하지 않는 경로: FileNotFoundError
5. 깨진 JSON 문자열 파일: ValueError
```
- 생성 코드 위치: 커밋 9040025
- 코드 리딩에서 발견한 결함:
  1) UnicodeDecodeError는 별도로 처리하지 않아 잘못된 인코딩 파일에서 ValueError가 아닌 UnicodeDecodeError가 발생함. 문서의 예외 명세와 일치시키려면 예외 처리 추가 필요.
- 수정 내역: 커밋 7a96602
- 테스트 결과: pytest 5 passed