import re
from itertools import combinations, product
from typing import Optional

from utils import (
    ALLOWED_LOW_BAND_MIXES,
    Component,
    Combo,
    ComboDocument,
    decode_bw_class,
    dl_base_signature,
)

SUPPORTED_LTE_BANDS = {1, 2, 3, 4, 5, 7, 8, 12, 13, 14, 17, 18, 19, 20, 21, 25,
                       26, 28, 29, 30, 32, 38, 39, 40, 41, 42, 46, 48, 66, 71, 75}

LOW_BANDS = {5, 8, 12, 13, 14, 17, 18, 19, 20, 26, 28, 29, 71}
TDD_BANDS = {38, 39, 40, 41, 42, 48}
NO_4X4_BANDS = LOW_BANDS | {21}

MAX_DL_SPATIAL_STREAMS = 24

CLASS_BASE = {
    "A": 32768,
    "B": 16384,
    "C": 8192,
    "D": 4096,
    "E": 2048,
    "F": 1024,
}

CLASS_CC_COUNT = {
    "A": 1,
    "B": 2,
    "C": 2,
    "D": 3,
    "E": 4,
    "F": 5,
}

CLASS_RANK = {
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "E": 5,
    "F": 6,
}

LOWER_CLASS_VARIANTS = {
    "A": ("A",),
    "B": ("A", "B"),
    "C": ("A", "C"),
    "D": ("A", "C", "D"),
    "E": ("A", "C", "D", "E"),
    "F": ("A", "C", "D", "E", "F"),
}


ExclusionRule = tuple[
    str,
    int,
    Optional[str],
]


def _class_letter(
    raw_value: int,
) -> str:
    class_letter, _mimo = decode_bw_class(
        raw_value
    )

    return class_letter


def parse_band_list(
    text: str,
) -> set[int]:
    values: set[int] = set()

    for token in re.split(
        r"[\s,]+",
        text.strip(),
    ):
        if not token:
            continue

        if not token.isdigit():
            raise ValueError(
                f"Invalid LTE band: {token}"
            )

        band = int(token)

        if band <= 0:
            raise ValueError(
                f"Invalid LTE band: {token}"
            )

        values.add(band)

    if not values:
        raise ValueError(
            "Enter at least one LTE band"
        )

    return values


def class_is_at_or_above(
    raw_value: int,
    minimum_class: str,
) -> bool:
    if raw_value == 0:
        return False

    actual_class = _class_letter(
        raw_value
    )

    if actual_class not in CLASS_RANK:
        return False

    if minimum_class not in CLASS_RANK:
        return False

    return (
        CLASS_RANK[actual_class]
        >= CLASS_RANK[minimum_class]
    )


def parse_exclusions(
    text: str,
) -> list[ExclusionRule]:
    rules: list[ExclusionRule] = []

    for raw_token in text.split(","):
        token = re.sub(
            r"\s+",
            "",
            raw_token,
        ).upper()

        if not token:
            continue

        repeated_match = re.fullmatch(
            r"(\d+)\+(\d+)",
            token,
        )

        if repeated_match:
            left_band = int(
                repeated_match.group(1)
            )

            right_band = int(
                repeated_match.group(2)
            )

            if left_band != right_band:
                raise ValueError(
                    "Only repeated intra-band "
                    "patterns are supported: "
                    f"{raw_token.strip()}"
                )

            rules.append(
                (
                    "repeat",
                    left_band,
                    None,
                )
            )

            continue

        class_match = re.fullmatch(
            r"(\d+)([A-F])",
            token,
        )

        if class_match:
            band = int(
                class_match.group(1)
            )

            minimum_excluded_class = (
                class_match.group(2)
            )

            rules.append(
                (
                    "class_or_higher",
                    band,
                    minimum_excluded_class,
                )
            )

            continue

        raise ValueError(
            f"Invalid exclusion: "
            f"{raw_token.strip()}\n"
            "Use entries such as "
            "3+3, 40D, or 41E."
        )

    return rules


def combo_matches_exclusion(
    combo: Combo,
    rules: list[ExclusionRule],
) -> bool:
    for rule_type, band, class_letter in rules:
        if rule_type == "repeat":
            occurrence_count = sum(
                1
                for component
                in combo.components
                if component.band == band
            )

            if occurrence_count >= 2:
                return True

        elif rule_type == "class_or_higher":
            if class_letter is None:
                continue

            for component in combo.components:
                if component.band != band:
                    continue

                dl_excluded = (
                    class_is_at_or_above(
                        component.bwClassMimoDl,
                        class_letter,
                    )
                )

                ul_excluded = (
                    class_is_at_or_above(
                        component.bwClassMimoUl,
                        class_letter,
                    )
                )

                if dl_excluded or ul_excluded:
                    return True

    return False


def apply_band_filter(
    document: ComboDocument,
    allowed_bands: set[int],
    rules: list[ExclusionRule],
) -> int:
    kept_combos: list[Combo] = []
    removed_count = 0

    for combo in document.combos:
        contains_disallowed_band = any(
            component.band
            not in allowed_bands
            for component
            in combo.components
        )

        if contains_disallowed_band:
            removed_count += 1
            continue

        if combo_matches_exclusion(
            combo,
            rules,
        ):
            removed_count += 1
            continue

        kept_combos.append(
            combo
        )

    document.combos = kept_combos

    return removed_count


# Direct Class-B input is now accepted.
#
# Examples:
#
#   1+8B
#   1+1+8B+40D
#   3B+7+41C
#
# A missing class still means Class A.
def parse_custom_combo(
    text: str,
) -> list[tuple[int, str]]:
    compact = re.sub(
        r"\s+",
        "",
        text,
    ).upper()

    if not compact:
        raise ValueError(
            "Enter a theoretical LTE "
            "combination"
        )

    result: list[
        tuple[int, str]
    ] = []

    for token in compact.split("+"):
        match = re.fullmatch(
            r"(\d+)([A-F]?)",
            token,
        )

        if not match:
            raise ValueError(
                "Invalid custom-combo "
                f"component: {token}"
            )

        band = int(
            match.group(1)
        )

        class_letter = (
            match.group(2)
            or "A"
        )

        if band not in SUPPORTED_LTE_BANDS:
            raise ValueError(
                f"Unsupported LTE band: {band}"
            )

        result.append(
            (
                band,
                class_letter,
            )
        )

    if len(result) < 2:
        raise ValueError(
            "The theoretical combination "
            "must contain at least two "
            "components"
        )

    return result


def combo_cc_count(
    components: list[
        tuple[int, str]
    ],
) -> int:
    return sum(
        CLASS_CC_COUNT[class_letter]
        for _band, class_letter
        in components
    )


def valid_low_band_mix(
    components: list[
        tuple[int, str]
    ],
) -> bool:
    bands = {
        band
        for band, _class_letter
        in components
    }

    present_low_bands = (
        bands & LOW_BANDS
    )

    if len(present_low_bands) <= 1:
        return True

    return (
        frozenset(present_low_bands)
        in ALLOWED_LOW_BAND_MIXES
    )


def valid_duplex_mix(
    components: list[
        tuple[int, str]
    ],
    allow_fdd_tdd: bool,
) -> bool:
    bands = {
        band
        for band, _class_letter
        in components
    }

    contains_tdd = bool(
        bands & TDD_BANDS
    )

    contains_fdd = bool(
        bands - TDD_BANDS
    )

    if (
        not allow_fdd_tdd
        and contains_tdd
        and contains_fdd
    ):
        return False

    return True


def valid_dl_band_mix(
    components: list[
        tuple[int, str]
    ],
    allow_fdd_tdd: bool,
) -> bool:
    if not valid_low_band_mix(
        components
    ):
        return False

    if not valid_duplex_mix(
        components,
        allow_fdd_tdd,
    ):
        return False

    return True


def class_choices_for_maximum(
    class_letter: str,
) -> tuple[str, ...]:
    try:
        return LOWER_CLASS_VARIANTS[
            class_letter
        ]

    except KeyError as exc:
        raise ValueError(
            "Unsupported maximum class: "
            f"{class_letter}"
        ) from exc


def expand_class_variants(
    maximum_components: list[
        tuple[int, str]
    ],
) -> set[
    tuple[
        tuple[int, str],
        ...,
    ]
]:
    component_options: list[
        tuple[
            tuple[int, str],
            ...,
        ]
    ] = []

    for band, maximum_class in (
        maximum_components
    ):
        choices = tuple(
            (
                band,
                class_letter,
            )
            for class_letter
            in class_choices_for_maximum(
                maximum_class
            )
        )

        component_options.append(
            choices
        )

    return {
        tuple(variant)
        for variant in product(
            *component_options
        )
    }


def make_dl_value(
    band: int,
    class_letter: str,
) -> int:
    try:
        base_value = CLASS_BASE[
            class_letter
        ]

    except KeyError as exc:
        raise ValueError(
            "Unsupported bandwidth class: "
            f"{class_letter}"
        ) from exc

    if band in NO_4X4_BANDS:
        return base_value

    return base_value | 1


def build_components(
    variant: list[
        tuple[int, str]
    ],
) -> list[Component]:
    return [
        Component(
            band=band,
            bwClassMimoDl=make_dl_value(
                band,
                class_letter,
            ),
            bwClassMimoUl=0,
        )
        for band, class_letter
        in variant
    ]

# Count the total DL spatial streams.
def component_dl_stream_count(
    component: Component,
) -> int:
    class_letter, mimo = decode_bw_class(
        component.bwClassMimoDl
    )

    if class_letter not in CLASS_CC_COUNT:
        return 0

    return (
        CLASS_CC_COUNT[class_letter]
        * mimo
    )


def total_dl_spatial_streams(
    components: list[Component],
) -> int:
    return sum(
        component_dl_stream_count(
            component
        )
        for component in components
    )


def copy_components(
    components: list[Component],
) -> list[Component]:
    return [
        Component(
            band=component.band,
            bwClassMimoDl=(
                component.bwClassMimoDl
            ),
            bwClassMimoUl=(
                component.bwClassMimoUl
            ),
        )
        for component in components
    ]

# If a combo exceeds 24 streams, generate every, create mimo downgrade variants
#
# Example:
#
#   1C + 3C + 7C + 28
#
# Too many streams:
#
#   4+4 + 4+4 + 4+4 + 2 = 26
#
# Becomes:
#
#   2+2 + 4+4 + 4+4 + 2 = 22
#   4+4 + 2+2 + 4+4 + 2 = 22
#   4+4 + 4+4 + 2+2 + 2 = 22 etc
def expand_mimo_limited_variants(
    components: list[Component],
    maximum_streams: int = (
        MAX_DL_SPATIAL_STREAMS
    ),
) -> list[list[Component]]:
    current_streams = total_dl_spatial_streams(
        components
    )

    if current_streams <= maximum_streams:
        return [
            copy_components(
                components
            )
        ]

    four_by_four_indices = [
        index
        for index, component
        in enumerate(components)
        if (
            component.bwClassMimoDl != 0
            and component.bwClassMimoDl & 1
        )
    ]

    if not four_by_four_indices:
        return []

    for downgrade_count in range(
        1,
        len(four_by_four_indices) + 1,
    ):
        valid_variants: list[
            list[Component]
        ] = []

        for indices_to_downgrade in combinations(
            four_by_four_indices,
            downgrade_count,
        ):
            candidate = copy_components(
                components
            )

            for component_index in (
                indices_to_downgrade
            ):
                candidate[
                    component_index
                ].bwClassMimoDl &= ~1

            if (
                total_dl_spatial_streams(
                    candidate
                )
                <= maximum_streams
            ):
                valid_variants.append(
                    candidate
                )

        """Stop at the first downgrade count that produces
        at least one legal configuration. This ensures only
        minimally downgraded variants are generated."""
        if valid_variants:
            return valid_variants

    return []

def component_dl_signature(
    components: list[Component],
) -> tuple:
    return tuple(
        sorted(
            (
                component.band,
                component.bwClassMimoDl,
            )
            for component in components
        )
    )


def _document_defaults(
    document: ComboDocument,
) -> tuple[int, int, int]:
    template = (
        document.combos[0]
        if document.combos
        else None
    )

    if template is not None:
        return (
            template.bcs,
            template.configMaskLow,
            template.configMaskHigh,
        )

    return (
        2147483648,
        1,
        0,
    )



#   8+8  -> repeated Class-A components only
#   8B   -> generates both 8A and 8B
def generate_custom_combos(
    document: ComboDocument,
    theoretical: list[
        tuple[int, str]
    ],
    max_cc: int,
    allow_fdd_tdd: bool,
    default_bcs: Optional[int] = None,
) -> tuple[int, int, set[tuple]]:
    if max_cc not in range(
        2,
        8,
    ):
        raise ValueError(
            "Max CC must be between 2 and 7"
        )

    existing_dl_signatures = {
        dl_base_signature(combo)
        for combo in document.combos
    }

    generated_signatures: set[
        tuple
    ] = set()

    additions: list[
        Combo
    ] = []

    skipped_existing_count = 0

    (
        inherited_bcs,
        default_conf_low,
        default_conf_high,
    ) = _document_defaults(
        document
    )

    generated_bcs = (
        inherited_bcs
        if default_bcs is None
        else int(default_bcs)
    )

    if not 0 <= generated_bcs <= 0xFFFFFFFF:
        raise ValueError(
            "Default BCS doesn't fit uint32"
        )

    theoretical_length = len(
        theoretical
    )

    for subset_size in range(
        1,
        theoretical_length + 1,
    ):
        for index_subset in combinations(
            range(theoretical_length),
            subset_size,
        ):
            maximum_subset = [
                theoretical[index]
                for index in index_subset
            ]

            for expanded_subset in (
                expand_class_variants(
                    maximum_subset
                )
            ):
                variant = list(
                    expanded_subset
                )

                represented_cc_count = (
                    combo_cc_count(
                        variant
                    )
                )

                if not (
                    2
                    <= represented_cc_count
                    <= max_cc
                ):
                    continue

                if not valid_dl_band_mix(
                    variant,
                    allow_fdd_tdd,
                ):
                    continue

                normal_components = build_components(
                    variant
                )

                mimo_variants = (
                    expand_mimo_limited_variants(
                        normal_components
                    )
                )

                for components in mimo_variants:
                    signature = (
                        component_dl_signature(
                            components
                        )
                    )

                    if (
                        signature
                        in generated_signatures
                    ):
                        continue

                    generated_signatures.add(
                        signature
                    )

                    if (
                        signature
                        in existing_dl_signatures
                    ):
                        skipped_existing_count += 1
                        continue

                    additions.append(
                        Combo(
                            components=components,
                            bcs=generated_bcs,
                            configMaskLow=(
                                default_conf_low
                            ),
                            configMaskHigh=(
                                default_conf_high
                            ),
                        )
                    )

                    existing_dl_signatures.add(
                        signature
                    )
                    
    document.combos.extend(
        additions
    )

    return (
        len(additions),
        skipped_existing_count,
        generated_signatures,
    )
