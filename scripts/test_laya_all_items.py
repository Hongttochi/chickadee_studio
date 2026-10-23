"""Exercise every source through the actual shipped CPU worker; no paid provider."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from chickadee.laya_review import review_sources


async def check(app):
    resources=app.parent/'resources'
    os.environ.update(CHICKADEE_LAYA_WORKER=str(resources/'laya/ChickadeeLaya.exe'),
                      CHICKADEE_LAYA_MODEL_DIR=str(resources/'laya-model'))
    sources=[{'text':f'도서관 문화 강좌 {n}회 안내입니다. 신청 기간과 이용 시간을 확인해 주세요.'} for n in range(25)]
    sources.extend([{'text':sources[0]['text']},{'text':''}])
    progress=[];started=time.monotonic()
    real_spawn=asyncio.create_subprocess_exec
    with patch('asyncio.create_subprocess_exec',wraps=real_spawn) as spawned:
        summary=await review_sources(sources,emit=progress.append,timeout_seconds=180)
    assert summary['status']=='completed',summary
    assert summary['analyzed']==25 and summary['covered']==26,summary
    assert summary['omitted']==0 and summary['item_limit'] is None,summary
    assert summary['skipped_empty']==1 and summary['paid_requests']==0,summary
    assert spawned.call_count==1,spawned.call_count
    assert [e['processed'] for e in progress if e.get('action')=='progress']==[12,24,25],progress
    assert all(s['local_ai']['laya']['status']=='completed' for s in sources[:-1])
    result={'status':'passed','actual_cpu_worker':True,'model_processes':spawned.call_count,
            'elapsed_seconds':round(time.monotonic()-started,3),**summary}
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--app',required=True,type=Path);args=p.parse_args()
    asyncio.run(check(args.app.resolve()))
