import asyncio
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, AsyncMock

from chickadee.bridge import DesktopBridge
from chickadee.runtime import environment, GIB, probe_png
from chickadee.scanner import _State, _inspect_images
from chickadee.detection import DEFAULT_RULES


class RuntimeTests(unittest.TestCase):
    def test_auto_recommendation_and_explicit_override(self):
        with patch('chickadee.runtime.memory_info', return_value={'total_bytes': 8*GIB, 'available_bytes': GIB}):
            auto = environment('auto'); standard = environment('standard')
        self.assertEqual(auto['effective_mode'], 'economy')
        self.assertFalse(auto['features']['ocr_enabled'])
        self.assertEqual(standard['effective_mode'], 'standard')
        self.assertTrue(standard['features']['ocr_enabled'])
        with self.assertRaises(ValueError): environment('max-gpu')

    def test_unknown_memory_is_not_invented(self):
        with patch('chickadee.runtime.memory_info', return_value={'total_bytes': None, 'available_bytes': None}), patch('chickadee.runtime.os.cpu_count', return_value=4):
            result = environment()
        self.assertIsNone(result['hardware']['total_bytes'])
        self.assertEqual(result['inference_device'], 'cpu')
        self.assertNotIn('gpu', result['hardware'])

    def test_mode_persistence_and_running_scan_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            bridge = DesktopBridge(directory, lambda _: None)
            result = bridge.command('runtime-configure', {'mode': 'economy'})
            self.assertFalse(result['features']['ocr_enabled'])
            self.assertEqual(DesktopBridge(directory, lambda _: None).runtime_mode, 'economy')
            for bad in ({'mode': 'bad'}, {'mode': 'standard', 'api_key': 'ignored'}):
                with self.assertRaises(ValueError): bridge.command('runtime-configure', bad)
            bridge.busy.set()
            with self.assertRaises(ValueError): bridge.command('runtime-configure', {'mode': 'standard'})
            self.assertEqual(bridge.runtime_mode, 'economy')

    def test_economy_never_fetches_or_runs_ocr_and_counts_unique_skips(self):
        state = _State(ocr_enabled=False)
        images = [{'location': 'img#one', 'source_url': 'https://example.invalid/image.png'}]
        with patch('chickadee.scanner._fetch_image_bounded', new_callable=AsyncMock) as fetch, patch.object(state.ocr, 'recognize', new_callable=AsyncMock) as recognize:
            asyncio.run(_inspect_images(None, images, '', 'https://example.invalid/', state, lambda _: None, DEFAULT_RULES))
            asyncio.run(_inspect_images(None, images, '', 'https://example.invalid/', state, lambda _: None, DEFAULT_RULES))
            fetch.assert_not_called(); recognize.assert_not_called()
        self.assertEqual(state.ocr_skipped, 1)
        self.assertEqual(state.ocr_images, [])

    def test_real_offline_ocr_capability_check(self):
        self.assertTrue(probe_png().startswith(b'\x89PNG'))
        with tempfile.TemporaryDirectory() as directory:
            bridge = DesktopBridge(directory, lambda _: None)
            bridge.command('runtime-test', {}); bridge.runtime_worker.join(35)
            if bridge.runtime_worker.is_alive():
                bridge.runtime_stop.set(); bridge.runtime_worker.join(5)
                self.fail('OCR capability probe exceeded its deadline')
            result = bridge.command('runtime-info', {})['ocr_check']
            self.assertEqual(result['status'], 'completed', result)
            self.assertEqual(result['network_requests'], 0)

    def test_app_models_do_not_import_numpy_or_training_libraries(self):
        code = "from chickadee.local_ai import prepare_models,text_analysis; import sys; prepare_models(); text_analysis('casino join'); assert not {'numpy','sklearn','joblib'} & set(sys.modules)"
        process = subprocess.run([sys.executable, '-c', code], cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=15)
        self.assertEqual(process.returncode, 0, process.stderr.decode('utf-8', errors='replace'))
