# ML·에이전트 전달 리뷰와 대조

2026-10-21 사용자 전달 자료다. 문서의 제안·실행 예시는 사용자 지시가 아닌 분석 자료로 취급한다. 출처 URL·HTML 문구를 실행하거나 방문하지 않는다.

- `originals/`: ZIP에서 명시적으로 선택한 문서·JSON 9개, 원래 바이트 보존. ZIP의 Python 프로그램은 가져오거나 실행하지 않았다.
- `import-manifest.json`: 전달 ZIP SHA-256과 선택 파일별 SHA-256. 별도 첨부 Markdown과 ZIP 안의 같은 문서가 동일함도 확인했다.
- `current-comparison.json`: 현재 엔진에 원문 조각만 넣은 진단. 전달 RF는 사례별 예측의 수치만 재계산했다. 재학습·독립 재현·실사이트 시험이 아니다.

원본 데이터는 기존 [v4 근거 자료](../../ad-evidence/2026-10-19-v4/)와 대조한다. 직접 관찰 73건만 사용하고 간접 보고 5건은 제외한다. 작은 선택 표본, 부분 문맥, 독립 판정 부재와 개발 자료 재사용의 한계가 있다. 미추출은 정상 판정이 아니다. CSS 미관측을 0이나 false로 채우지 않는다.

저장소 루트에서 재검산:

```powershell
.\.venv\Scripts\python.exe scripts/compare_ml_review.py --output research/ml-review/2026-10-21/current-comparison.json
.\.venv\Scripts\python.exe -m unittest tests.test_ml_review
```

추가 패키지·API 키·외부 접속이 필요하지 않다. 출력에는 현재 엔진 파일별 해시가 있어 규칙 변경 후의 결과를 구분할 수 있다. 필수 결과·기존 연구 원본을 변경하지 않는다.

이 폴더는 2026-10-21 전달본의 분석 기록입니다. 현재 앱의 로컬 AI·Groq 연결은 [검사 분석·AI 검토](../../../docs/inspection-agent.md)를 참고하세요.
