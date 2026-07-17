#!/usr/bin/env python3
"""Validate S5300 LTE CA confseq families and their export round trip."""

import argparse
import tempfile
from pathlib import Path

from conf_id import CONF_ID_NAMES
from s5300_confseq import (
    discover_s5300_families,
    document_to_dict,
    export_s5300_bundle,
    load_s5300_bundle,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("confseq_dir", type=Path)
    args = parser.parse_args()

    families = discover_s5300_families(args.confseq_dir)
    if not families:
        raise SystemExit("No complete S5300 LTE CA family found")

    first_conf_id_names = None
    for family in families:
        bundle = load_s5300_bundle(args.confseq_dir, family)
        if first_conf_id_names is None:
            first_conf_id_names = bundle.conf_id_names
        elif bundle.conf_id_names != first_conf_id_names:
            raise SystemExit(f"{family}: conf_id mapping differs between families")
        with tempfile.TemporaryDirectory(prefix=f"{family}-") as temp_dir:
            output_dir = Path(temp_dir)
            export_s5300_bundle(bundle, bundle.document, output_dir)
            reloaded = load_s5300_bundle(output_dir, family)
            if document_to_dict(reloaded.document) != document_to_dict(
                bundle.document
            ):
                raise SystemExit(f"{family}: exported combo data differs")
        print(
            f"{family}: {len(bundle.document.combos)} combos, "
            f"{len(bundle.conf_id_names) - 1} categories from "
            "plmn_mapping_0x13F, 6 profiles, round-trip OK"
        )

    s5300_names = {
        category_id: name
        for category_id, name in first_conf_id_names.items()
        if category_id != 0
    }
    pixel9_names = {
        category_id: name
        for category_id, name in CONF_ID_NAMES.items()
        if category_id != 0
    }
    shared_ids = sorted(set(s5300_names) & set(pixel9_names))
    mismatches = [
        category_id
        for category_id in shared_ids
        if s5300_names[category_id] != pixel9_names[category_id]
    ]
    if mismatches:
        raise SystemExit(f"Pixel 9 shared conf_id names differ: {mismatches}")
    print(
        f"Pixel 9 alignment: {len(shared_ids)} shared IDs have identical names; "
        f"S5300-only={sorted(set(s5300_names) - set(pixel9_names))}; "
        f"Pixel-9-only={sorted(set(pixel9_names) - set(s5300_names))}"
    )


if __name__ == "__main__":
    main()
