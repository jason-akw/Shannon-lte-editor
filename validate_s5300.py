#!/usr/bin/env python3
"""Validate S5300 LTE CA confseq families and their export round trip."""

import argparse
import tempfile
from pathlib import Path

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

    for family in families:
        bundle = load_s5300_bundle(args.confseq_dir, family)
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
            "6 profiles, round-trip OK"
        )


if __name__ == "__main__":
    main()
