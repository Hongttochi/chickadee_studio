from pathlib import Path
import tempfile
import time
import tkinter as tk
import unittest

from chickadee.gui import Application


class GuiTests(unittest.TestCase):
    def test_start_filter_detail_and_saved_result(self):
        with tempfile.TemporaryDirectory() as folder:
            root = tk.Tk()
            root.withdraw()
            app = Application(root, Path(folder), demo=True)
            try:
                app.start()
                deadline = time.monotonic() + 50
                while app.outcome is None and time.monotonic() < deadline:
                    root.update()
                    time.sleep(0.02)
                self.assertIsNotNone(app.outcome, app.status.get())
                self.assertEqual(app.outcome.report["status"], "completed")
                self.assertEqual(len(app.table.get_children()), 14)
                self.assertTrue((Path(folder) / "result.json").exists())
                app.filter.set("JAMO")
                app.refresh()
                self.assertEqual(len(app.table.get_children()), 4)
                app.table.selection_set(app.table.get_children()[0])
                app.show_detail()
                self.assertIn("위치:", app.detail.get("1.0", "end"))
                self.assertIn("원문:", app.detail.get("1.0", "end"))
            finally:
                app.stop.set()
                if app.worker:
                    app.worker.join(timeout=20)
                if app.demo_site:
                    app.demo_site.close()
                root.destroy()
