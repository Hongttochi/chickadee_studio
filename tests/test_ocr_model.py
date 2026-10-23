import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from chickadee.ocr_worker import recognition_folder


class OCRModelTests(unittest.TestCase):
    def test_bundled_recognizer_matches_approved_inference_hashes(self):
        folder, label = recognition_folder(Path('unused'))
        self.assertIn('Korean adapted', label)
        self.assertGreater((folder/'inference.pdiparams').stat().st_size, 1_000_000)

    def test_no_candidate_or_unapproved_candidate_keeps_official_model(self):
        with tempfile.TemporaryDirectory() as directory:
            official = Path('official')
            self.assertEqual(recognition_folder(official,directory)[0],official)
            Path(directory,'manifest.json').write_text('{"approved_for_app":false}')
            self.assertEqual(recognition_folder(official,directory)[0],official)

    def test_corrupted_or_unknown_candidate_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);files=[]
            for name in ('inference.json','inference.pdiparams','inference.yml'):
                data=name.encode();(folder/name).write_bytes(data)
                files.append({'name':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
            value={'approved_for_app':True,'model':'korean_PP-OCRv5_mobile_rec','validation':{'passed':True},'files':files}
            manifest=folder/'manifest.json';manifest.write_text(json.dumps(value))
            self.assertEqual(recognition_folder(Path('official'),folder)[0],folder)
            (folder/'inference.pdiparams').write_bytes(b'corrupted')
            with self.assertRaises(ValueError):recognition_folder(Path('official'),folder)
            value['files'][0]['name']='../inference.json';manifest.write_text(json.dumps(value))
            with self.assertRaises(ValueError):recognition_folder(Path('official'),folder)
