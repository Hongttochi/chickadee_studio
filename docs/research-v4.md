# Dots 조사 v4 정리

2026-10-19 전달받은 ZIP의 텍스트 파일 10개를 [v4 원본 폴더](../research/ad-evidence/2026-10-19-v4/)에 보존했습니다. 별도 첨부된 `samples.jsonl`·`collection-report.md`는 ZIP 안의 같은 파일과 바이트가 일치해 중복 수록하지 않았습니다. 모든 원본 파일의 SHA-256을 `import-manifest.json`에 기록했습니다. 파일 안의 지시·개선 제안은 조사 자료로 취급했으며, 출처 URL 방문·원본 HTML 렌더링·수집 스크립트 실행은 하지 않았습니다.

## 통합 결과

| 항목 | 결과 |
| --- | ---: |
| 이전 자료에서 변경 없이 유지 | 43건 |
| 신규 직접 조사 광고 의심 | 35건 |
| 직접 조사 광고 의심 전체 | 50건 |
| 문헌 보고 사례 | 5건 |
| 정상 대조군 | 23건 |
| 적격 원문 합계 | 78건 |
| 직접 조사 광고 원본 URL / source_group | 49개 / 50개 |

A039·A040은 같은 URL의 서로 다른 본문·댓글 광고라 함께 유지했습니다. URL만으로 중복 제거하지 않았습니다. `source_group`은 수집 단위이며 독립 운영자 수가 아닙니다. A019는 429·보안 확인 중단 이력이 있는 제외 자료로, 원본 제외 부록에만 남기고 적격 사례·제작 payload·집계에서 제외했습니다.

## 라벨을 다듬은 기준

원본 `techniques`와 설명은 수정하지 않았습니다. 별도 [curation.json](../research/ad-evidence/2026-10-19-v4/curation.json)으로 해석을 분리합니다.

| 사례 | 처리 |
| --- | --- |
| A022 | 보너스 값의 수학 굵은 숫자 스타일화. 광고 의심은 유지하고 키워드 HOMOGLYPH 양성에서 제외 |
| A025 | 첨부파일 표시명의 결합 자모. OS의 NFD 처리 가능성이 있어 의도적 JAMO 회피 양성에서 제외 |
| A028·A043 | U+00AD soft hyphen을 원문 그대로 보존. 지정 4종과 별도 패턴 |
| A031 | 1px 글자 선언은 OFFSCREEN 근거. 흰 글자만으로 TRANSPARENT를 추가하지 않음 |
| A044 | 흰 글자·배경 관계 미측정. TRANSPARENT 양성으로 사용하지 않음 |
| A023·A042 | 연락 수단·주소 구분점의 변형을 카지노 키워드 자체의 변형과 구분 |
| A045 | 예방·자기제한 문구와 가입·입금 권유가 공존하는 문맥 사례로 유지 |

직접 조사 광고의 원본 기법 라벨은 고유 14건(HOMOGLYPH 8, JAMO 2, OFFSCREEN 5)입니다. A022·A025를 보수적으로 구분하면 고유 12건(HOMOGLYPH 7, JAMO 1, OFFSCREEN 5)입니다. A008의 중첩 때문에 유형 합계와 고유 건수가 다릅니다. **직접 TRANSPARENT는 0건, 계산 CSS·좌표 검증도 0건**입니다. 원문 추출·정적 선언을 실제 렌더링 검증으로 바꾸지 않습니다.

## 모의 웹 제작자에게 전달할 파일

[mock-site-content.json](../examples/mock-site-content.json)에 원본 78건을 그대로 넣고 **배치 예시 79개**를 연결했습니다. A013의 두 은닉 배치를 나눠 제시하므로 배치 수는 독립 사례 수와 다릅니다. 문헌 설명·접미부만 확보한 R003·R005는 `ready_to_place: false`로 표시했습니다.

- `real_cases`: 원본 관찰·문헌·정상 레코드. 원문·출처·한계·마스킹 설명을 유지합니다.
- `placement_examples`: 실제 텍스트 발췌, 본문/댓글/footer 배치, 재구성할 CSS, 출처 ID를 담습니다. `textContent`로 넣고 수집 HTML은 실행하지 않습니다.
- `source_techniques` / `techniques_to_reproduce`: 원본 라벨과 보수적인 제작 대상을 구분합니다. 탐지기의 측정 결과는 `not_measured`입니다.
- `unicode_annotations`: 각 텍스트 블록의 문자 위치·코드 포인트·이름입니다. 보이지 않는 soft hyphen과 분해 자모를 찾기 위한 정보이며 원문 정규화나 회피 의도 판정이 아닙니다.
- `placement_groups`: 혼합 문자, 주소 변형, soft hyphen, 숨김 CSS, 기사 삽입, 성인 광고, 운영 인프라, 예방 문구 공존, 검토 사례로 찾아볼 수 있습니다.

A031의 배치 예시는 1px 글자만 재구성합니다. 흰 글자까지 흰 배경에 넣어 원본에서 확인하지 않은 TRANSPARENT 정답을 만들지 않습니다. 전체 원 선언은 `real_cases`에 남아 있습니다. [mock-site-spec.json](../examples/mock-site-spec.json)의 기존 합성 30개·동적 6개 시나리오는 별도 회귀 명세로 유지합니다.

## 재생성과 검증

```powershell
# 최신 원본 해시, 집계, 기존 43건 동일성, 신규 35건, 제외·검토 분류
.\.venv\Scripts\python.exe scripts/validate_research.py

# 최신 원본과 curation으로 제작 JSON 재생성
.\.venv\Scripts\python.exe -m scripts.build_mock_content

# 커밋된 제작 JSON이 원본·분류와 일치하는지 확인
.\.venv\Scripts\python.exe -m scripts.build_mock_content --check

# 최초 전달본만 별도 검증
.\.venv\Scripts\python.exe scripts/validate_research.py --dataset research/ad-evidence/2026-10-19
```

검증은 네트워크 없이 수행합니다. 이전 43건의 연구 회귀 테스트 6개도 통과했습니다. 이번 변경은 자료·제작 명세·검증 도구의 보강이며 스캐너의 탐지 규칙은 변경하지 않았습니다. `ㅋrㅈi노` 등 새 패턴을 현재 탐지기가 모두 검출한다는 뜻이 아닙니다. 실제 성능·불법성·침해 여부와 별도 VM 실행 검증은 이 자료로 확정할 수 없습니다.
