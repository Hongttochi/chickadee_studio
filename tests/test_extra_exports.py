import copy,json,tempfile,unittest
from pathlib import Path
from chickadee.exports import extra_result
from chickadee.scanner import ScanOutcome
ROOT=Path(__file__).resolve().parents[1]
class ExtraExportTests(unittest.TestCase):
 def test_extra_is_separate_and_never_confirms_unreviewed_advertising(self):
  result=json.loads((ROOT/'examples/result.empty.json').read_text(encoding='utf8'))
  original=copy.deepcopy(result)
  candidate={'id':'c1','url':'https://example.invalid/a','location':'article > p','category':'GAMBLING','evidence_text':'원문\n보존'}
  report={'status':'completed','pages_scanned':[],'errors':[],'ad_candidates':[candidate,copy.deepcopy(candidate)]}
  extra=extra_result(result,report)
  self.assertEqual(len(extra['findings']),1)
  f=extra['findings'][0]
  self.assertEqual(f['technique'],'ETC');self.assertFalse(f['is_violation'])
  self.assertEqual(f['evidence_text'],candidate['evidence_text']);self.assertIn('검토',f['extra_finding'])
  self.assertEqual(result,original)
  with tempfile.TemporaryDirectory() as folder:
   p=ScanOutcome(result,report).save(Path(folder));raw=p.with_name('result_extra.json').read_bytes()
   self.assertFalse(raw.startswith(b'\xef\xbb\xbf'));self.assertEqual(json.loads(raw),extra)
   self.assertEqual(json.loads(p.read_bytes()),original)
 def test_empty_extra_retains_required_meta_and_findings(self):
  result=json.loads((ROOT/'examples/result.empty.json').read_text(encoding='utf8'))
  extra=extra_result(result,{})
  self.assertEqual(set(extra),{'meta','findings'});self.assertEqual(extra['findings'],[])
if __name__=='__main__':unittest.main()
