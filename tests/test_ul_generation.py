import unittest

from custom_utils import (
    generate_custom_combos,
    valid_low_band_mix,
)
from utils import (
    S5300_UL_AUTO_VALUE,
    VALIDATION_LOW_BAND_MIX,
    VALIDATION_SDL_UL,
    Combo,
    ComboDocument,
    Component,
    auto_fill_ul_bands,
    auto_fill_ulca,
    combo_uses_auto_pcc,
    dl_base_signature,
    fix_validation_issues,
    generate_ul_variants,
    repair_and_deduplicate,
    valid_ul_pair,
    validate_document,
)


def make_combo(bands, ul_values=None):
    if ul_values is None:
        ul_values = [0] * len(bands)

    return Combo(
        components=[
            Component(
                band=band,
                bwClassMimoDl=32768,
                bwClassMimoUl=ul_value,
            )
            for band, ul_value in zip(bands, ul_values)
        ],
        bcs=2147483648,
        configMaskLow=1,
        configMaskHigh=0,
    )


class AutoPccGenerationTests(unittest.TestCase):
    def test_existing_auto_pcc_does_not_generate_single_pcc_variants(self):
        document = ComboDocument(combos=[
            make_combo(
                [1, 3, 7],
                [S5300_UL_AUTO_VALUE] * 3,
            )
        ])

        self.assertEqual(
            auto_fill_ul_bands(
                document,
                supports_auto_pcc=True,
            ),
            0,
        )
        self.assertEqual(len(document.combos), 1)
        self.assertTrue(combo_uses_auto_pcc(document.combos[0]))

        result = generate_ul_variants(
            document,
            selected_index=0,
            include_ulca=False,
            supports_auto_pcc=True,
        )
        self.assertEqual(result.created_count, 0)
        self.assertIn("already covers", result.message)

    def test_auto_pcc_semantics_are_s5300_only(self):
        document = ComboDocument(combos=[
            make_combo(
                [1, 3],
                [S5300_UL_AUTO_VALUE] * 2,
            )
        ])

        self.assertEqual(auto_fill_ul_bands(document), 2)
        self.assertEqual(len(document.combos), 3)

    def test_repair_preserves_valid_auto_pcc(self):
        document = ComboDocument(combos=[
            make_combo(
                [1, 3, 7],
                [S5300_UL_AUTO_VALUE] * 3,
            )
        ])

        repaired, duplicates = repair_and_deduplicate(
            document,
            supports_auto_pcc=True,
        )

        self.assertEqual((repaired, duplicates), (0, 0))
        self.assertEqual(len(document.combos), 1)
        self.assertTrue(combo_uses_auto_pcc(document.combos[0]))

    def test_validation_fix_preserves_valid_auto_pcc(self):
        document = ComboDocument(combos=[
            make_combo(
                [1, 3, 7],
                [S5300_UL_AUTO_VALUE] * 3,
            )
        ])

        results = fix_validation_issues(
            document,
            supports_auto_pcc=True,
        )

        self.assertEqual(results["missing_ul_filled"], 0)
        self.assertEqual(results["invalid_ul_removed"], 0)
        self.assertEqual(len(document.combos), 1)
        self.assertTrue(combo_uses_auto_pcc(document.combos[0]))

    def test_auto_pcc_option_preserves_the_no_ul_combo(self):
        original = make_combo([1, 3, 7])
        document = ComboDocument(combos=[original])

        self.assertEqual(
            auto_fill_ul_bands(
                document,
                use_auto_pcc=True,
                supports_auto_pcc=True,
            ),
            1,
        )
        self.assertEqual(len(document.combos), 2)
        self.assertIs(document.combos[0], original)
        self.assertEqual(
            [
                component.bwClassMimoUl
                for component in document.combos[0].components
            ],
            [0, 0, 0],
        )
        self.assertTrue(combo_uses_auto_pcc(document.combos[1]))

    def test_auto_pcc_keeps_separate_ulca_variants(self):
        document = ComboDocument(combos=[
            make_combo(
                [1, 3],
                [S5300_UL_AUTO_VALUE] * 2,
            )
        ])

        self.assertEqual(
            auto_fill_ulca(
                document,
                allow_fdd_aa_ulca=True,
                use_auto_pcc=True,
                supports_auto_pcc=True,
            ),
            1,
        )
        self.assertEqual(len(document.combos), 2)
        self.assertEqual(
            sum(combo_uses_auto_pcc(combo) for combo in document.combos),
            1,
        )
        self.assertEqual(
            sorted(
                sum(
                    component.bwClassMimoUl != 0
                    for component in combo.components
                )
                for combo in document.combos
                if not combo_uses_auto_pcc(combo)
            ),
            [2],
        )

    def test_band_46_forces_explicit_legal_pcc_fallback(self):
        document = ComboDocument(combos=[make_combo([1, 46])])

        self.assertEqual(
            auto_fill_ul_bands(
                document,
                use_auto_pcc=True,
                supports_auto_pcc=True,
            ),
            1,
        )

        self.assertEqual(len(document.combos), 2)
        self.assertEqual(
            [
                component.bwClassMimoUl
                for component in document.combos[1].components
            ],
            [32768, 0],
        )

    def test_invalid_auto_pcc_with_band_46_is_repaired_atomically(self):
        document = ComboDocument(combos=[
            make_combo(
                [1, 46],
                [S5300_UL_AUTO_VALUE] * 2,
            )
        ])

        repair_and_deduplicate(
            document,
            supports_auto_pcc=True,
        )

        self.assertEqual(
            [
                component.bwClassMimoUl
                for component in document.combos[0].components
            ],
            [32768, 0],
        )

    def test_band_46_uplink_is_reported_by_global_validation(self):
        document = ComboDocument(combos=[
            make_combo([1, 46], [0, 32768])
        ])

        report = validate_document(document)
        self.assertTrue(
            report.issues_of_type(VALIDATION_SDL_UL)
        )


class LowBandWhitelistTests(unittest.TestCase):
    def test_downlink_low_band_whitelist(self):
        self.assertTrue(valid_low_band_mix([(8, "A"), (20, "A")]))
        self.assertTrue(valid_low_band_mix([(20, "A"), (28, "A")]))
        self.assertFalse(valid_low_band_mix([(8, "A"), (28, "A")]))

    def test_ulca_low_band_whitelist(self):
        self.assertTrue(valid_ul_pair(8, 20, allow_fdd_aa_ulca=True))
        self.assertTrue(valid_ul_pair(20, 28, allow_fdd_aa_ulca=True))
        self.assertFalse(valid_ul_pair(8, 28, allow_fdd_aa_ulca=True))

    def test_validation_uses_the_same_low_band_whitelist(self):
        allowed_8_20 = validate_document(
            ComboDocument(combos=[make_combo([8, 20], [32768, 0])])
        )
        allowed_20_28 = validate_document(
            ComboDocument(combos=[make_combo([20, 28], [32768, 0])])
        )
        blocked_8_28 = validate_document(
            ComboDocument(combos=[make_combo([8, 28], [32768, 0])])
        )

        self.assertFalse(
            allowed_8_20.issues_of_type(VALIDATION_LOW_BAND_MIX)
        )
        self.assertFalse(
            allowed_20_28.issues_of_type(VALIDATION_LOW_BAND_MIX)
        )
        self.assertTrue(
            blocked_8_28.issues_of_type(VALIDATION_LOW_BAND_MIX)
        )


class AutoGenerationScopeTests(unittest.TestCase):
    def test_existing_involved_combo_is_in_scope(self):
        involved = make_combo([8, 20])
        unrelated = make_combo([1, 3])
        document = ComboDocument(combos=[involved, unrelated])

        added, skipped, signatures = generate_custom_combos(
            document,
            theoretical=[(8, "A"), (20, "A")],
            max_cc=2,
            allow_fdd_tdd=False,
        )

        self.assertEqual((added, skipped), (0, 1))
        self.assertIn(dl_base_signature(involved), signatures)
        self.assertNotIn(dl_base_signature(unrelated), signatures)

        auto_fill_ulca(
            document,
            allow_fdd_aa_ulca=True,
            target_dl_signatures=signatures,
        )

        unrelated_group = [
            combo
            for combo in document.combos
            if dl_base_signature(combo)
            == dl_base_signature(unrelated)
        ]
        self.assertEqual(unrelated_group, [unrelated])
        self.assertEqual(
            [component.bwClassMimoUl for component in unrelated.components],
            [0, 0],
        )

    def test_new_involved_combo_is_in_scope(self):
        unrelated = make_combo([1, 3])
        document = ComboDocument(combos=[unrelated])

        added, skipped, signatures = generate_custom_combos(
            document,
            theoretical=[(8, "A"), (20, "A")],
            max_cc=2,
            allow_fdd_tdd=False,
        )

        self.assertEqual((added, skipped), (1, 0))

        auto_fill_ulca(
            document,
            allow_fdd_aa_ulca=True,
            target_dl_signatures=signatures,
        )

        unrelated_group = [
            combo
            for combo in document.combos
            if dl_base_signature(combo)
            == dl_base_signature(unrelated)
        ]
        involved_group = [
            combo
            for combo in document.combos
            if dl_base_signature(combo) in signatures
        ]
        self.assertEqual(unrelated_group, [unrelated])
        self.assertGreater(len(involved_group), 1)

    def test_global_scope_adds_variants_for_unrelated_combos(self):
        involved = make_combo([8, 20])
        unrelated = make_combo([1, 3])
        document = ComboDocument(combos=[involved, unrelated])

        auto_fill_ulca(
            document,
            allow_fdd_aa_ulca=True,
            target_dl_signatures=None,
        )

        unrelated_group = [
            combo
            for combo in document.combos
            if dl_base_signature(combo)
            == dl_base_signature(unrelated)
        ]
        self.assertGreater(len(unrelated_group), 1)


if __name__ == "__main__":
    unittest.main()
