import asyncio
import base64
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from PIL import Image
from playwright.async_api import async_playwright
from chickadee.scanner import _State, _inspect_frame
from chickadee.inspection import validate_screenshots


class PageEvidenceTests(unittest.TestCase):
    def test_title_body_comments_are_collected_with_matching_captures(self):
        async def check():
            async with async_playwright() as pw:
                browser = await pw.chromium.launch()
                try:
                    page = await browser.new_page(viewport={'width':900, 'height':600})
                    await page.set_content('''<header style="height:750px;background:#ddd">정상 사이트 메뉴</header>
                      <article><h1>카 지 노 신 규 가 입 혜 택</h1>
                      <p>상품 주문 특별 할인 구매 혜택</p>
                      <div class="comment">원금 보장 고수익 투자 모집</div>
                      <div class="comment">신용 확인 없이 당일 대출 상담 신청</div></article>''')
                    state = _State()
                    state.trace.snapshot('https://different.example/post', 'fixture', 'read', lambda _: None)
                    script = Path('chickadee/extract.js').read_text()
                    with patch('chickadee.scanner.visual_analysis', return_value={'status':'unavailable'}):
                        await _inspect_frame(page.main_frame,'',{},'https://different.example/post',script,state,lambda _:None,
                                             detect_techniques=False,ocr_enabled=False)
                    roles = {source.get('source_role') for row in state.ad_candidates for source in row['evidence_sources']}
                    self.assertTrue({'title','body','comment'}.issubset(roles), roles)
                    self.assertEqual(await page.evaluate('scrollY'),0)
                    for row in state.ad_candidates:
                        for source in row['evidence_sources']:
                            screenshot = state.screenshots[source['screenshot_id']]
                            self.assertEqual(screenshot['capture'],'target_element')
                            self.assertEqual(screenshot['location'],source['location'])
                            image = Image.open(io.BytesIO(base64.b64decode(screenshot['data_url'].split(',')[1])))
                            self.assertLess(image.height,200) # A text element, not the unrelated 600px viewport.
                    validate_screenshots(state.screenshots)
                    if os.environ.get('CHICKADEE_WRITE_PAGE_FIXTURE'):
                        Path(os.environ['CHICKADEE_WRITE_PAGE_FIXTURE']).write_text(json.dumps({
                            'kind':'done', 'result':{'meta':{'entry_url':'https://different.example/post','elapsed_sec':1},'findings':[]},
                            'report':{'status':'completed','pages_scanned':['https://different.example/post'],
                                      'ad_candidates':state.ad_candidates,'screenshots':state.screenshots,
                                      'ocr_images':[],'evidence_details':{}}},ensure_ascii=False))
                finally:
                    await browser.close()
        asyncio.run(check())
