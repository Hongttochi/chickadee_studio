치카비봇 ML + 에이전트 개선 검토·오프라인 시험
기준: 2026-10-21 KST

이번 산출물은 1차 검토 및 자체 프로토타입 시험이다. 원본 저장소의 실행·변경·push, 참고 저장소의 실행, 실제 LLM/브라우저 에이전트 시험은 수행하지 않았다.

핵심 제안: 기존 규칙으로 관측된 은닉 기법을 판정하고, ML로 광고 문맥의 검토 우선순위를 보조하며, 근거가 부족한 후보만 제한된 에이전트가 조사한다. 광고 의심과 피싱, 법적 불법성은 별도 판단이다.


# 치카비봇 ML + 에이전트 참고 구현 비교

검토 기준: 2026-10-21 KST. 공개 GitHub API로 커밋·트리·소스·테스트를 읽었으며, 참고 저장소의 코드나 테스트를 실행하지 않았다. 아래는 정적 검토와 제안이며 실제 성능 실험 결과가 아니다. 별도 오프라인 실험 보고서와 구분해야 한다.

## 1. 결론

치카비봇의 기존 규칙 엔진을 없애고 URL 피싱 모델로 바꾸는 방향은 맞지 않는다. **광고 문맥을 판단하는 ML + 관측 가능한 은닉 기법을 판정하는 규칙 + 부족한 근거만 조사하는 제한된 에이전트**로 분리하는 것이 적합하다.

- 광고 의심 여부, HOMOGLYPH/JAMO/TRANSPARENT/OFFSCREEN 여부, 피싱 여부는 서로 다른 출력이다. 합쳐서 단일 악성 점수로 만들지 않는다.
- 정상 공공 도메인의 게시판에도 광고가 들어갈 수 있다. 정상 HTTPS/공공 도메인만으로 해당 DOM 요소를 정상 처리해서는 안 된다.
- 반대로 광고성 문구라는 이유만으로 피싱이나 법적 불법성을 확정하지 않는다.
- 에이전트는 자유 웹 탐색자가 아니라 근거 조사자다. 같은 사이트의 허용된 읽기 동작과 이미 수집한 DOM·스타일 증거를 이용해 확인/보류를 결정한다.

## 2. 고정 소스 버전

| 자료 | 확인한 커밋 / 기준 | 역할 |
|---|---|---|
| ad-sentinel | `6294a4f9d6c2997abcb81b32b9f519459a33f48b` | Python/Playwright 규칙·가중 점수 기반 공공사이트 광고 탐지 |
| detector | `bb16354960c04f268a9a66d7b1e45ab543ba2b34` | Java/Playwright, 은닉 root와 의미 게이트 기반 탐지 |
| chickadee_Bot | `ff6ba7746930fd71d298775d8b1521cf490652a9` | Python 규칙 엔진 + 로컬 도구 계약, 현재 LLM 미연결 |
| Velog | 2024-03-03 게시 글, 현재 공개 본문 | 11개 URL/웹 특징 RF 입문 실험 |

커밋 고정 링크:
- [ad-sentinel](https://github.com/woojin052500-arch/ad-sentinel/tree/6294a4f9d6c2997abcb81b32b9f519459a33f48b)
- [detector](https://github.com/OhSuBin13/detector/tree/bb16354960c04f268a9a66d7b1e45ab543ba2b34)
- [치카비봇](https://github.com/orqan137/chickadee_Bot/tree/ff6ba7746930fd71d298775d8b1521cf490652a9)

## 3. 참고 자료에서 실제로 확인한 것

### 3.1 Velog: RF는 학습 방식 참고, 현장 기능 그대로 이식 금지

[원문](https://velog.io/@2jinu/random-forest%EC%9D%84-%EC%82%AC%EC%9A%A9%ED%95%9C-%ED%94%BC%EC%8B%B1-%EC%82%AC%EC%9D%B4%ED%8A%B8-%EC%8B%9D%EB%B3%84)

게시된 코드는 11개 특징, 80/20 무작위 분할, 100개 트리 RF와 SHAP을 사용한다. 분할 seed·도메인 그룹·시간 분리는 표시되지 않았다. 작성자도 예제 피싱을 정상으로 판정한 한계를 명시했다. 운영 추출기는 네트워크 접속을 수행하므로 실행하지 않았다.

정적 검토상 favicon 판정은 hostname 문자열 포함 여부라서 다른 도메인을 오인할 수 있고, `//` 상대 URL도 내부로 처리할 수 있다. 서브도메인은 Public Suffix를 고려하지 않은 점 개수다. 단축주소 처리 실패를 악성값으로 돌리는 점도 결측과 악성을 섞는다. 인증서 설명과 구현도 일치하지 않는다. 따라서 **RF 비교군과 설명 가능성 아이디어만 참고**하고, 사이트 피싱 라벨을 광고 요소 라벨로 재사용하지 않는다.

### 3.2 AD Sentinel: 여러 근거와 미검사 영역을 보여 주는 설계

실제로 확인한 파일:
- [detector.py](https://github.com/woojin052500-arch/ad-sentinel/blob/6294a4f9d6c2997abcb81b32b9f519459a33f48b/ad_sentinel/detector/detector.py)
- [variants.py](https://github.com/woojin052500-arch/ad-sentinel/blob/6294a4f9d6c2997abcb81b32b9f519459a33f48b/ad_sentinel/detector/variants.py)
- [test_detector.py](https://github.com/woojin052500-arch/ad-sentinel/blob/6294a4f9d6c2997abcb81b32b9f519459a33f48b/tests/test_detector.py)
- [gate.py](https://github.com/woojin052500-arch/ad-sentinel/blob/6294a4f9d6c2997abcb81b32b9f519459a33f48b/ad_sentinel/crawler/gate.py)

구현은 학습 모델이 아니라 가산 점수다. 기본값은 high 5, suspect 4, 최소 근거 2개이며, 키워드·숨김·외부 링크·의심 도메인·연락처·파라미터 반사 등을 조합한다. UTS #39 confusables, 스타일 문자, 기호 삽입, 초성, 자판 변환 등을 지원하고 변형 방식에 따라 가중치를 낮춘다. 동일 위치/부모·자식 및 페이지 간 중복을 묶는다.

특히 가져올 설계는 `unchecked`다. 못 연 페이지, 시간 초과 iframe, 제한으로 일부만 검사한 요소, robots 제외를 **정상/문제 없음이 아닌 미검사**로 반환한다. 실제 mois_sample JSON을 이용한 정상 사이트 회귀 테스트도 존재한다.

주의: 게이트 클릭은 위험 단어와 외부 링크 등을 검사하지만 단어 목록만으로 안전을 보장할 수 없다. 상대·프로토콜 상대 URL, onclick, 새 창, 리다이렉트는 네트워크 정책이 최종 차단해야 한다. 클로킹·반사형 탐지 아이디어는 유용하나 현재 사용자 범위에서 외부 목적지 방문이나 입력 주입을 자동 허용하는 근거가 아니다.

### 3.3 detector: 숨김과 광고 의도를 따로 판정, 위치까지 채점

실제로 확인한 파일:
- [HiddenDetector.java](https://github.com/OhSuBin13/detector/blob/bb16354960c04f268a9a66d7b1e45ab543ba2b34/src/main/java/addetector/detect/HiddenDetector.java)
- [AdSignals.java](https://github.com/OhSuBin13/detector/blob/bb16354960c04f268a9a66d7b1e45ab543ba2b34/src/main/java/addetector/detect/AdSignals.java)
- [collector.js](https://github.com/OhSuBin13/detector/blob/bb16354960c04f268a9a66d7b1e45ab543ba2b34/src/main/resources/js/collector.js)
- [HiddenDetectorTest.java](https://github.com/OhSuBin13/detector/blob/bb16354960c04f268a9a66d7b1e45ab543ba2b34/src/test/java/addetector/detect/HiddenDetectorTest.java)
- [Evaluate.java](https://github.com/OhSuBin13/detector/blob/bb16354960c04f268a9a66d7b1e45ab543ba2b34/src/main/java/addetector/eval/Evaluate.java)
- [judge.js](https://github.com/OhSuBin13/detector/blob/bb16354960c04f268a9a66d7b1e45ab543ba2b34/src/main/resources/js/judge.js)

가장 가까운 숨김 root 단위로 문구를 모으고, 메뉴 및 긴 저밀도 숨김 글을 거른 뒤 광고 의미 게이트를 적용한다. 표본에서 얻은 길이 200/키워드 밀도10% 경계는 보편 법칙이 아니므로 치카비봇에 하드코딩하기보다 특징·회귀 사례로 참고할 만하다. 연락처가 있을 때 문맥 차단을 완화하는 코드가 있으므로 보도문에 인용된 URL·전화번호라는 대조군이 필요하다.

평가기는 모의 페이지의 정답 요소와 `location + technique`를 대조한다. iframe 경로, selector가 정확히 한 요소를 가리키는지, 같은 요소 중복, 놓친 요소, 금지 URL 요청을 함께 검사한다. 단순 문장 분류 정확도보다 치카비봇 목적에 가깝다.

[eval/history.csv](https://github.com/OhSuBin13/detector/blob/bb16354960c04f268a9a66d7b1e45ab543ba2b34/eval/history.csv)의 마지막 기록은 모의23페이지에서 핵심75건 TP75/FP1/FN0이다. 이는 저자 저장소의 기록이며 이번 재현 결과나 실사이트 성능이 아니다. `--strict`는 `knownFp`를 허용하므로 strict 통과를 오탐0으로 해석하면 안 된다.

### 3.4 현재 치카비봇은 어제보다 발전해 있음

[현재 detection.py](https://github.com/orqan137/chickadee_Bot/blob/ff6ba7746930fd71d298775d8b1521cf490652a9/chickadee/detection.py)는 조건부 r→ㅏ, Greek COM 문맥, 광고 권유 신호, 보도·예방·제품 문맥 제외, 원문 span을 구현한다. [extract.js](https://github.com/orqan137/chickadee_Bot/blob/ff6ba7746930fd71d298775d8b1521cf490652a9/chickadee/extract.js)는 스크롤 좌표, 고정 위치 구분, 조상 opacity·작은 clip, 배경 이미지 불확실성을 고려한다. 따라서 어제 지적된 항목을 미수정 결함으로 다시 보고하면 안 된다.

[candidates.py](https://github.com/orqan137/chickadee_Bot/blob/ff6ba7746930fd71d298775d8b1521cf490652a9/chickadee/candidates.py)는 단순 광고 후보와 필수 은닉기법 결과를 이미 분리한다. [tests/test_research.py](https://github.com/orqan137/chickadee_Bot/blob/ff6ba7746930fd71d298775d8b1521cf490652a9/tests/test_research.py)에 정상 문맥·혼합 한글·CSS·스크롤 회귀 테스트가 존재한다. 존재 확인이지 실행 성공 확인은 아니다.

[tools.py](https://github.com/orqan137/chickadee_Bot/blob/ff6ba7746930fd71d298775d8b1521cf490652a9/chickadee/tools.py)는 이미 JSON Schema 기반 stdio 도구 계약을 갖는다. scan 상태/결과/이벤트, 실행 제어, review.update 등이 있으며 `agent_connected=False`다. [agent-extension.md](https://github.com/orqan137/chickadee_Bot/blob/ff6ba7746930fd71d298775d8b1521cf490652a9/docs/agent-extension.md)도 원격 LLM 미연결을 명시한다.

## 4. 권장 개선 구조

1. 기존 수집기와 기법 판정은 유지한다. 입력은 원문, 문맥 경계, 요소/프레임 위치, 관측 CSS, 결측 이유다.
2. ML은 광고 문맥 후보의 우선순위와 정상/의심/보류를 담당한다. 첫 비교군은 고정 규칙, char n-gram 선형 모델, 작은 RF다. URL 피싱 RF를 그대로 이식하지 않는다.
3. 문장·DOM 특성은 키워드 수/밀도, 권유·예방·인용 문맥, 정규화 변화량, 문자 스크립트 혼합, 링크와 키워드 거리, 역할/메뉴/접근성, 텍스트 길이 등이다. CSS는 관측값과 결측 마스크를 별도로 둔다.
4. 보류/상충 사례만 에이전트로 보낸다. 허용 행동은 같은 content_scope 주변 문장 읽기, 조상 스타일/좌표 조회, selector 재검증, 허용된 동일사이트 읽기 컨트롤의 새 관측 요청이다. 현재 계약에 없는 미세 조회 도구는 명시적으로 추가해야 한다.
5. 에이전트 출력은 `assessment`, `evidence_ids`, `missing_evidence`, `recommended_next_action`, `abstain_reason`으로 제한한다. 사람이 확정하지 않은 ML 결과를 학습 정답으로 자동 환류하지 않는다. 원문과 기존 필수 결과는 불변으로 둔다.

## 5. 공정한 시험 설계

### 즉시 가능한 오프라인 진단
- 원문 텍스트만으로 고정 baseline과 ML을 비교. 동일/유사 문구·도메인·source_group 연결요소는 같은 fold로 묶는다.
- fit/특징 선택/threshold 조정은 train 내부만 사용한다. 작은 표본이면 seed별 분산과 fold별 클래스 수를 함께 낸다.
- 실관측/간접보고/합성 데이터를 분리한다. 현재 광고 의심 라벨은 최종 법적 불법성/피싱 라벨이 아니다.
- CSS를 관측하지 않은 샘플로 은닉기법 recall을 계산하지 않는다. 수집 데이터의 원래 주석·기법·판정 이유를 입력 특징으로 사용하지 않는다.
- accuracy만이 아니라 TP/FP/FN, precision, recall, PR-AUC, 보류율, coverage를 보고한다. 모델 확률의 보정 여부는 별도 검증한다.

### 격리 환경에서 추후 필요한 실행 시험
- 현 버전 규칙 엔진 A / 규칙+ML B / 규칙+ML+고정 추가조회 C / 규칙+ML+에이전트 D를 같은 샘플·같은 추가조회 예산으로 비교한다.
- 에이전트 이득은 D-B뿐 아니라 D-C로 측정한다. 단순히 더 많이 읽어서 좋아진 것을 에이전트 추론 성능이라 부르지 않는다.
- 합성 대조군: 정상 숨김 메뉴, sr-only 접근성, 긴 FAQ, 보도문 속 인용 URL, 일반 스크롤, 고정 요소, 이미지 배경, 조상 opacity, 교차 태그 문자, 중첩 iframe, 긴 키워드 도배.
- 결과는 후보 분류, 기법별 다중라벨, selector 유효성/유일성, frame 경로, 근거 span 정확성, 중복률, 미검사율을 각각 채점한다.
- 운영 안전: 외부 목적지/다운로드/폼 제출0, 429·인증서 경고·CAPTCHA에서 중단, 프롬프트 인젝션0, 최대 단계·시간·토큰 준수, 잘못된 run_id·미등록 도구 거부.
- 장황한 보고서보다 불확실성을 정확히 보존했는지, 사람이 검토할 건수를 얼마나 줄였는지와 누락 손실을 함께 비교한다.

## 6. 라이선스와 실행 경계

두 참고 저장소의 전체 트리에서 프로젝트 자체 코드에 대한 명시적 LICENSE는 확인하지 못했다. ad-sentinel의 THIRD_PARTY_NOTICES.txt와 detector의 LICENSE-THIRD-PARTY.md는 의존성 고지이며 프로젝트 자체 재사용 허락으로 간주할 수 없다. GitHub 메타데이터도 각각 license null / Other(NOASSERTION)이다. 치카비봇은 자체 [고지 문서](https://github.com/orqan137/chickadee_Bot/blob/ff6ba7746930fd71d298775d8b1521cf490652a9/docs/third-party-notices.md)에 전체 라이선스 미정이라고 명시한다.

따라서 구조·검증 아이디어를 참고한 독립 구현을 우선하고, 타 프로젝트 코드/fixtures를 복사·배포하려면 별도 라이선스 확인이 필요하다. Unicode confusables는 독립 공식 라이선스가 있으나 해당 고지 유지가 필요하다.

이번 단계에서는 공개 소스 읽기와 자체 코드의 오프라인 데이터 진단만 가능하다. 내려받은 제3자 코드, Gradle wrapper, pytest import, 설치/빌드/모델 역직렬화 실행은 별도 실행 승인 및 격리 확인 전 하지 않는다. 기존 사용자 제한에 따라 실제 피싱·광고 외부 목적지를 방문하지 않는다. 동적 탐지·전체 봇 실행 성능과 Windows 배포 성공은 이번 정적 검토로 증명되지 않는다.


# 치카비봇 ML + 증거 수집 에이전트: 오프라인 진단

작성일: 2026-10-21 KST. 기존 코드나 운영 봇을 실행·수정하지 않았다. 아래 수치는 새로 작성한 비교용 프로토타입의 결과이며, 현재 Chickadee의 전체 규칙 엔진 성능이 아니다.

## 먼저 결론

작은 표본에서 RF는 정상 오탐을 줄이는 대신 광고 의심 누락을 늘렸다. 따라서 “RF로 교체하면 개선된다”는 결론은 불가능하다. ML은 검토 우선순위 신호로, 에이전트는 부족한 근거를 수집하는 역할로 분리하는 것이 다음 실험 가설이다. 이 자료는 광고 의심 조각 모음이지 피싱 데이터셋이 아니다. 자격증명 탈취, 사칭, 악성 사이트 또는 불법성의 판정 성능은 전혀 측정하지 않았다.

## 데이터 감사

- 기존 v4의 직접 관찰 73건: ad_suspected 50, normal 23. 간접 보고 5건은 모든 학습·평가에서 제외.
- 일부 evidence_text는 “CΟΜ” 3글자, “야동” 2글자 또는 일반적인 이벤트 문구뿐이다. 수집자가 주변 문맥으로 붙인 라벨을 조각만으로 복원할 수 없는 사례가 있다.
- 라벨은 수집 당시 판단이다. 독립 판정자 합의와 대표성 검증이 없다. 무작위 표집이 아니며 keyword/topic 기반 수집 편향과 인위적 정상 대조군이 존재한다.
- source_group만 사용하면 다른 이름의 같은 기관/사이트 사례가 양쪽에 섞일 수 있다. 따라서 도메인 근사값, 동일 source_group, 정규화된 동일 텍스트, 길이20 이상에서 SequenceMatcher 유사도0.9 이상의 문구를 모두 연결하여 63개 그룹으로 묶었다.
- 도메인 근사는 ac.kr/co.kr/go.kr/or.kr/ne.kr 및 ac.id/co.id/go.id를 뒤3라벨로, 그외 뒤2라벨로 묶는다. PSL 구현이 아니다. cafe24.com 등 호스팅 tenant까지 한 그룹으로 묶는 보수적 과병합이 있다. 같은 캠페인의 다른 도메인·문구는 놓칠 수 있다.
- 정상과 광고 의심이 섞인 aks.ac.kr/gachon.ac.kr도 같은 그룹이다. 매 fold 학습/평가 그룹 교집합이 비어 있음을 assert했다.
- 모델 입력은 evidence_text만 사용. URL, 제목, source_group, label_reason, techniques, limitations, CSS, observation_status 등은 모델 특성이 아니다. 그룹 지정과 보고를 위한 metadata만 사용한다.
- “[광고 목적지 삭제]” 같은 수집자 삽입 마커는 ML 입력에서 제거했다. HTML/JS, 원본 저장소 코드, 모델 pickle을 실행하거나 불러오지 않았다.

## 방법

고정 seed 20261021, 5-fold StratifiedGroupKFold. 표본마다 자신이 포함되지 않은 학습 집합에서 만든 예측 하나를 취합했다. TF-IDF vocabulary도 학습 fold에서만 생성했다. 하이퍼파라미터 탐색은 하지 않았다.

1. majority: 학습 fold의 다수 클래스. 클래스 불균형의 착시를 확인하기 위한 대조군.
2. keyword_raw: 자체 고정 키워드가 하나라도 포함되면 의심. 현재 봇을 재현하지 않은 약한 대조군.
3. keyword_nfkc: NFKC, 소문자화, Unicode Cf 제거, 공백 정리 후 같은 키워드.
4. rf_char_tfidf: 위 정규화 텍스트의 문자2~4gram TF-IDF(최대5000개)와 RandomForest(300trees, min_samples_leaf2, class_weight balanced).

키워드 목록은 metrics.json/코드에 고정되어 있다. 데이터의 주제를 알고 구성했으므로 완전히 손대지 않은 테스트셋이 아니다. 현재 Chickadee는 주변 홍보 문맥, 정상 기사/제품 예외, 혼합문자 복원과 원문 위치 등을 사용하므로 이 간단한 키워드 모델보다 훨씬 복잡하다.

## 결과

| 자체 프로토타입 | 정상 오탐 /23 | 의심 누락 /50 | 의심 precision | 의심 recall | 균형정확도 |
|---|---:|---:|---:|---:|---:|
| 다수 클래스 |23|0|68.5%|100.0%|50.0%|
| 단순 키워드 |12|13|75.5%|74.0%|60.9%|
| 정규화 키워드 |12|10|76.9%|80.0%|63.9%|
| 문자 TF-IDF + RF |6|17|84.6%|66.0%|70.0%|

RF는 균형정확도와 precision이 높지만 recall은 낮다. 전체 accuracy는 다수 클래스와 RF가 모두68.5%이므로 accuracy 하나로 해석하면 부적절하다. 작은 편향 표본의 탐색적 비교이며 통계적 우월성·실서비스 일반화·정확도 보장은 하지 않는다. 오탐·누락별 ID와 예측은 predictions.jsonl, fold별 지표와 클래스 수는 metrics.json에 있다.

## 에이전트와 관련하여 실제로 시험한 범위

자체 작성한 결정론적 정책 함수에 12개 합성 조건을 넣어 모두 통과했다. 이것은 요구사항을 테스트 코드로 옮긴 것일 뿐, LLM의 판단력이나 브라우저 에이전트 성공률을 입증하지 않는다. LLM/API 호출, 실제 브라우저 상호작용, 외부 사이트 조회를 하지 않았다.

정책 예시: CSS 미확인→hidden unknown 유지; style 선언만 있음→computed style/box 요청 계획; 숨겨진 정상 제품/예방 문구→정상 문맥 검토; 짧은 혼합문자→동일 요소 문맥 요청; 간접보고→직접확인 전 보류; 페이지의 지시문→무시. 모든 분기는 확정판정 대신 abstain으로 끝난다. 테스트는 정확히 이런 보수적인 계약만 확인한다. 요청 계획은 어떤 동작도 실행하지 않는다.

## 다음에 필요한 검증

- 광고 판별, 은닉/우회 탐지, 위치 식별, 피싱 판별을 별도 목표·라벨로 분리.
- 문구 조각 외에 동일 요소/부모 문맥, 실제 링크 목적지, 원문 offset, DOM/frame chain, computed style, bounding box, 수집 시각을 하나의 증거 패킷으로 확보. 미확인은 0/false가 아니라 null/unknown 유지.
- 동일 페이지·캠페인·도메인과 유사 문구를 묶은 학습/검증 분리, 이후 다른 시기/기관으로 외부 평가. 검토 중 발견한 테스트 사례로 임계값을 맞추지 말 것.
- 정상 교육자료, 경고 기사, 브랜드·상품명, 접근성 메뉴, 실제 홍보 유도 문맥을 독립 판정자가 다시 라벨링.
- ML 점수를 위험 확률로 그대로 읽지 말고 보정 여부·보류 구간·오탐 비용 검증. ML과 규칙이 충돌하거나 근거가 부족하면 근거 재수집 또는 사람 검토로 전달.
- 실제 에이전트 시험은 별도 통제된 fixture 페이지에서 수행하고, 입력 지시문 무시, 개인정보 입력/제출 금지, 허용된 읽기 동작, 시간/요청 예산, 중단·보류 조건을 평가.

## 재현

이미 설치된 신뢰 가능한 Python/numpy/scikit-learn 환경에서 실행한다. 새 패키지 설치가 필요하지 않았으며 원본 저장소 코드를 실행하지 않았다.

```
python offline_diagnostic.py --source bundled_inputs
python test_evidence_policy.py
```

첫 명령은 metrics.json과 predictions.jsonl을 다시 쓴다. bundled_inputs는 원본에서 ID, 라벨, 그룹 구분에 필요한 출처와 텍스트만 추린 비실행 스냅샷이며 원본 HTML/JS를 포함하지 않는다. 출처 URL은 provenance 문자열일 뿐 코드가 방문하지 않는다. 기본 --source는 상위 폴더의 기존 chickadee-evidence-v4를 가리킨다. 원본 파일 SHA256은 provenance.json에 보존했다. 스냅샷으로 재현하면 metrics.json의 입력 파일 SHA256만 달라지며 예측/지표는 같아야 한다.

## 파일

- offline_diagnostic.py: 자체 작성한 감사·그룹 분할·비교 코드
- metrics.json: 버전, 그룹 연결 이유, 짧은 입력 목록, fold별/전체 지표, 제한
- predictions.jsonl: 사례별 원문 조각/정규화 조각/실제 라벨/모델 예측/fold/그룹
- bundled_inputs/: 재현용 최소 텍스트 스냅샷, 간접보고5개는 실행 시 제외
- provenance.json: 원본 입력 파일 해시 및 스냅샷 범위
- test_evidence_policy.py, policy_test_results.json: 결정론적 합성 정책 계약시험

외부 데이터 업로드·라이브 의심 사이트 방문·기존 파일 수정·실제 봇 코드 실행·자동 신고/차단은 하지 않았다.
