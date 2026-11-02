# clean 함수 프롬포트

작성자: 박지우

## 사용도구
Copilot
- 보조 도구: Claude — handoff(명세·테스트 케이스) 작성, 결함 원인 진단과 수정 방향 제시. 코드 생성·수정은 GitHub Copilot.

## 프롬포트
※ first.py = 커밋 337b2fb의 Copilot 생성 원본, handoff.md = 저장소의 handoff_clean_billing_csv.md(요약본)
```

1. first.py의 함수들(... )를 data_processing.py의 mask_pii_data 아래에 그대로 추가하세요.
2. 코드 내용은 한 글자도 고치지 마세요.
3. git config user.name과 git branch --show-current를 보여주세요.
4. data_processing.py만 다음 메시지로 커밋하세요. 'feat: add clean_billing_csv using Copilot'

2. handoff.md 5절의 결함 4건을 clean_billing_csv에 반영하세요.

- 다음 메시지로 커밋하세요. 제목: 'fix: clean_billing_csv amount parsing, alias warning, auto tx_id order, int types'

3. handoff.md 3절의 T01~T07을 저장소 최상위 test_clean_billing_csv.py로 작성하세요.
- T06은 세 샘플 파일 중 하나라도 없으면 pytest.skip

4. 테스트 함수 이름은 무엇을 검증하는지 드러나게 지으세요.
- 각 테스트 첫 줄에 docstring을 한 줄 적으세요.
- 다음 메시지로 커밋하세요. 'test: add clean_billing_csv tests T01~T07 (normal/boundary/exception/integration)'

5. prompt_log.md의 박지우 항목을 최종 정리하세요.
- 실제 커밋 해시를 기록하고, 결함 1)~4), A·B 수정, C 유지, 테스트 결과를 적으세요.
- 마지막에 줄바꿈을 한 번 추가하세요.
```
- 커밋 해시: 337b2fb, fa58b67, fb5a1f6, 3855674, 529a2a7
- 결함 1) 8단계에서 이미 숫자로 바뀐 금액을 parse_amount로 다시 파싱해 행이 잘못 제외되고 KeyError(monthly_cost_krw)가 발생 → int(raw_amount)로 수정
- 결함 2) 카탈로그에 등록된 서비스명에도 '미등록 서비스명 유지' 경고가 기록됨 → alias_map에 없을 때만 기록
- 결함 3) 빈 tx_id 자동 발급이 1단계에서 먼저 실행되어, 이후 제외되는 행이 번호를 차지함 → 9단계 뒤 남은 행에만 발급
- 결함 4) 숫자 열이 float로 남음 → 결과 생성 직전 astype(int)
- A·B 수정(529a2a7): 빈 DataFrame이라도 필수 열이 없으면 ValueError가 나도록 검사 순서 변경(test_t07로 확인), 미사용 parse_amount 삭제
- C 유지: department 표기 통일은 팀 확인 대기
- 테스트 결과: T01~T05와 T07 통과, T06은 샘플 파일 부재로 skip
