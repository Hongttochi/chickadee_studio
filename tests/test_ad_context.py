import unittest
from unittest.mock import patch
from chickadee.ad_context import commercial_support
from chickadee.local_ai import add_model_candidates, enrich_report


class AdContextTests(unittest.TestCase):
    def test_information_is_not_an_ad_even_with_a_high_model_score(self):
        texts = ['인기 검색어 | #누리과정 #개정 누리과정 #놀이 #놀이지원',
                 '지역사회자원을 활용한 우리 가족 놀이 실천 사례 공모전 수상작 발표',
                 '정서·행동 등 발달 분야 특별 할인 안내 작성자 2026.10.22 답변대기',
                 '직장인 독서 동아리 모임 일정 안내', '시민 과학 체험 행사 결과 발표',
                 '병원 진료를 받고 회복한 개인적인 경험입니다.', '최근 검색어 인기 자료 목록']
        for text in texts:
            with self.subTest(text=text):
                self.assertFalse(commercial_support(text))
                packet = {'url':'https://different.example/post', 'location':'#content', 'text':text,
                          'local_ai':{'laya':{'status':'completed','label':'ad_context','review_priority':'high','score':.99}}}
                report = {'evidence_packets':[packet], 'ad_candidates':[]}
                add_model_candidates(report, 'laya')
                self.assertEqual(report['ad_candidates'],[])
                with patch('chickadee.local_ai.text_analysis', return_value={
                    'status':'completed','label':'ad_context','review_priority':'high','score':.99}):
                    enrich_report(report)
                self.assertEqual(report['ad_candidates'],[])

    def test_commercial_actions_and_product_pitches_remain_reviewable(self):
        for text in ['정기 청소 서비스 첫 예약 할인 혜택 지금 신청하세요',
                     '신제품을 체험해보세요! 더 편한 생활을 만나보세요',
                     '새로 나온 청소기를 사용해보세요! 먼지 걱정을 줄여드립니다.',
                     '숙박 예약 시 특별 혜택! 지금 예약하세요', '카지노 신규 가입 보너스']:
            with self.subTest(text=text):
                self.assertTrue(commercial_support(text))
