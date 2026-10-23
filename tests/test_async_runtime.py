import unittest
from unittest.mock import Mock, patch
from chickadee.async_runtime import event_loop_runner


class RunnerTests(unittest.TestCase):
    def error(self, code):
        error = OSError('initialization failed'); error.winerror = code; return error

    def test_only_initialization_is_retried(self):
        first, second = Mock(), Mock()
        first.get_loop.side_effect = self.error(10014)
        with patch('chickadee.async_runtime.asyncio.Runner', side_effect=[first, second]) as factory, patch('chickadee.async_runtime.time.sleep'):
            with event_loop_runner() as runner: self.assertIs(runner, second)
        self.assertEqual(factory.call_count, 2)
        first.close.assert_called_once(); second.close.assert_called_once()

    def test_work_is_never_retried(self):
        runner = Mock()
        with patch('chickadee.async_runtime.asyncio.Runner', return_value=runner) as factory:
            with self.assertRaises(OSError):
                with event_loop_runner(): raise self.error(10014)
        factory.assert_called_once(); runner.close.assert_called_once()

    def test_other_errors_and_retry_limit_are_preserved(self):
        for code, attempts in [(10013, 1), (10014, 5)]:
            runner = Mock(); runner.get_loop.side_effect = self.error(code)
            with patch('chickadee.async_runtime.asyncio.Runner', return_value=runner) as factory, patch('chickadee.async_runtime.time.sleep'):
                with self.assertRaises(OSError):
                    with event_loop_runner(): self.fail('Work must not start')
                self.assertEqual(factory.call_count, attempts)
