import unittest
from chickadee.candidates import analyze_candidate


class OCRCandidateTests(unittest.TestCase):
    def test_shopping_coupons_and_service_price_offers(self):
        for text in ('상품상세참조 중국 의약품 오일연고 쿠폰적용가22,770원 20,040원',
                     '검대추출물수면명 양제꿀잠 추가즉시활인쿠폰',
                     '해외구매대방 SWISSE 잠잘자는약 상품 10.000원 도서산간 배송비',
                     '미국 수면질향상 12512091 추105%적립',
                     '8병 강도 120탭/병 야간 깊은수면 불면증 성인을위한',
                     '스마일라식공식인증안과 230만원 48% 아벤트기간:2024-03-01',
                     '스마일라식 국내최저가제공 정상가 350만원 특별 우대가 담당자문의'):
            with self.subTest(text=text):
                self.assertIn('COMMERCIAL', [h['category'] for h in analyze_candidate(text)])

    def test_specialist_service_banner(self):
        for text in ('교통사고 후유쯤 치료 전문 병원', '입주 청소 전문 업체'):
            self.assertIn('COMMERCIAL', [h['category'] for h in analyze_candidate(text)])
        self.assertNotIn('COMMERCIAL', [h['category'] for h in analyze_candidate('치료 전문 병원 지정기준 현황 안내자료')])

    def test_prices_and_medical_mentions_without_promotion_are_not_commercial(self):
        for text in ('진료비 1만원을 지출했다', '안과 수술 환자의 48%가 응답했다',
                     '주문하기 버튼 구현 방법', '할인 쿠폰 사용법 안내',
                     '불면증과 숙면에 관한 건강 정보',
                     '수술 진료비는 230만원이었다', '쿠폰적용가 1만원 광고를 누르지 마세요'):
            with self.subTest(text=text):
                self.assertNotIn('COMMERCIAL', [h['category'] for h in analyze_candidate(text)])

    def test_account_transfer_recruitment(self):
        text = '세금을줄이고자(차)(명)계좌모집중입니다 한계좌기준200만원 1인최대3계좌까지 양도가능합니다'
        self.assertIn('ACCOUNT_TRADE', [h['category'] for h in analyze_candidate(text)])
        self.assertNotIn('ACCOUNT_TRADE', [h['category'] for h in analyze_candidate('계좌 양도 모집에 응하면 처벌받습니다')])

    def test_targeted_events_with_prices_or_benefits_are_commercial(self):
        for text in ('수험생 여러분 고생하셨습니다! 치과 수능 이벤트 교정 진단비 1만원 수험표지장시적용',
                     '직장인 이벤트 주말에 수술하고 월요일에 출근하세요 +플러스 혜택 '
                     '10만원 주기할인 이벤트기간:2023.01.01~2023.12.31',
                     '신입생 이벤트 수강료 30,000원', '직장인 프로모션 추가 할인',
                     '가정의 달 기획전 사은품 증정', '수험생 특가 진단비 1만 원'):
            with self.subTest(text=text):
                self.assertIn('COMMERCIAL', [h['category'] for h in analyze_candidate(text)])

    def test_event_names_dates_and_warnings_alone_are_not_commercial(self):
        for text in ('수능 응원 이벤트 수험생 여러분 고생하셨습니다.',
                     '도서관 직장인 독서 이벤트 2026.11.01',
                     '교내 수능 행사 이벤트 참여 안내',
                     '수능 이벤트 진단비 1만원이라는 광고 문구를 비판하는 기사',
                     '직장인 이벤트 할인 광고를 누르지 마세요'):
            with self.subTest(text=text):
                self.assertNotIn('COMMERCIAL', [h['category'] for h in analyze_candidate(text)])

    def test_product_detail_crops_without_brand_or_price_are_commercial(self):
        cases = ('좁쌀여드름연고 땀띠 트러블 진정에 탁월하며 '
                 '트러블은 3일 정도 쓰니 좋아지구요 사용전 사용후 '
                 '수시로 꾸준히 발라주니 점점 괜찮아지면서',
                 '여드름으로 붉어진 피부를 가라앉힐 수 있어요 '
                 '사용 전 울긋불긋 피부 사용 후 붉은기 완화',
                 '플라즈마와 미세전류가 피부 진피층까지 침투하여 '
                 '주름 개선 진정 및 트러블 케어 피부트러블 완화',
                 '피부질환을 치료하는 의료기기 LED마스크 '
                 '피부손상개선 피부진정 미백 여드름완화 피부재생',
                 '엑소좀 부스터 #피부재생 #안티에이징 #피부장벽강화 '
                 '피부 관련 문제를 해결해주며 아토피 등에 효과적입니다.',
                 '스토어PICK 판매자가 직접 선정한 베스트 리뷰입니다. '
                 '한달사용기 한달정도 사용했는데 가격이 부담돼서 샀어요. 아주 만족스럽습니다')
        for text in cases:
            with self.subTest(text=text):
                self.assertIn('COMMERCIAL', [h['category'] for h in analyze_candidate(text)])

    def test_health_information_and_personal_reviews_alone_are_not_commercial(self):
        cases = ('여드름은 청소년기에 흔하며 피부에 염증이 나타납니다.',
                 '연고를 사용하기 전 주의사항을 읽으세요.',
                 '여드름 연고를 쓰니 좋아졌다는 개인적인 일기입니다.',
                 '피부 개선과 회복에 관한 연구 결과를 발표했습니다.',
                 '사용 전후 피부 진정 효과 광고를 누르지 마세요',
                 '좁쌀여드름 연고 사용전 사용후 개선 광고 문구를 비판하는 기사',
                 '사용 전 전원을 확인하고 사용 후 코드를 뽑으세요',
                 '화장품 사용기 한 달 사용했는데 만족스럽습니다')
        for text in cases:
            with self.subTest(text=text):
                self.assertNotIn('COMMERCIAL', [h['category'] for h in analyze_candidate(text)])

    def test_investment_trial_and_free_class_recruitment(self):
        for text in ('종목추천서비스체험 이벤트-\n급등주무료체험1개월 제공\n사이트방문\n'
                     '급등주 검색기부터 투자 수익률을 높여주는 프로그램까지',
                     '무료투자강의!\n인원 제한1,000명!\n가입하기\n'
                     '주식시장의 황금같은 투자 기회를 놓치지 마세요!',
                     '주식 교육 무료 강의 신청', '투자서비스 체험 1개월 제공 문의'):
            with self.subTest(text=text):
                self.assertIn('INVESTMENT', [h['category'] for h in analyze_candidate(text)])

    def test_investment_mentions_and_warning_quotes_are_not_recruitment(self):
        for text in ('학교 금융 교육: 주식 투자 강의 일정 안내',
                     '무료투자강의! 가입하기 광고를 누르지 마세요',
                     '종목추천 서비스 무료체험 사이트방문 사기 피해 예방 안내',
                     '주식시장 무료 자료 안내', '도서관 무료 강의 신청'):
            with self.subTest(text=text):
                self.assertNotIn('INVESTMENT', [h['category'] for h in analyze_candidate(text)])

    def test_account_recruitment_from_real_image_transcription_without_url(self):
        text = ('유통 임대계좌 안내입니다. 신규 또는 휴면 임대계좌 등록해주시면 '
                '1개 접수시 3일 사용 이백만원 등록비 드리며 최대 5개까지 등록가능합니다.')
        self.assertIn('ACCOUNT_TRADE', [h['category'] for h in analyze_candidate(text)])
        disguised = '계/좌를 임대해 주실 경우 1계좌당 일주일에 300만원 수익 가능.'
        self.assertIn('ACCOUNT_TRADE', [h['category'] for h in analyze_candidate(disguised)])

    def test_prevention_and_ordinary_bank_notices_are_not_recruitment(self):
        for text in ('계좌를 임대하면 처벌받습니다. 고수익 모집 피해 예방 안내입니다.',
                     '도서관 회원 등록과 계좌 자동이체 안내입니다.',
                     '당일 대출 사기 피해 예방과 상담 신청 주의 안내'):
            self.assertEqual(analyze_candidate(text), [], text)

    def test_phone_or_image_only_loan_ad_does_not_require_a_url(self):
        self.assertIn('LOAN', [h['category'] for h in analyze_candidate('신용 확인 없이 당일 대출 상담 신청')])

    def test_small_loan_banners_without_the_word_loan(self):
        for text in ('방문없이당일 진행\n20-200소액전문',
                     '비대면 소액 전문 50~300만원',
                     '급전 10만-100만원 당일입금'):
            with self.subTest(text=text):
                self.assertIn('LOAN', [h['category'] for h in analyze_candidate(text)])

    def test_amount_and_same_day_services_alone_are_not_loans(self):
        for text in ('20-200만원 상품 당일 배송', '소액 전문 상담 안내',
                     '소액소송 전문 20~200만원 당일 상담',
                     '비대면 소액 전문 20~200만원 모집 피해 예방 안내',
                     '방문 없이 당일 진료 20~200명', '50~300만원 소액 자금 안내'):
            with self.subTest(text=text):
                self.assertNotIn('LOAN', [h['category'] for h in analyze_candidate(text)])

    def test_commercial_offers_survive_partial_ocr_without_product_or_url(self):
        for text in ('최대 49%할인\n수송전\n플I트-이벤트',
                     '최대 ４９％ 할 인',
                     'N예약\n검색\n리뷰작성시\n커피기프티콘\n드려요',
                     '리뷰 등록하면 쿠폰을 제공합니다'):
            with self.subTest(text=text):
                self.assertIn('COMMERCIAL', [h['category'] for h in analyze_candidate(text)])

    def test_discount_mentions_and_quoted_warnings_are_not_sales_offers(self):
        for text in ('도서관 독서 행사 안내', '할인율 49% 계산 문제',
                     '최대 할인 안내', '리뷰 작성 방법과 쿠폰 사용법',
                     '최대 49% 할인 광고를 누르지 마세요',
                     '최대 49% 할인이라는 광고 문구를 비판하는 기사',
                     '최대 149% 할인', '0% 할인'):
            with self.subTest(text=text):
                self.assertEqual(analyze_candidate(text), [])

    def test_multiple_sales_signals_produce_one_commercial_candidate(self):
        hits = analyze_candidate('특별 할인 상품 주문 최대 49% 할인! 리뷰 작성시 쿠폰 드려요')
        self.assertEqual([hit['category'] for hit in hits], ['COMMERCIAL'])

    def test_prevention_benefit_can_be_a_commercial_product_promotion(self):
        cases = ('말라리아, 일본뇌염, 지카바이러스, 뎅기열\n'
                 '모기기피제를팔뿌리기만 해도다양한 필병감염의예방이가능합니다!\n'
                 'SOFFELL 쏘텔벌레 해승 방증모기 퇴지제',
                 '본 제품을 사용하기만 해도 피부 개선에 도움이 됩니다',
                 '감염 예방용 상품 주문 특별 할인 구매 혜택 20% 할인')
        for text in cases:
            with self.subTest(text=text):
                self.assertIn('COMMERCIAL', [hit['category'] for hit in analyze_candidate(text)])

    def test_health_advice_and_consumer_warnings_are_not_product_ads(self):
        cases = ('말라리아 일본뇌염 지카바이러스 뎅기열 예방 안내',
                 '모기기피제를 뿌리기만 해도 감염 예방이 가능합니다',
                 'WHO: 모기기피제를 사용하기만 해도 감염 예방이 가능합니다',
                 'DEET 모기기피제를 사용하기만 해도 감염 예방이 가능합니다',
                 '본 제품 사용만으로 질병 예방이 가능하다는 허위 광고 피해 예방 안내',
                 '감염 예방용 제품 20% 할인 광고를 누르지 마세요')
        for text in cases:
            with self.subTest(text=text):
                self.assertNotIn('COMMERCIAL', [hit['category'] for hit in analyze_candidate(text)])

    def test_drug_transactions_from_ocr_do_not_depend_on_photo_score(self):
        cases = ('자유게시킨\n리화나 bd 대마초 열에스디밀 일역매시드 워드 weed 열 우표 대MT 블로터 직관(구객문의)필각:\n트리스트쿠쉬',
                 '캔디허브 대마LSD 코카인\n떨 케타민\n아이스판매\n작대기 판매',
                 '아이스딜러 문의주세요 #아이스판매 #작대기팝니다',
                 '필로폰 판매 문의', 'weed 주문 문의', 'LSD팝니다')
        for text in cases:
            with self.subTest(text=text):
                self.assertIn('DRUGS', [hit['category'] for hit in analyze_candidate(text)])

    def test_drug_education_treatment_and_ambiguous_objects_are_not_transactions(self):
        cases = ('대마초와 코카인에 대한 설명', '마약 판매 광고를 누르지 마세요',
                 '필로폰 판매자 검거 보도', '대마초 구매 피해 예방 안내',
                 '케타민 치료 상담 문의', '케타민 의료 연구 및 구입 절차',
                 '아이스 커피 판매', '정원 weed 제거 도구 판매',
                 '나무 작대기 팝니다', '투명 비닐봉투 판매', '잔디가 바람에 떨립니다')
        for text in cases:
            with self.subTest(text=text):
                self.assertNotIn('DRUGS', [hit['category'] for hit in analyze_candidate(text)])


if __name__ == '__main__':
    unittest.main()
