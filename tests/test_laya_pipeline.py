"""Pipeline contracts, bounded failure/cancellation, integrity; no paid provider."""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
import sys
from pathlib import Path
from threading import Event
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from chickadee.content_analysis import analyze_content
from chickadee.inspection import validate_inspection, validate_local_ai
from chickadee.laya_review import LayaSession, enrich_laya, review_sources, unavailable, MAX_ITEMS
from chickadee.laya_worker import verified_bundle, QUESTIONS
from chickadee.runtime import environment
from tests.test_inspection_agent import packet

SIGNAL={'status':'completed','model':'Laya','version':'test-fixture', 'score':.8,
        'score_kind':'calibrated_promotion_score','label':'ad_context','review_priority':'high','paid_requests':0}


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_model_does_not_start_worker_or_call_paid_api(self):
        with patch.dict(os.environ,{},clear=True), patch('asyncio.create_subprocess_exec') as process, patch('chickadee.agent.groq_request') as paid:
            result=await LayaSession().analyze(['도서관 안내'])
        self.assertEqual(result[0]['status'],'unavailable');process.assert_not_called();paid.assert_not_called()

    async def test_real_process_with_unapproved_model_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'CHICKADEE_LAYA_MODEL_DIR':folder}), patch('chickadee.runtime.memory_info',return_value={'available_bytes':8*1024**3}):
            result=await LayaSession().analyze(['이미지에서 읽은 글자'])
        self.assertEqual(result[0]['status'],'unavailable')

    async def test_external_python_worker_loads_from_installed_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            config=folder/'laya.json'
            config.write_text(json.dumps({'format':1,'model_dir':str(folder),'python':sys.executable}),encoding='utf-8')
            with patch.dict(os.environ,{'CHICKADEE_LAYA_CONFIG':str(config)},clear=True), patch('chickadee.runtime.memory_info',return_value={'available_bytes':8*1024**3}):
                result=await LayaSession().analyze(['설치한 로컬 실행 환경의 원문'])
            self.assertEqual(len(result),1)
            self.assertEqual(result[0]['reason'],'model_or_runtime_unavailable')
            self.assertEqual(result[0]['paid_requests'],0)

    async def test_low_memory_does_not_load_large_model(self):
        with patch.dict(os.environ,{'CHICKADEE_LAYA_MODEL_DIR':'unused'}), patch('chickadee.runtime.memory_info',return_value={'available_bytes':1024**3}), patch('asyncio.create_subprocess_exec') as process:
            value=await LayaSession().analyze(['원문'])
        self.assertEqual(value[0]['reason'],'insufficient_memory');process.assert_not_called()

    async def test_expired_time_budget_never_starts_worker(self):
        with patch('asyncio.create_subprocess_exec') as process:
            value=await LayaSession(timeout_seconds=0).analyze(['원문'])
        self.assertEqual(value[0]['reason'],'time_budget');process.assert_not_called()

    async def test_ocr_then_ml_then_laya_keeps_input_response_and_output_sources(self):
        image=(Path(__file__).parent/'fixtures/ocr/promotion.png').read_bytes()
        stages=[];received=[]
        async def infer(texts):
            received.extend(texts);return [dict(SIGNAL) for _ in texts]
        ocr={'status':'completed','engine':'PaddleOCR','model':'fixture','lines':[{'text':'카지노 가입 보너스','confidence':.95}]}
        with patch('chickadee.content_analysis.OCRSession.recognize',AsyncMock(return_value=ocr)), patch.object(LayaSession,'analyze',side_effect=infer):
            value=await analyze_content('도서관 안내',image,environment('standard'),Event(),stages.append)
        self.assertEqual(stages[-3:],['ml','laya','laya'])
        self.assertEqual(stages[:2],['models','ml']) # typed text bypasses OCR
        self.assertLess(stages.index('ocr'),max(i for i,s in enumerate(stages) if s=='ml'))
        self.assertEqual(received,['도서관 안내','카지노 가입 보너스'])
        self.assertEqual(value['sources'][1]['local_ai']['laya']['score'],.8)
        self.assertEqual(value['sources'][1]['source_kind'],'image_ocr')
        self.assertFalse(value['sources'][1]['original_unicode_observed'])
        self.assertEqual(value['paid_requests'],0)
        self.assertEqual(set(value),{'status','sources','image','errors','runtime_environment','finished_at','paid_requests','candidate_count'})

    async def test_review_is_bounded_deduplicated_and_counts_omissions(self):
        sources=[{'text':f'본문 {n}'} for n in range(MAX_ITEMS+2)]+[{'text':'본문 0'}]
        async def infer(texts):return [dict(SIGNAL) for _ in texts]
        with patch.object(LayaSession,'analyze',side_effect=infer) as infer_mock:
            value=await review_sources(sources)
        self.assertEqual(len(infer_mock.call_args.args[0]),MAX_ITEMS)
        self.assertEqual(value['omitted'],2);self.assertEqual(value['status'],'partial')
        self.assertEqual(sources[-1]['local_ai']['laya'],SIGNAL)

    async def test_stop_and_worker_failure_preserve_original_evidence(self):
        stop=Event();started=asyncio.Event();closed=asyncio.Event()
        async def slow(_texts):
            started.set()
            try:await asyncio.sleep(60)
            finally:closed.set()
        sources=[{'text':'원문 보존'}]
        with patch.object(LayaSession,'analyze',side_effect=slow):
            task=asyncio.create_task(review_sources(sources,stop=stop))
            await started.wait();stop.set();await asyncio.wait_for(task,2)
        self.assertTrue(closed.is_set());self.assertEqual(sources[0]['text'],'원문 보존')
        self.assertEqual(sources[0]['local_ai']['laya']['status'],'unavailable')
        with patch.object(LayaSession,'analyze',AsyncMock(side_effect=RuntimeError('broken worker'))):
            self.assertEqual((await review_sources(sources))['status'],'unavailable')

    async def test_review_never_changes_findings_hashes_or_promotes_candidates(self):
        p=packet();p['local_ai']={'text':{'score':.1}}
        row={'url':p['url'],'location':p['location'],'evidence_text':p['text'],'source_kind':'dom_text'}
        report={'evidence_packets':[p],'ad_candidates':[row],'evidence_details':{},'screenshots':{},'local_ai':{},'findings':[{'untouched':True}]}
        before=deepcopy(report['findings']);text_hash=p['text_sha256']
        with patch.object(LayaSession,'analyze',AsyncMock(return_value=[dict(SIGNAL)])):
            await enrich_laya(report)
        self.assertEqual(report['findings'],before);self.assertEqual(p['text_sha256'],text_hash)
        self.assertEqual(len(report['ad_candidates']),1);self.assertEqual(row['local_ai']['laya'],SIGNAL)
        validate_local_ai({'laya':p['local_ai']['laya']})

    async def test_navigation_without_features_does_not_spend_review_budget(self):
        body=packet();body['local_ai']={'text':{'score':None,'feature_count':0}}
        heading={**deepcopy(body),'id':'heading','location':'h1','text':'게시글 001','scope_quality':'element'}
        report={'evidence_packets':[heading,body],'local_ai':{}}
        with patch.object(LayaSession,'analyze',AsyncMock(return_value=[dict(SIGNAL)])) as infer:
            await enrich_laya(report)
        self.assertEqual(infer.call_args.args[0],[body['text']])
        self.assertEqual(heading['local_ai']['laya']['reason'],'insufficient_scope')
        self.assertEqual(report['local_ai']['laya']['status'],'partial')


class BundleTests(unittest.TestCase):
    def bundle(self,folder):
        (folder/'base').mkdir();(folder/'base/config.json').write_text('{}')
        (folder/'base/model.safetensors').write_bytes(b'base-fixture-not-a-real-model')
        (folder/'best.safetensors').write_bytes(b'test-only-inert-fixture')
        files=[{'path':p.relative_to(folder).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [folder/'base/config.json',folder/'base/model.safetensors',folder/'best.safetensors']]
        meta={'format':1,'training':'full_encoder','approved':True,'version':'test-only','temperature':2.85,'files':files,
            'evaluation':{'passed':True,'threshold':.5,'test_used_for_training':False,'checkpoint_sha256':files[-1]['sha256']}}
        (folder/'manifest.json').write_text(json.dumps(meta));return meta

    def test_hash_gate_rejects_corruption_unlisted_files_and_unapproved_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);meta=self.bundle(folder)
            verified_bundle(folder) # integrity gate only; fake fixture is never loaded as a model
            (folder/'base/config.json').write_text('corrupt')
            with self.assertRaises(ValueError):verified_bundle(folder)
            (folder/'base/config.json').write_text('{}');(folder/'base/extra.py').write_text('not executed')
            with self.assertRaises(ValueError):verified_bundle(folder)
            meta['approved']=False;(folder/'manifest.json').write_text(json.dumps(meta))
            with self.assertRaises(ValueError):verified_bundle(folder)

    def test_invalid_laya_scores_rejected(self):
        for score in [float('nan'),True,1.1]:
            with self.assertRaises(ValueError):validate_local_ai({'laya':dict(SIGNAL,score=score)})
