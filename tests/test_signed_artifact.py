import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('accept_signed_app', Path(__file__).resolve().parents[1] / 'scripts/accept_signed_app.py')
signing = importlib.util.module_from_spec(spec); spec.loader.exec_module(signing)


class SignedArtifactTests(unittest.TestCase):
    def fixture(self, root):
        a, b = root / 'original', root / 'signed'
        for folder in (a, b):
            folder.mkdir()
            (folder / 'app.asar').write_bytes(b'exact application and design')
            (folder / 'Chickadee.exe').write_bytes(b'MZ' + b'x' * 100)
        return a, b

    def test_signed_native_replacement_preserves_application(self):
        with tempfile.TemporaryDirectory() as folder:
            a, b = self.fixture(Path(folder))
            (b / 'Chickadee.exe').write_bytes(b'MZ' + b'x' * 100 + b'signature')
            signing.accept(a, b)
            self.assertEqual((a / 'Chickadee.exe').read_bytes(), (b / 'Chickadee.exe').read_bytes())
            self.assertEqual((a / 'app.asar').read_bytes(), b'exact application and design')

    def test_application_mutation_and_file_injection_rejected_before_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            a, b = self.fixture(Path(folder))
            original = (a / 'Chickadee.exe').read_bytes()
            (b / 'app.asar').write_bytes(b'changed design or code')
            with self.assertRaisesRegex(ValueError, 'code or data'): signing.accept(a, b)
            self.assertEqual((a / 'Chickadee.exe').read_bytes(), original)
            (b / 'extra.exe').write_bytes(b'MZ' + b'x' * 100)
            with self.assertRaisesRegex(ValueError, 'file list'): signing.accept(a, b)
            with self.assertRaisesRegex(ValueError, 'separate'): signing.accept(a, a)
