import tempfile
import unittest
from pathlib import Path

from s5300_confseq import (
    CONFSEQ_MESSAGE,
    Clz4Metadata,
    S5300_UL_AUTO_VALUE,
    decode_confseq_blob,
    document_to_dict,
    encode_confseq_blob,
    export_s5300_bundle,
    load_s5300_bundle,
    nv_crc,
)
from utils import Combo, Component, ParseError


FAMILY = "lte_ca"


def append_nv(message, name, values):
    item = message.nvitem.add()
    item.id = nv_crc(name)
    for value in values:
        group = item.item.add()
        if value:
            group.value.append(value)


def append_combo(message, combo_id, combo):
    prefix = f"UECAPA_REL10_CA_COMB_{combo_id}_"
    append_nv(message, prefix + "NUM_BAND", [len(combo.components)])
    append_nv(message, prefix + "BAND", [item.band for item in combo.components])
    append_nv(
        message,
        prefix + "DL_BW_CLASS_BIT_MAP",
        [item.bwClassMimoDl for item in combo.components],
    )
    append_nv(
        message,
        prefix + "UL_BW_CLASS_BIT_MAP",
        [item.bwClassMimoUl for item in combo.components],
    )
    append_nv(message, prefix + "SET_BITMAP", [combo.bcs])
    low = combo.configMaskLow
    if low >= 1 << 63:
        low -= 1 << 64
    append_nv(message, prefix + "CATEGORY_ARRAY", [low, combo.configMaskHigh])


def fixture_combos():
    return [
        Combo(
            components=[
                Component(band=1, bwClassMimoDl=32769, bwClassMimoUl=32768),
                Component(band=3, bwClassMimoDl=32768, bwClassMimoUl=0),
            ],
            bcs=0,
            configMaskLow=(1 << 63) | (1 << 31) | 3,
            configMaskHigh=1 << (82 - 64),
        ),
        Combo(
            components=[Component(band=7, bwClassMimoDl=8192, bwClassMimoUl=8192)],
            bcs=3,
            configMaskLow=4,
            configMaskHigh=2,
        ),
        Combo(
            components=[
                Component(
                    band=1,
                    bwClassMimoDl=32768,
                    bwClassMimoUl=S5300_UL_AUTO_VALUE,
                ),
                Component(
                    band=3,
                    bwClassMimoDl=32768,
                    bwClassMimoUl=S5300_UL_AUTO_VALUE,
                ),
            ],
            bcs=3221225472,
            configMaskLow=1,
            configMaskHigh=0,
        ),
    ]


def write_fixture(directory: Path):
    combos = fixture_combos()
    messages = {}
    for suffix in ("0", "1", "common"):
        message = CONFSEQ_MESSAGE()
        message.Revision = "test-revision"
        message.Name = f"{FAMILY}_{suffix}"
        messages[suffix] = message

    for combo_id, combo in enumerate(combos, start=1):
        append_combo(messages["0"], combo_id, combo)
    append_nv(messages["common"], "UECAPA_REL10_CA_COMB_NUM", [len(combos)])
    append_nv(messages["common"], "TEST_UNRELATED_COMMON_NV", [7, 0])

    metadata = Clz4Metadata(checksum=0x12345678, trailing=b"tail")
    for suffix, message in messages.items():
        for mirror in (False, True):
            output = CONFSEQ_MESSAGE()
            output.ParseFromString(message.SerializeToString())
            if mirror:
                output.Name += ".common"
            raw = encode_confseq_blob(output.SerializeToString(), metadata)
            name = output.Name.replace(".", "_")
            (directory / name).write_bytes(raw)

    plmn = CONFSEQ_MESSAGE()
    plmn.Revision = "test-revision"
    plmn.Name = "plmn_mapping_0x13F"
    append_nv(
        plmn,
        "NRCAPA_CA_NV_PLMN_CATEGORY_ID",
        [1, 2, 3, 31, 63, 65, 82],
    )
    for category_id, name in (
        (1, "VZW"),
        (2, "TMO"),
        (3, "ATT"),
        (31, "WILDCARD"),
        (63, "APAC_COMMON"),
        (65, "1_1_DE"),
        (82, "MX_COMMON"),
    ):
        append_nv(
            plmn,
            f"NRCAPA_CA_NV_PLMN_NAME_FOR_PLMN_CATEGORY_ID_{category_id}",
            name.encode("ascii"),
        )
    for mirror in (False, True):
        output = CONFSEQ_MESSAGE()
        output.ParseFromString(plmn.SerializeToString())
        if mirror:
            output.Name += ".common"
        raw = encode_confseq_blob(output.SerializeToString(), metadata)
        name = output.Name.replace(".", "_")
        (directory / name).write_bytes(raw)


class S5300ConfseqTests(unittest.TestCase):
    def test_raw_bundle_round_trip_preserves_common_nv_and_mirrors(self):
        with tempfile.TemporaryDirectory() as source_name:
            source = Path(source_name)
            write_fixture(source)
            bundle = load_s5300_bundle(source, FAMILY)
            self.assertEqual(
                bundle.conf_id_names,
                {
                    0: "Default",
                    1: "VZW",
                    2: "TMO",
                    3: "ATT",
                    31: "WILDCARD",
                    63: "APAC_COMMON",
                    65: "1_1_DE",
                    82: "MX_COMMON",
                },
            )
            self.assertEqual(document_to_dict(bundle.document)["combos"], [
                {
                    "components": [
                        {"band": 1, "bwClassMimoDl": 32769, "bwClassMimoUl": 32768},
                        {"band": 3, "bwClassMimoDl": 32768, "bwClassMimoUl": 0},
                    ],
                    "bcs": 0,
                    "configMaskLow": (1 << 63) | (1 << 31) | 3,
                    "configMaskHigh": 1 << (82 - 64),
                },
                {
                    "components": [
                        {"band": 7, "bwClassMimoDl": 8192, "bwClassMimoUl": 8192},
                    ],
                    "bcs": 3,
                    "configMaskLow": 4,
                    "configMaskHigh": 2,
                },
                {
                    "components": [
                        {
                            "band": 1,
                            "bwClassMimoDl": 32768,
                            "bwClassMimoUl": S5300_UL_AUTO_VALUE,
                        },
                        {
                            "band": 3,
                            "bwClassMimoDl": 32768,
                            "bwClassMimoUl": S5300_UL_AUTO_VALUE,
                        },
                    ],
                    "bcs": 3221225472,
                    "configMaskLow": 1,
                    "configMaskHigh": 0,
                },
            ])

            bundle.document.combos[0].components[1].bwClassMimoUl = 32768
            bundle.document.combos.append(Combo(
                components=[Component(band=28, bwClassMimoDl=32768, bwClassMimoUl=0)],
                bcs=1,
                configMaskLow=8,
                configMaskHigh=0,
            ))

            with tempfile.TemporaryDirectory() as output_name:
                output = Path(output_name)
                written = export_s5300_bundle(bundle, bundle.document, output)
                self.assertEqual(len(written), 6)
                reloaded = load_s5300_bundle(output, FAMILY)
                self.assertEqual(
                    document_to_dict(reloaded.document),
                    document_to_dict(bundle.document),
                )
                common = reloaded.profiles[f"{FAMILY}_common"].message
                unrelated = next(
                    item
                    for item in common.nvitem
                    if item.id == nv_crc("TEST_UNRELATED_COMMON_NV")
                )
                self.assertEqual(
                    [tuple(group.value) for group in unrelated.item],
                    [(7,), ()],
                )
                for primary in (
                    f"{FAMILY}_0",
                    f"{FAMILY}_1",
                    f"{FAMILY}_common",
                ):
                    left = reloaded.profiles[primary].message
                    right = reloaded.profiles[f"{primary}.common"].message
                    self.assertEqual(
                        [item.SerializeToString() for item in left.nvitem],
                        [item.SerializeToString() for item in right.nvitem],
                    )

                data, metadata = decode_confseq_blob(written[0].read_bytes())
                self.assertTrue(data)
                self.assertEqual(metadata.checksum, 0x12345678)
                self.assertEqual(metadata.trailing, b"tail")

    def test_unknown_segment_nv_is_rejected(self):
        with tempfile.TemporaryDirectory() as source_name:
            source = Path(source_name)
            write_fixture(source)
            for profile_name in (f"{FAMILY}_0", f"{FAMILY}_0_common"):
                profile_path = source / profile_name
                data, metadata = decode_confseq_blob(profile_path.read_bytes())
                message = CONFSEQ_MESSAGE()
                message.ParseFromString(data)
                append_nv(message, "UNRELATED_SEGMENT_NV", [1])
                profile_path.write_bytes(
                    encode_confseq_blob(message.SerializeToString(), metadata)
                )

            with self.assertRaisesRegex(ParseError, "not a pure LTE combo segment"):
                load_s5300_bundle(source, FAMILY)

    def test_auto_pcc_marker_cannot_be_mixed_with_explicit_ul(self):
        with tempfile.TemporaryDirectory() as source_name:
            source = Path(source_name)
            write_fixture(source)
            bundle = load_s5300_bundle(source, FAMILY)
            bundle.document.combos[2].components[1].bwClassMimoUl = 0

            with tempfile.TemporaryDirectory() as output_name:
                with self.assertRaisesRegex(ValueError, "mixes the S5300 Auto PCC"):
                    export_s5300_bundle(
                        bundle,
                        bundle.document,
                        Path(output_name),
                    )


if __name__ == "__main__":
    unittest.main()
