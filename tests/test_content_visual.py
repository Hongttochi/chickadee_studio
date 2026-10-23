import asyncio
import base64
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
from threading import Event
import unittest
from functools import wraps
from unittest.mock import AsyncMock, patch

from chickadee.content_visual import TOPICS, enrich_content_images, image_candidates, model_contract, validate_analysis
from chickadee.async_runtime import event_loop_runner


def async_test(function):
    @wraps(function)
    def wrapped(self):
        with event_loop_runner() as runner:return runner.run(function(self))
    return wrapped


def sample():
    from PIL import Image
    buffer=io.BytesIO();Image.new('RGB',(32,32),'white').save(buffer,format='PNG');data=buffer.getvalue()
    sha=hashlib.sha256(data).hexdigest();relative='evidence/images/'+sha+'.png'
    image={'id':'im_1','url':'http://127.0.0.1/','location':'img#photo','status':'completed',
        'width':32,'height':32,'lines':[],'text':'','recognition_status':'unreadable',
        'image_sha256':sha,'relative_path':relative}
    analysis={'status':'completed','model':'test','model_sha256':'a'*64,'image_sha256':sha,
        'scores':dict(zip(TOPICS,[.1,.2,.9])),'thresholds':dict.fromkeys(TOPICS,.6)}
    return data,image,analysis


class ContentVisualTests(unittest.TestCase):
    def test_explicit_financial_ad_is_not_relabelled_by_unrelated_photo_score(self):
        _, image, analysis = sample()
        image['lines'] = [{'text': '무료투자강의! 인원 제한 1,000명! 가입하기', 'confidence': .98}]
        self.assertEqual(image_candidates(image, analysis), [])
        self.assertEqual(analysis['scores']['drugs'], .9)

    def test_corroborated_drug_ad_survives_other_commercial_signals(self):
        from chickadee.candidates import analyze_candidate
        _, image, analysis = sample()
        image['text'] = '필로폰 판매 문의 20% 할인'
        self.assertIn('DRUGS', [r['category'] for r in analyze_candidate(image['text'])])
        self.assertEqual(image_candidates(image, analysis), [])

    def test_photo_scores_alone_never_assert_gambling_advertising(self):
        _, image, analysis = sample()
        for score in (.575, .753, .99):
            with self.subTest(score=score):
                analysis['scores'] = dict(zip(TOPICS, [.1, score, .1]))
                analysis['thresholds']['gambling'] = .48
                rows = image_candidates(image, analysis)
                self.assertEqual([r['category'] for r in rows], ['IMAGE_REVIEW'])
                self.assertNotIn('도박 이미지', rows[0]['evidence_text'])
                self.assertEqual(rows[0]['local_ai']['content_visual']['scores']['gambling'], score)

    @async_test
    async def test_direct_image_uses_ocr_before_resolving_photo_topic(self):
        from chickadee.content_analysis import analyze_content
        from chickadee.runtime import environment
        data, _, analysis = sample()
        ocr = {'status': 'completed', 'lines': [
            {'text': '무료투자강의! 인원 제한 1,000명! 가입하기', 'confidence': .98}]}
        with patch('chickadee.content_analysis.analyze_photo', new_callable=AsyncMock, return_value=analysis), \
             patch('chickadee.content_analysis.OCRSession.recognize', new_callable=AsyncMock, return_value=ocr), \
             patch('chickadee.content_analysis.review_sources', new_callable=AsyncMock):
            value = await analyze_content('', data, environment('standard'), Event())
        self.assertEqual(value['image']['ad_candidates'], [])
        self.assertEqual([r['category'] for r in value['sources'][0]['ad_candidates']], ['INVESTMENT'])

    @async_test
    async def test_photo_pixels_are_collected_when_ocr_switch_is_off(self):
        from chickadee.scanner import _State,_inspect_images,_ocr_summary,ScanConfig
        data,_,_=sample();state=_State(ocr_enabled=False,photo_enabled=True)
        source='data:image/png;base64,'+base64.b64encode(data).decode()
        with patch.object(state.ocr,'recognize',new_callable=AsyncMock) as ocr:
            await _inspect_images(None,[{'location':'img','source_url':source,'source_type':'img'}],'','http://127.0.0.1/',state,lambda _:None,None)
        ocr.assert_not_awaited();self.assertEqual(len(state.image_assets),1)
        self.assertEqual(state.ocr_images[0]['recognition_status'],'skipped')
        self.assertEqual(_ocr_summary(state,ScanConfig('http://127.0.0.1/',ocr_enabled=False))['completed'],0)

    @async_test
    async def test_photo_pixels_survive_ocr_timeout(self):
        from chickadee.scanner import _State,_inspect_images
        data,_,_=sample();state=_State(photo_enabled=True)
        source='data:image/png;base64,'+base64.b64encode(data).decode()
        with patch.object(state.ocr,'recognize',new_callable=AsyncMock,side_effect=ValueError('OCR timeout')):
            await _inspect_images(None,[{'location':'img','source_url':source,'source_type':'img'}],'','http://127.0.0.1/',state,lambda _:None,None)
        self.assertEqual(state.ocr_images[0]['status'],'failed')
        self.assertEqual(state.image_assets[state.ocr_images[0]['relative_path']],data)

    @async_test
    async def test_blank_ocr_image_still_becomes_photo_candidate(self):
        data,image,analysis=sample();report={'ocr_images':[image],'ad_candidates':[]}
        with patch('chickadee.content_visual.model_contract',return_value={'approved_for_app':True}), \
             patch('chickadee.content_visual.ContentSession.recognize',new_callable=AsyncMock,return_value=analysis) as worker:
            await enrich_content_images(report,{image['relative_path']:data})
        worker.assert_awaited_once();self.assertEqual(report['content_visual']['analyzed'],1)
        self.assertEqual(report['ad_candidates'][0]['category'],'IMAGE_REVIEW')
        self.assertEqual(report['ad_candidates'][0]['source_kind'],'image_visual')
        self.assertEqual(report['ocr_images'][0]['recognition_status'],'unreadable')

    @async_test
    async def test_one_inference_per_hash_and_unique_candidate_ids(self):
        data,image,analysis=sample();second={**image,'id':'im_2','url':'http://127.0.0.1/other'}
        report={'ocr_images':[image,second],'ad_candidates':[{'id':'c_00007','url':'http://127.0.0.1/','category':'LOAN'}]}
        with patch('chickadee.content_visual.model_contract',return_value={}), \
             patch('chickadee.content_visual.ContentSession.recognize',new_callable=AsyncMock,return_value=analysis) as worker:
            await enrich_content_images(report,{image['relative_path']:data})
        worker.assert_awaited_once();self.assertEqual([r['id'] for r in report['ad_candidates']],['c_00007','c_00008'])

    @async_test
    async def test_unapproved_missing_model_never_starts_inference(self):
        data,image,_=sample();report={'ocr_images':[image]}
        with patch('chickadee.content_visual.model_contract',return_value=None), \
             patch('chickadee.content_visual.ContentSession.recognize',new_callable=AsyncMock) as worker:
            await enrich_content_images(report,{image['relative_path']:data})
        worker.assert_not_awaited();self.assertEqual(report['content_visual']['status'],'unavailable')

    @async_test
    async def test_changed_image_bytes_fail_closed(self):
        data,image,analysis=sample();report={'ocr_images':[image]}
        with patch('chickadee.content_visual.model_contract',return_value={}), \
             patch('chickadee.content_visual.ContentSession.recognize',new_callable=AsyncMock) as worker:
            await enrich_content_images(report,{image['relative_path']:data+b'changed'})
        worker.assert_not_awaited();self.assertEqual(report['content_visual']['failed'],1)

    @async_test
    async def test_scan_save_reload_and_csv_include_no_text_photo_signal(self):
        from chickadee.scanner import ScanConfig,ScanOutcome,scan
        data,image,analysis=sample()
        async def crawl(config,state,*args):
            state.pages.append(config.entry_url);state.ocr_images.append(image);state.image_assets[image['relative_path']]=data
        with patch('chickadee.scanner._crawl',new=crawl), \
             patch('chickadee.scanner.enrich_laya',new_callable=AsyncMock), \
             patch('chickadee.content_visual.model_contract',return_value={}), \
             patch('chickadee.content_visual.ContentSession.recognize',new_callable=AsyncMock,return_value=analysis):
            outcome=await scan(ScanConfig('http://127.0.0.1/',timeout_sec=60))
        with tempfile.TemporaryDirectory() as folder:
            path=outcome.save(Path(folder));loaded=ScanOutcome.load(path)
            self.assertEqual(loaded.report['ad_candidates'][0]['category'],'IMAGE_REVIEW')
            self.assertIn('IMAGE_REVIEW',path.with_name('result.csv').read_text(encoding='utf-8-sig'))
            self.assertEqual(loaded.result['findings'],[])

    @async_test
    async def test_direct_image_keeps_visual_candidate_when_ocr_fails(self):
        from chickadee.content_analysis import analyze_content
        from chickadee.runtime import environment
        data,_,analysis=sample()
        with patch('chickadee.content_analysis.analyze_photo',new_callable=AsyncMock,return_value=analysis), \
             patch('chickadee.content_analysis.OCRSession.recognize',new_callable=AsyncMock,side_effect=ValueError('no text')), \
             patch('chickadee.content_analysis.review_sources',new_callable=AsyncMock):
            value=await analyze_content('',data,environment('standard'),Event())
        self.assertEqual(value['candidate_count'],1)
        self.assertEqual(value['image']['ad_candidates'][0]['category'],'IMAGE_REVIEW')
        self.assertEqual(value['image']['local_ai']['content_visual']['status'],'completed')


class PhotoContractTests(unittest.TestCase):
    def test_unapproved_contract_does_not_load_weights(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'manifest.json').write_text('{"approved_for_app":false}')
            self.assertIsNone(model_contract(folder))

    def test_invalid_scores_are_rejected(self):
        _,_,value=sample()
        for number in (float('nan'),float('inf'),-1,2,True):
            bad=deepcopy(value);bad['scores']['drugs']=number
            with self.assertRaises(ValueError):validate_analysis(bad)

    def test_real_cpu_resnet_forward_matches_three_sigmoid_heads(self):
        import paddle
        from chickadee.content_worker import PhotoReader
        data,_,_=sample();paddle.set_device('cpu')
        with tempfile.TemporaryDirectory() as folder:
            model=paddle.vision.models.resnet18(pretrained=False)
            model.fc=paddle.nn.Sequential(paddle.nn.Dropout(.25),paddle.nn.Linear(512,3))
            model.fc[1].weight.set_value(paddle.zeros_like(model.fc[1].weight))
            model.fc[1].bias.set_value(paddle.to_tensor([-3.,0.,3.]))
            file=Path(folder,'model.pdparams');paddle.save(model.state_dict(),str(file))
            contract={'dropout':.25,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'thresholds':dict.fromkeys(TOPICS,.6)}
            with patch('chickadee.content_visual.DATA',Path(folder)),patch('chickadee.content_visual.model_contract',return_value=contract):
                reader=PhotoReader();value=validate_analysis(reader.read(data))
            self.assertLess(value['scores']['sexual_content'],.05)
            self.assertAlmostEqual(value['scores']['gambling'],.5,places=5)
            self.assertGreater(value['scores']['drugs'],.95)


if __name__=='__main__':unittest.main()
