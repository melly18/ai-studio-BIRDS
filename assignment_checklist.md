## 9주차 과제 최종 제출 체크리스트

### 📍 팀원별 구현 함수 및 파일 위치 안내
| 담당자 | 구현 함수명 | 파일 위치 |
| :--- | :--- | :--- |
| **김서연** | `calculate_seat_leakage()` | `quant_analysis.py` |
| **박지우** | `clean_billing_csv()` | `data_processing.py` |
| **강규민** | `mask_pii_data()` | `data_processing.py` |
| **장형욱** | `detect_duplicate_tags()` | `quant_analysis.py` |
| **차세연** | `load_billing_csv()`, `load_saas_catalog()` | `data_processing.py` |

---

### ✅ 제출 확인용 체크리스트
- [x] 1. 팀원 1인당 최소 1개 함수, 사이클 6단계 완주
- [x] 2. 함수당 테스트 3개 이상(정상·경계·예외), pytest 전체 통과
- [x] 3. prompt_log.md: 프롬프트 원문 + 발견 결함 + 수정 내역 + 커밋 해시 작성 완료
- [x] 4. 함수당 2커밋 이상, 의미 있는 커밋 메시지 작성
- [x] 5. .gitignore(.env, .venv/, __pycache__/) 적용 및 보안 체크리스트 포함
- [x] 6. LLM 의존 기능의 Mock 격리 및 [MOCK] 표시 (이번 주차 구현 함수에는 LLM 기능이 포함되지 않아 해당 없음)
- [x] 7. 저장소에 PII·실데이터·API 키가 없음을 전원 교차 확인