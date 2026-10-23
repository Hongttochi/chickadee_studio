import unittest
from chickadee.candidates import analyze_candidate


class OCRCandidateTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
