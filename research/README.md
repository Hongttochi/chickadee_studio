# 연구 자료

전달받은 조사 원본과 재현용 데이터를 보관합니다. 앱 사용법은 [데스크톱 가이드](../docs/desktop.md), 현재 AI 연결은 [검사 분석·AI 검토](../docs/inspection-agent.md)를 참고하세요.

| 자료 | 내용 |
| --- | --- |
| [초기 광고 조사](ad-evidence/2026-10-19/) | 최초 전달 자료·출처·원본 해시 |
| [v4 광고 조사](ad-evidence/2026-10-19-v4/) | 후속 수집 자료와 분류·제외 기록 |
| [ML 전달 리뷰](ml-review/2026-10-21/) | 제공된 평가 자료와 코드 대조 결과 |

원본 파일과 `import-manifest.json`은 출처·무결성 확인을 위해 유지합니다. 같은 사례가 여러 전달본에 포함될 수 있으므로 건수를 합산하지 않습니다. 과거 연구 결과를 현재 앱의 성능 수치로 사용하지 않습니다.

```powershell
.\.venv\Scripts\python.exe scripts/validate_research.py
.\.venv\Scripts\python.exe -m unittest tests.test_research tests.test_ml_review
```

로컬 학습 데이터·가중치·작업 로그는 Git에서 제외된 `training-local/`에서 관리합니다.
