# handoff — clean_billing_csv (9주차 6단계 사이클 ④~⑥)

Copilot Chat에 이 파일을 `#file:handoff.md`로 첨부해서 전달한다.

## 0. Copilot에게 — 먼저 읽을 규칙

- **함수 시그니처 변경 금지.** 다른 팀원 코드가 이 시그니처로 호출한다.
- **`data_processing.py` 본문은 임의로 고치지 말 것.** 결함을 발견하면 목록으로만 보고하고, 수정은 사용자가 승인한 항목만 한다.
- **새 라이브러리 import 금지.** 허용: 표준 라이브러리, `pandas`, `pytest`.
- **보안: 원본 CSV를 열거나 첨부하거나 붙여넣지 말 것.** `payment_history_raw_100_sample.csv`의 `card_holder_pii` 열에는 실명처럼 보이는 이름·이메일·카드번호가 들어 있다. 테스트 데이터는 아래 3절의 더미 값만 사용한다. 통합 테스트는 파일을 디스크에서 읽기만 한다.
- 이 파일에 없는 기능은 추가하지 말 것.

## 1. 역할·맥락

SaaS 비용 진단 서비스의 Step1(CSV 정제) 모듈이다. 결제내역 CSV(DataFrame)를 받아 더티 데이터를 정제한다. 정제 결과는 다음 단계로 넘어간다.

- 다음 함수: `mask_pii_data`가 `card_holder_pii`를 `[REDACTED]`로 바꾼다.
- 그 뒤: 좌석 누수 탐지, 중복 태그 탐지, 비용 매트릭스 단계.

## 2. 명세

### 함수 시그니처 (변경 금지)

```python
def clean_billing_csv(df: pd.DataFrame, catalog: dict) -> tuple[pd.DataFrame, list[dict]]:
```

### 입력

**`df`**: 모든 값이 문자열로 읽힌 DataFrame(`dtype=str`). 필수 열은 9개다.

`tx_id, billing_date, service_name, department, billing_cycle, seat_count, active_users, billing_amount_krw, card_holder_pii`

**`catalog`**: `{"tools": [{"service_name": "Figma", "aliases": ["피그마", "figma"]}, ...]}`

### 출력

**`(result, warnings)`**

- `result`: 위 9개 열 + `monthly_cost_krw`, 총 10열이다.
- int 열: `seat_count`, `active_users`, `billing_amount_krw`, `monthly_cost_krw`
- `warnings`: `{"tx_id": str, "reason": str, "action": "제외" | "보정"}`의 리스트

### 정제 규칙 (코드 1~9단계 순서)

| 단계 | 대상 | 처리 |
|---|---|---|
| 1 | tx_id | 중복이면 뒤의 행을 **제외**한다. |
| 2 | billing_date | 5가지 형식(`-`, `/`, `.`, 8자리, `YYYY년 M월 D일`)을 `YYYY-MM-DD`로 통일한다. 실패하면 **제외**. |
| 3 | service_name | 카탈로그의 alias를 표준 이름으로 바꾼다(대소문자 무시). 빈값이면 **제외**. 카탈로그에 없는 이름은 유지하고 "미등록" 경고를 남긴다. |
| 4 | department | 빈값이면 `미상`으로 **보정**한다. |
| 5 | billing_cycle | 월간/monthly/month는 `월간`, 연간/annual/yearly는 `연간`으로 바꾼다. 그 외는 **제외**. |
| 6 | seat_count | 숫자 변환에 실패하거나 0 이하면 **제외**한다. |
| 7 | active_users | 빈값·음수는 0으로, seat_count보다 크면 seat_count로 **보정**한다. |
| 8 | billing_amount_krw | 쉼표·`원`·`₩`를 제거한다. 빈값이나 음수면 **제외**. 0은 유지한다. |
| 9 | monthly_cost_krw | 월간은 그대로 쓴다. 연간은 `int(금액/12 + 0.5)`. |
| 마지막 | tx_id | 빈 tx_id는 1~9단계를 모두 통과한 행에만 `TX-AUTO-001`부터 순서대로 발급한다. |

### 예외·경계 방침

- 빈 DataFrame이 들어오면 10열짜리 빈 DataFrame과 `[]`를 반환한다.
- 행이 있는데 필수 열이 빠졌으면 `ValueError("필수 열 누락: <열이름>")`을 발생시킨다.

## 3. 테스트 케이스 (확정됨 — 이 값 그대로 작성)

- 파일: 저장소 최상위의 `test_clean_billing_csv.py` (새 파일). 기존 `test_data_processing.py`는 다른 팀원 담당이라 수정 금지.
- 함수 1개 = 케이스 1개
- 아래 기대값은 실제 실행으로 확인한 값이다.

공통 더미 카탈로그:

```python
CATALOG = {"tools": [
    {"service_name": "Figma", "aliases": ["피그마", "figma"]},
    {"service_name": "Slack", "aliases": ["슬랙", "slack"]},
]}
```

| ID | 구분 | 입력 (더미, `card_holder_pii="더미"`) | 기대 결과 |
|---|---|---|---|
| T01 | 정상 | 1행: `TX-1, 2026/10/05, 피그마, 디자인, 월간, 10, 6, "180,000원"`<br>2행: `TX-2, 20261006, slack, 영업, annual, 7, 4, 1478400` | 2행이 남는다.<br>1행: `2026-10-05`, `Figma`, 금액 180000, 월비용 180000<br>2행: `2026-10-06`, `Slack`, `연간`, 금액 1478400, 월비용 **123200**<br>숫자 4열은 모두 int64 |
| T02 | 경계 | 9개 열만 있고 행이 없는 DataFrame | 10열 빈 DataFrame, warnings `[]` |
| T03 | 경계 | 1행: `"", 2026-10-07, Figma, "", 월간, 5, 9, 0` | tx_id `TX-AUTO-001`, department `미상`, active_users **5**, 금액 0, 월비용 0이 유지된다.<br>warnings 3개: 미상 보정, 초과 보정, 자동 발급 |
| T04 | 예외 | 6행.<br>정상 `TX-1`, 같은 `TX-1` 중복, `TX-3`(날짜 `abc`), `TX-4`(seat 0), `TX-5`(금액 -500), `TX-6`(cycle `weekly`) | 결과는 `TX-1` 1행이다.<br>"제외" 경고 5개: 중복 / 잘못된 billing_date / 잘못된 billing_cycle / seat_count <= 0 / 금액 음수 |
| T05 | 예외 | 행 1개, `card_holder_pii` 열 없음 | `pytest.raises(ValueError, match="필수 열 누락")` |
| T07 | 예외 | 행이 없고 `card_holder_pii` 열도 없는 DataFrame | `pytest.raises(ValueError, match="필수 열 누락")`<br>4절 A를 수정하기 전에는 실패하는 것이 정상이다. |
| T06 | 통합 | 테스트 파일과 같은 폴더의 `payment_history_raw_100_sample.csv`(`dtype=str`), `saas_catalog_30_sample.json`, `정답지_정제후_결제내역.csv`.<br>세 파일 중 하나라도 없으면 `pytest.skip` (PII가 포함된 원본은 저장소에 올리지 않음) | 80행이 남는다.<br>정답지(`정제후_결제내역.csv`)와 `card_holder_pii`를 뺀 8개 값 열이 모두 일치한다.<br>tx_id 순서도 일치한다. |

T06은 정답지에 `monthly_cost_krw` 열이 없으므로 정답지에 있는 열만 비교한다. 비교할 때는 양쪽 다 `astype(str)`로 맞춘다.

## 4. 코드 리딩 체크리스트 (9주차) — 보고만, 수정은 승인 후

`data_processing.py`를 아래 6개 항목으로 검토하고 결과를 표로 보고할 것.

1. 시그니처 대조
2. 경계 추적 (빈 입력, 0, 음수, 누락 키)
3. 예외 방침 대조
4. 위험 관용구 (가변 기본값, 광범위한 except, 하드코딩)
5. 의존성
6. 설명 가능성

사람이 이미 발견한 점검 포인트다. 각 항목의 처리 방침은 이미 결정되어 있다.

| # | 발견 | 결정 | 할 일 |
|---|---|---|---|
| A | 빈 입력 검사가 필수 열 검사보다 먼저 실행된다. 그래서 "열도 빠지고 행도 없는" 입력은 ValueError 없이 빈 결과를 반환한다. | **수정** | 필수 열 검사를 빈 입력 검사보다 앞으로 옮긴다. 순서만 바꾸고 다른 줄은 건드리지 않는다. |
| B | `parse_amount()`는 8단계 수정 이후 어디에서도 호출되지 않는 죽은 코드다. | **수정** | `parse_amount` 함수 정의를 삭제한다. |
| C | `department` 표기가 통일되지 않는다(`Data`/`데이터`, `기획팀`/`기획`). | **유지** | 코드는 수정하지 않는다. 정답지도 통일하지 않았으므로 현재 코드는 명세와 일치한다. 통일 규칙은 팀이 정할 사항이라 `prompt_log.md`에 "팀 확인 대기"로 기록한다. |

A를 고친 뒤에는 3절의 T07이 통과해야 한다. A를 고쳐도 T02(9개 열이 다 있는 빈 DataFrame)는 지금처럼 빈 결과를 반환해야 한다.

## 5. 이미 반영된 수정

Copilot이 처음 생성한 코드를 실행했을 때 KeyError가 발생했다. 원인을 진단해서 아래 4건을 수정했다. 코드에서 `# FIXED:` 주석으로 표시되어 있다.

| # | 결함 | 증상 | 수정 |
|---|---|---|---|
| 1 | 8단계에서 `to_numeric` 결과(float)를 `parse_amount`에 다시 넣음 | `int("672000.0")`에서 ValueError → 모든 행이 제외됨 → `KeyError: monthly_cost_krw` | `int(raw_amount)`로 변경 |
| 2 | "미등록 서비스명" 경고 조건 오류 | 카탈로그에 있는 이름에도 경고 76건 발생 | `not in alias_map`일 때만 기록 |
| 3 | 빈 tx_id 자동 발급을 1단계에서 수행 | 나중에 제외되는 행이 번호를 차지해 번호가 어긋남 | 9단계 이후, 검증을 통과한 행에만 발급 |
| 4 | 숫자 열이 float로 남음 | `211200.0` | 4개 열을 `astype(int)`로 변환 |

## 6. Copilot이 할 일 (순서대로)

1. 4절 체크리스트 결과를 보고한다. 이 단계에서는 코드를 수정하지 않는다.
2. 3절 T01~T07을 그대로 `test_clean_billing_csv.py`로 작성한다.
3. `pytest -v`를 실행한다. 이 시점에는 T07만 실패해야 한다. 실패를 먼저 확인하는 단계다.
4. 사용자가 승인하면 4절 A와 B만 수정한다. 수정한 줄에는 `# FIXED:` 주석을 단다.
5. `pytest -v`를 다시 실행하고 전체 통과 출력 전문을 보여준다. 실패하면 원인만 보고한다.
6. 아래 `prompt_log.md` 항목 초안을 채운다. `<...>`는 사용자가 채울 칸이므로 비워 둔다.

```markdown
## [모듈] clean_billing_csv — <날짜>, 작성자: 박지우
- 사용 도구: GitHub Copilot Chat (코드 생성, 테스트 작성, 결함 2건 수정)
- 프롬프트: <Copilot에 보낸 원문 전체>
- 생성 코드 위치: 커밋 <해시> (Copilot 생성 원본)
- 코드 리딩에서 발견한 결함:
  1) 금액 이중 파싱으로 전 행 제외 → KeyError
  2) 미등록 경고 오발생 76건
  3) 자동 tx_id 발급 시점 오류
  4) 숫자 열 float 잔존
  5) 빈 입력이 필수 열 검사를 건너뜀 → 검사 순서 변경 (Copilot 수정)
  6) 사용하지 않는 parse_amount → 삭제 (Copilot 수정)
  7) department 표기 미통일 → 유지, 팀 확인 대기 (정답지 기준 명세와 일치)
- 수정 내역: 커밋 <해시>
- 테스트 결과: pytest <N> passed
```

## 7. 커밋 계획 (사용자가 직접 실행)

- **커밋 1:** Copilot 생성 원본 `data_processing.py` (수정 전)
- **커밋 2:** `fix: clean_billing_csv amount parsing, alias warning, auto tx_id order, int types` (`# FIXED` 4건)
- **커밋 3:** `test: add clean_billing_csv tests (normal/boundary/exception/integration)`
- **커밋 4:** `fix: check required columns before empty-input return, remove unused parse_amount` + `prompt_log.md`

모든 커밋의 author는 박지우 본인 계정이어야 한다. 커밋 전에는 `.gitignore`에 `.env`, `.venv/`, `__pycache__/`가 들어 있는지 확인한다. 원본 CSV(PII 포함)는 저장소에 올려도 되는지 팀과 먼저 확인한다.

## 8. 완료 기준

- [ ] 시그니처가 명세와 글자 단위로 일치한다.
- [ ] T01~T07 pytest가 전부 통과한다.
- [ ] A·B는 수정되었고 C는 유지 사유가 기록되어 있다.
- [ ] `prompt_log.md`에 수정 7건(4건 + A·B + C 유지)이 기록되어 있다.
- [ ] 프롬프트, 테스트, 커밋 어디에도 실제 PII가 없다.
