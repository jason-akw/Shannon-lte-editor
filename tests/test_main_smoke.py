import tkinter as tk
import unittest

from main import ComboEditorApp


class MainWindowSmokeTests(unittest.TestCase):
    def test_main_window_builds_with_s5300_actions(self):
        try:
            app = ComboEditorApp()
        except tk.TclError as exc:
            self.skipTest(f"Tk display is unavailable: {exc}")
        try:
            app.withdraw()
            self.assertTrue(callable(app.import_s5300_confseq_folder))
            self.assertTrue(callable(app.export_s5300_confseq_folder))
            self.assertTrue(callable(app.import_s5300_json))
            self.assertTrue(callable(app.export_s5300_json))
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
