import tkinter as tk
import unittest

from main import ComboEditorApp
from s5300_confseq import S5300_UL_AUTO_VALUE
from tools_ui import ConfIdDialog
from utils import Combo, Component


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
            dialog = ConfIdDialog(
                parent=app,
                document=app.document,
                conf_id_names={0: "Default", 31: "WILDCARD"},
            )
            try:
                dialog.withdraw()
                self.assertEqual(
                    dialog.conf_id_names,
                    {0: "Default", 31: "WILDCARD"},
                )
            finally:
                dialog.destroy()
        finally:
            app.destroy()

    def test_s5300_auto_pcc_expands_to_each_band_in_the_ui(self):
        try:
            app = ComboEditorApp()
        except tk.TclError as exc:
            self.skipTest(f"Tk display is unavailable: {exc}")
        try:
            app.withdraw()
            app.s5300_family = "lte_ca"
            combo = Combo(components=[
                Component(
                    band=band,
                    bwClassMimoDl=32768,
                    bwClassMimoUl=S5300_UL_AUTO_VALUE,
                )
                for band in (1, 3, 7, 28)
            ])

            row = app._combo_row_values(0, combo)
            self.assertEqual(row[3], "Auto PCC (1 / 3 / 7 / 28)")
            self.assertEqual(row[5], 1)

            app._set_component_ul_value(combo, 2, 32768)
            self.assertEqual(
                [item.bwClassMimoUl for item in combo.components],
                [0, 0, 32768, 0],
            )

            app._set_component_ul_value(combo, 0, S5300_UL_AUTO_VALUE)
            self.assertEqual(
                [item.bwClassMimoUl for item in combo.components],
                [S5300_UL_AUTO_VALUE] * 4,
            )
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
