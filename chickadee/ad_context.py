"""Commercial evidence required before a model-only score creates an ad row."""
import re
import unicodedata


def commercial_support(text):
    text = re.sub(r'\s+', '', unicodedata.normalize('NFKC', text)).casefold()
    if re.search(r'(?:새로나온|신제품|출시).{0,40}(?:사용해보세요|체험해보세요|경험해보세요)', text):
        return True
    subject = re.search(r'상품|제품|서비스|판매|구매|주문|가격|예약|시술|수술|수강|배송|매장|쇼핑|브랜드|스토어|숙박|업체|대출|투자|카지노|슬롯|토토|베팅|성인방송|마약|계좌', text)
    offer = re.search(r'할인|특가|무료체험|쿠폰|혜택|보너스|사은품|증정|최저가|우대가|적립|수익|\d+(?:,\d{3})*(?:만|천)?원', text)
    action = re.search(r'문의|상담|신청|구매|주문|예약|방문|받으|가입|클릭', text)
    pitch = re.search(r'추천합니다|놓치지마|만나보세요|판매합니다|예약하세요|구매하세요|주문하세요', text)
    return bool(subject and ((offer and action) or pitch))
