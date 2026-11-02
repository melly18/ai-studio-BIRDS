# [data_processing] clean_billing_csv - 2026-11-02, 작성자: 박지우
1. - [v] 제출물에 실존 인물의 실명·전화번호·이메일 등 PII가 포함되지 않았다(테스트는 더미 데이터, 샘플 원본 CSV는 저장소 미포함).
2. - [v] 외부 AI(챗봇·API)에 기업 기밀·타인 코드·PII를 입력하지 않았다.
3. - [v] 외부 데이터 사용 시 출처·라이선스를 확인하고 PII 열을 비식별 처리했다(과제 제공 샘플, PII 열은 mask_pii_data로 [REDACTED] 처리).
4. - [v] API 키·비밀번호가 소스코드에 하드코딩되어 있지 않다.
5. - [v] .env 파일이 .gitignore에 등록되어 있고, git ls-files 확인 결과 추적되지 않는다.
6. - [v] 커밋 히스토리에 키가 노출된 적이 없다.
7. - [v] 키·비밀 값을 print/log/스크린샷으로 전체 출력하지 않았다.
8. - [v] AI 사용 내역(프롬프트·채택·수정)을 과제 규정에 따라 기록·첨부했다(clean_function_prompt_박지우.md, handoff_clean_billing_csv.md).
**이 함수는 LLM 기능을 포함하지 않음**
