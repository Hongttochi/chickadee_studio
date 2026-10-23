"""Review candidates without asserting illegality or inventing an evasion code."""
import re
import unicodedata
from functools import lru_cache

from .detection import DEFAULT_RULES, analyze, skeleton, is_editorial_context, text_ranges, merge_analyses

CATEGORY_LABELS = {"GAMBLING": "도박 홍보 의심", "ADULT": "성인 콘텐츠 홍보 의심",
                   "LOAN": "대출 모집 의심", "INVESTMENT": "투자 모집 의심", "COMMERCIAL": "구매·추천 유도",
                   "AI_CONTEXT": "AI 광고 문맥", "IMAGE_REVIEW": "이미지 검토 필요",
                   "ACCOUNT_TRADE": "계좌·통장 거래 의심", "DRUGS": "마약 거래·홍보 의심"}


@lru_cache(maxsize=512)
def analyze_candidate(text, rules=DEFAULT_RULES, breaks=()):
    if breaks:
        grouped = {}
        for start, end in text_ranges(text, breaks):
            for hit in analyze_candidate(text[start:end], rules):
                category = hit['category']
                if category not in grouped:
                    grouped[category] = {**hit, 'matched_keywords':[], 'reasons':[], '_analyses':[]}
                combined = grouped[category]
                combined['matched_keywords'].extend(k for k in hit['matched_keywords'] if k not in combined['matched_keywords'])
                combined['reasons'].extend(r for r in hit['reasons'] if r not in combined['reasons'])
                if 'analysis' in hit:
                    combined['_analyses'].append((start, hit['analysis']))
        for hit in grouped.values():
            parts = hit.pop('_analyses')
            if parts:
                hit['analysis'] = merge_analyses(parts, rules)
        return list(grouped.values())
    if is_editorial_context(text):
        return []
    result = []
    base = analyze(text, rules)
    if base["is_advertisement"]:
        keywords = list(dict.fromkeys(m["keyword"] for m in base["matches"]))
        adult = any(k in {"야동", "porn", "성인방송", "성인사이트", "성인물"} for k in keywords)
        result.append({"category": "ADULT" if adult else "GAMBLING", "matched_keywords": keywords,
                       "reasons": ["광고 주제어와 근접한 권유 문맥"], "analysis": base})
    # Other domains remain review candidates, never mandatory technique findings.
    compact = skeleton(text)
    linked = bool(re.search(r"https?://[^\s<>]+", text, re.I))
    def contains(term):
        return skeleton(term) in compact
    prevention = bool(re.search(r'예방|피해.{0,12}(?:주의|신고|방지)|하지\s*마|금지|처벌|신고하세요|빌려주면', text))
    # A product can advertise prevention benefits. Reserve the broad prevention
    # exclusion for harmful solicitation, not ordinary commercial offers.
    commercial_warning = bool(re.search(r'피해.{0,12}(?:주의|신고|방지)|하지\s*마|금지|처벌|신고하세요|'
                                        r'(?:과장|허위)\s*광고.{0,12}(?:주의|예방|피해)', text))
    # Photo scores cannot replace explicit transaction evidence in OCR text.
    # Common words used as slang need corroboration, rather than matching alone.
    normalized = unicodedata.normalize('NFKC', text).casefold()
    drug_pattern = re.compile(r'마약|대마초|필로폰|코카인|케타민|엑스터시|메스암페타민|'
                              r'(?<![a-z])(?:lsd|dmt|mdma|weed|cocaine|methamphetamine)(?![a-z])')
    transaction_pattern = re.compile(r'판매|팝니다|삽니다|구매|구입|주문|직구|딜러')
    drug_notice = bool(re.search(r'치료|의료|처방|연구|논문|보도|단속|수사|검거|중독.{0,10}상담', normalized))
    slang = [term for term in ('아이스', '작대기', '떨') if contains(term)]
    drug_hits, trade_hits = [], []
    # Keep the topic and transaction close; navigation elsewhere on the page
    # must not turn a drug-prevention article into a sales candidate.
    for match in drug_pattern.finditer(normalized):
        nearby = normalized[max(0, match.start()-80):match.end()+80]
        if match[0] == 'weed' and re.search(r'정원|잡초|제초|잔디|gardening|herbicide|weed\s*(?:killer|remov)', nearby):
            continue
        trades = [m[0] for m in transaction_pattern.finditer(nearby)]
        if not trades and '문의' in nearby and len(set(drug_pattern.findall(nearby))) >= 2:
            trades = ['문의']
        if trades:
            drug_hits.append(match[0]); trade_hits.extend(trades)
    if not drug_hits and (len(slang) >= 2 or contains('아이스딜러')):
        for term in slang:
            if re.search(re.escape(term) + r'\s*(?:판매|팝니다|딜러)', normalized):
                drug_hits = slang; trade_hits = ['판매·모집 문구']; break
    if drug_hits and not prevention and not drug_notice:
        result.append({'category': 'DRUGS', 'matched_keywords': list(dict.fromkeys(drug_hits + trade_hits)),
                       'reasons': ['약물명 또는 복수의 관련 은어와 거래·연락 유도 문맥이 함께 나타납니다.']})
    account = [term for term in ('계좌', '통장') if contains(term)]
    rental = [term for term in ('임대', '대여', '매입', '삽니다', '빌리고', '양도') if contains(term)]
    recruiting = bool(re.search(r'등록해|등록비|접수시|모집|드립니다|드리며|수익|\d+\s*만\s*원', text))
    if account and rental and recruiting and not prevention:
        result.append({'category': 'ACCOUNT_TRADE', 'matched_keywords': account + rental,
                       'reasons': ['계좌·통장 거래와 대가 지급·모집 문맥이 함께 나타납니다.']})
    for category, topics, signals in (
        ("LOAN", ("대출", "대부"), ("상담 신청", "즉시 입금", "신용 확인 없이", "당일 대출")),
        ("INVESTMENT", ("투자",), ("수익 보장", "원금 보장", "고수익", "투자 모집")),
        ("COMMERCIAL", ("상품 주문", "추천 수당"), ("특별 할인", "추천 수당", "구매 혜택")),
    ):
        hits = [t for t in topics if contains(t)]
        selling = [t for t in signals if contains(t)]
        if hits and selling and not (commercial_warning if category == 'COMMERCIAL' else prevention):
            result.append({"category": category, "matched_keywords": hits,
                           "reasons": ["모집·구매 권유 문맥" + (" · 외부 주소 포함" if linked else ""), *selling]})
    # OCR often preserves only the offer itself, without a product name or URL.
    # Keep ordinary sales offers as review candidates independently of the
    # harmful-solicitation models; they do not establish a legal violation.
    offer_text = re.sub(r'\s+', '', unicodedata.normalize('NFKC', text)).casefold()
    investment_topic = re.search(r'종목추천(?:서비스)?|급등주|(?:주식|투자)(?:강의|교육|정보|서비스)', offer_text)
    investment_offer = re.search(r'무료(?:체험|(?:투자|주식)?(?:강의|교육))|체험.{0,12}제공', offer_text)
    investment_cta = re.search(r'사이트방문|가입하기|신청|참여하기|문의|상담', offer_text)
    if (investment_topic and investment_offer and investment_cta and not prevention
            and not any(hit['category'] == 'INVESTMENT' for hit in result)):
        result.append({'category': 'INVESTMENT',
                       'matched_keywords': [investment_topic[0], investment_offer[0], investment_cta[0]],
                       'reasons': ['투자 서비스·교육 주제와 무료 체험·제공 혜택 및 가입·방문 유도가 함께 나타납니다.']})
    # Short loan banners may omit the word 'loan'. Require all three clues
    # together instead of treating any amount or same-day service as lending.
    loan_topic = re.search(r'소액(?:전문|급전|자금)|급전', offer_text)
    loan_amount = re.search(r'\d+(?:\.\d+)?(?:만원|만|원)?[-~∼–]\d+(?:\.\d+)?(?:만원|만|원)?', offer_text)
    loan_service = re.search(r'당일(?:진행|입금|지급|송금)|즉시(?:입금|지급)|방문없이|무방문|비대면', offer_text)
    if loan_topic and loan_amount and loan_service and not prevention and not any(h['category'] == 'LOAN' for h in result):
        result.append({'category': 'LOAN',
                       'matched_keywords': [loan_topic[0], loan_amount[0], loan_service[0]],
                       'reasons': ['소액 자금 모집 표현·금액 범위·신속 또는 비대면 처리 문맥이 함께 나타납니다.']})
    offers, reasons = [], []
    event = re.search(r'이벤트|프로모션|기획전|특가', offer_text)
    event_benefit = re.search(r'할인|혜택|쿠폰|사은품|증정|무료체험|'
                              r'(?<![\d.])\d+(?:,\d{3})*(?:\.\d+)?(?:만|천)?원', offer_text)
    if event and event_benefit and not any(h['category'] in {'INVESTMENT', 'LOAN'} for h in result):
        offers.extend([event[0], event_benefit[0]])
        reasons.append('이벤트·프로모션 안내에 이용 가격·할인·혜택을 함께 제시합니다.')
    price = re.search(r'(?<![\d.])\d+(?:,\d{3})*(?:\.\d+)?(?:만|천)?원', offer_text)
    checkout = re.search(r'쿠폰적용가|장바구니|구매하기|주문하기|상품상세|원산지|해외구매', offer_text)
    coupon_offer = re.search(r'(?:즉시|추가|특별).{0,6}쿠폰|'
                             r'(?:할인|활인)쿠폰.{0,10}(?:받|제공|증정|지급|다운)', offer_text)
    service = re.search(r'라식|라섹|안과|치과|피부과|성형외과|수술|시술|진단비|검진', offer_text)
    price_offer = re.search(r'최저가|정상가|우대가|특별가|무료제공|무료증정', offer_text)
    rate = re.search(r'(?<![\d.])(\d{1,3}(?:\.\d+)?)%', offer_text)
    if price and checkout:
        offers.extend([price[0], checkout[0]])
        reasons.append('상품 구매·주문 화면 표현과 판매 가격이 함께 나타납니다.')
    if coupon_offer:
        offers.append(coupon_offer[0])
        reasons.append('추가·즉시 할인 쿠폰을 제공하는 홍보 문구')
    if service and price and (price_offer or (rate and 0 < float(rate[1]) <= 100)):
        offers.extend([service[0], price[0], price_offer[0] if price_offer else rate[0]])
        reasons.append('의료·미용 서비스와 특별 가격·혜택 또는 할인율을 함께 제시합니다.')
    sleep_claim = re.search(r'수면질향상|깊은수면|불면증|숙면|꿀잠', offer_text)
    pack_size = re.search(r'\d+(?:캡슐|탭|정|병)(?:/병)?', offer_text)
    loyalty = re.search(r'적립|포인트지급', offer_text)
    if sleep_claim and (pack_size or loyalty):
        offers.extend([sleep_claim[0], (pack_size or loyalty)[0]])
        reasons.append('수면 관련 효과를 강조하며 상품 포장 수량 또는 구매 적립 혜택을 제시합니다.')
    specialist = re.search(r'(?:치료|시술|수술|청소|시공|이사|수리|설치)전문(?:병원|의원|업체|센터)', offer_text)
    if specialist and not re.search(r'목록|현황|명단|지정기준|안내자료', offer_text):
        offers.append(specialist[0])
        reasons.append('특정 서비스의 전문 제공기관임을 내세우는 홍보 문구')
    discount = re.search(r'(?<![\d.])(\d{1,3}(?:\.\d+)?)%(?:할인|off)', offer_text)
    if discount and 0 < float(discount[1]) <= 100:
        offers.append(discount[0])
        reasons.append('할인율을 제시하는 구매·이용 권유 문구')
    reward = re.search(r'리뷰(?:작성|등록).{0,30}(?:기프티콘|사은품|쿠폰|적립금).{0,15}(?:드려|드립니다|증정|지급|제공)', offer_text)
    if reward:
        offers.append(reward[0])
        reasons.append('리뷰 작성에 대한 보상 제공 문구')
    product = re.search(r'제품|상품|서비스|기피제|영양제|화장품|세정제|정수기|공기청정기', offer_text)
    usage = re.search(r'(?:뿌리|바르|먹|섭취|사용|이용).{0,20}(?:만해도|만으로|하세요)', offer_text)
    benefit = re.search(r'(?:예방|개선|효과|보호|해결|완화).{0,8}(?:가능|도움|탁월|확실|보장)', offer_text)
    # A named product plus a persuasive usage/benefit claim is stronger evidence
    # than disease names or generic prevention advice alone. Acronyms used for
    # public agencies and repellent ingredients are not brand evidence.
    names = [m[0] for m in re.finditer(r'(?<![A-Za-z])[A-Z][A-Z0-9-]{2,19}(?![A-Za-z])', text)
             if m[0] not in {'WHO', 'CDC', 'KDCA', 'FDA', 'DEET', 'ICARIDIN'}]
    named_product = bool(names or re.search(r'본제품|자사제품|제품명|상품명|브랜드', offer_text))
    if product and usage and benefit and named_product:
        offers.extend([product[0], usage[0], benefit[0]])
        reasons.append('제품 표기와 사용을 권하는 효능·효과 강조 문구가 함께 나타납니다.')
    # Product-detail crops often omit the brand, price and checkout button.
    # Recognize their persuasive structure, without treating a symptom alone
    # or an ordinary personal experience as commercial promotion.
    before = re.search(r'사용전|시술전', offer_text)
    after = re.search(r'사용후|시술후', offer_text)
    health_product = re.search(r'연고|크림|세럼|앰플|화장품|영양제|의료기기|미용기|마스크|'
                               r'레이저|플라즈마|(?:스킨|엑소좀)부스터', offer_text)
    effects = list(re.finditer(r'개선|완화|진정|재생|미백|항노화|안티에이징|회복|가라앉힐|'
                              r'효과적|탁월|좋아지|괜찮아지|피부장벽강화', offer_text))
    effect_terms = list(dict.fromkeys(m[0] for m in effects))
    testimonial = re.search(r'(?:쓰니|써보니|발라주니|사용하니|사용했는데).{0,40}'
                            r'(?:좋아|괜찮|만족)|(?:진정|개선|완화|효과).{0,8}탁월', offer_text)
    if ((before and after and effects)
            or (health_product and effects and (testimonial or len(effect_terms) >= 3))):
        offers.extend(([health_product[0]] if health_product else []) + effect_terms[:6])
        reasons.append('사용·시술 전후 비교 또는 제품 종류와 효과·사용 후기 강조 문맥이 함께 나타납니다.')
    seller_review = re.search(r'판매자가직접선정한.{0,12}(?:베스트)?리뷰|스토어pick', offer_text)
    review_use = re.search(r'사용기|사용했|구매했|샀어요', offer_text)
    review_praise = re.search(r'만족|추천|좋아|효과', offer_text)
    if seller_review and review_use and review_praise:
        offers.extend([seller_review[0], review_use[0], review_praise[0]])
        reasons.append('판매자가 선정한 구매·사용 후기를 통해 상품 만족도를 강조합니다.')
    if offers and not commercial_warning:
        commercial = next((hit for hit in result if hit['category'] == 'COMMERCIAL'), None)
        if commercial is None:
            result.append({'category': 'COMMERCIAL', 'matched_keywords': offers, 'reasons': reasons})
        else:
            commercial['matched_keywords'].extend(offers)
            commercial['reasons'].extend(reasons)
    return result


def classify_candidates(elements, rules=None):
    """Prefer leaf evidence; group title/body within the same article or comment."""
    rules = rules or DEFAULT_RULES
    by_id = {e["node_id"]: e for e in elements}
    hits, ancestor_hits = [], set()
    for element in elements:
        for analysis in analyze_candidate(element["text"], rules, tuple(element.get('text_breaks', []))):
            hit = {**element, **analysis}
            hits.append(hit)
            parent = hit["parent_id"]
            while parent is not None and parent in by_id:
                ancestor_hits.add((parent, hit["category"]))
                parent = by_id[parent]["parent_id"]
    grouped = {}
    for hit in hits:
        if (hit["node_id"], hit["category"]) in ancestor_hits:
            continue
        key = hit.get("content_scope") or hit["location"], hit["category"]
        previous = grouped.get(key)
        evidence_hits = [*(previous.get('evidence_hits', []) if previous else []), hit]
        if previous is None or len(hit["text"]) > len(previous["text"]):
            grouped[key] = {**hit}
        grouped[key]['evidence_hits'] = evidence_hits
    return list(grouped.values())
