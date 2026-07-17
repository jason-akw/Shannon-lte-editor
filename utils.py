import re
from dataclasses import dataclass, field
from itertools import combinations
from typing import List, Optional
from typing import Iterable, List, Optional

try:
    from google.protobuf import (
        descriptor_pb2,
        descriptor_pool,
        message_factory,
    )
except ImportError:
    descriptor_pb2 = None
    descriptor_pool = None
    message_factory = None


# message ShannonLteUECap (new) protobuf schema

def build_shannon_lte_message_class():
    if descriptor_pb2 is None:
        raise RuntimeError(
            "Binary protobuf support requires the protobuf package.\n\n"
            "Install with:\n"
            "pip install protobuf"
        )

    fd = descriptor_pb2.FileDescriptorProto()
    fd.name = "shannon_lte_ue_cap.proto"
    fd.syntax = "proto2"

    component = fd.message_type.add()
    component.name = "Component"

    for name, number in (
        ("band", 1),
        ("bwClassMimoDl", 2),
        ("bwClassMimoUl", 3),
    ):
        field_descriptor = component.field.add()
        field_descriptor.name = name
        field_descriptor.number = number
        field_descriptor.label = (
            descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED
        )
        field_descriptor.type = (
            descriptor_pb2.FieldDescriptorProto.TYPE_INT32
        )

    combo = fd.message_type.add()
    combo.name = "Combo"

    field_descriptor = combo.field.add()
    field_descriptor.name = "components"
    field_descriptor.number = 1
    field_descriptor.label = (
        descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    )
    field_descriptor.type = (
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    )
    field_descriptor.type_name = ".Component"

    field_descriptor = combo.field.add()
    field_descriptor.name = "bcs"
    field_descriptor.number = 2
    field_descriptor.label = (
        descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    )
    field_descriptor.type = (
        descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
    )

    # Binary field 3:
    # conf_id 0 through 63.
    field_descriptor = combo.field.add()
    field_descriptor.name = "configMaskLow"
    field_descriptor.number = 3
    field_descriptor.label = (
        descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED
    )
    field_descriptor.type = (
        descriptor_pb2.FieldDescriptorProto.TYPE_UINT64
    )

    # Binary field 4:
    # conf_id 64 through 95.
    field_descriptor = combo.field.add()
    field_descriptor.name = "configMaskHigh"
    field_descriptor.number = 4
    field_descriptor.label = (
        descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED
    )
    field_descriptor.type = (
        descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
    )

    root = fd.message_type.add()
    root.name = "ShannonLteUECap"

    field_descriptor = root.field.add()
    field_descriptor.name = "version"
    field_descriptor.number = 1
    field_descriptor.label = (
        descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED
    )
    field_descriptor.type = (
        descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
    )

    field_descriptor = root.field.add()
    field_descriptor.name = "combos"
    field_descriptor.number = 2
    field_descriptor.label = (
        descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    )
    field_descriptor.type = (
        descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    )
    field_descriptor.type_name = ".Combo"

    field_descriptor = root.field.add()
    field_descriptor.name = "bitmask"
    field_descriptor.number = 3
    field_descriptor.label = (
        descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED
    )
    field_descriptor.type = (
        descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
    )

    pool = descriptor_pool.DescriptorPool()
    pool.Add(fd)

    descriptor = pool.FindMessageTypeByName(
        "ShannonLteUECap"
    )

    if hasattr(message_factory, "GetMessageClass"):
        return message_factory.GetMessageClass(
            descriptor
        )

    return message_factory.MessageFactory(
        pool
    ).GetPrototype(descriptor)


# value definitions

DL_VALUE_OPTIONS = [
    ("32768", "32768 (A)"),
    ("32769", "32769 (A 4×4)"),
    ("16384", "16384 (B)"),
    ("16385", "16385 (B 4×4)"),
    ("8192", "8192 (C)"),
    ("8193", "8193 (C 4×4)"),
    ("4096", "4096 (D)"),
    ("4097", "4097 (D 4×4)"),
    ("2048", "2048 (E)"),
    ("2049", "2049 (E 4×4)"),
    ("1024", "1024 (F)"),
    ("1025", "1025 (F 4×4)"),
]

UL_VALUE_OPTIONS = [
    ("0", "0 (None)"),
    ("32768", "32768 (A)"),
    ("8192", "8192 (C)"),
    ("4096", "4096 (D)"),
]

BCS_VALUE_OPTIONS = [
    (
        "2147483648",
        "2147483648 (BCS 0)",
    ),
    (
        "3221225472",
        "3221225472 (BCS 0, 1)",
    ),
    (
        "3758096384",
        "3758096384 (BCS 0, 1, 2)",
    ),
    (
        "4026531840",
        "4026531840 (BCS 0, 1, 2, 3)",
    ),
    (
        "4160749568",
        "4160749568 (BCS 0, 1, 2, 3, 4)",
    ),
    (
        "4227858432",
        "4227858432 (BCS 0, 1, 2, 3, 4, 5)",
    ),
]

BCS_VALUE_TO_LABEL = dict(
    BCS_VALUE_OPTIONS
)

BCS_LABEL_TO_VALUE = {
    label: value
    for value, label in BCS_VALUE_OPTIONS
}

DL_VALUE_TO_LABEL = dict(
    DL_VALUE_OPTIONS
)

UL_VALUE_TO_LABEL = dict(
    UL_VALUE_OPTIONS
)

DL_LABEL_TO_VALUE = {
    label: value
    for value, label in DL_VALUE_OPTIONS
}

UL_LABEL_TO_VALUE = {
    label: value
    for value, label in UL_VALUE_OPTIONS
}


@dataclass
class Component:
    band: int = 1
    bwClassMimoDl: int = 32768
    bwClassMimoUl: int = 0


@dataclass
class Combo:
    components: List[Component] = field(
        default_factory=list
    )
    bcs: int = 0

    # internal names
    configMaskLow: int = 0
    configMaskHigh: int = 0


@dataclass
class ComboDocument:
    version: int = 0
    combos: List[Combo] = field(
        default_factory=list
    )
    bitmask: int = 0


class ParseError(ValueError):
    pass


# Text protobuf parsing helpers

def _extract_balanced_blocks(
    text: str,
    keyword: str,
) -> List[str]:
    blocks: List[str] = []

    pattern = re.compile(
        rf"\b{re.escape(keyword)}\s*\{{",
        re.IGNORECASE,
    )

    for match in pattern.finditer(text):
        opening_brace_index = match.end() - 1
        depth = 0

        for index in range(
            opening_brace_index,
            len(text),
        ):
            character = text[index]

            if character == "{":
                depth += 1

            elif character == "}":
                depth -= 1

                if depth == 0:
                    blocks.append(
                        text[
                            opening_brace_index + 1:
                            index
                        ]
                    )
                    break

        else:
            raise ParseError(
                f"Unclosed {keyword} block"
            )

    return blocks


def _read_int(
    text: str,
    field_name: str,
    default: Optional[int] = None,
) -> int:
    match = re.search(
        rf"\b{re.escape(field_name)}\s*:\s*(-?\d+)",
        text,
        re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    if default is not None:
        return default

    raise ParseError(
        f"Missing field: {field_name}"
    )


def _read_int_aliases(
    text: str,
    field_names: tuple[str, ...],
    default: Optional[int] = None,
) -> int:
    """
    Read an integer using any accepted text field name.

    Alias matching is case-insensitive.
    The first matching alias in the text is used.
    """
    escaped_names = "|".join(
        re.escape(name)
        for name in field_names
    )

    match = re.search(
        rf"\b(?:{escaped_names})\s*:\s*(-?\d+)",
        text,
        re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    if default is not None:
        return default

    raise ParseError(
        "Missing field. Expected one of: "
        + ", ".join(field_names)
    )


LOW_MASK_FIELD_ALIASES = (
    "conf_id0to63",
    "configMaskLow",
    "config_mask_low",
    "unknown1",
    "maskLow",
    "lowMask",
    "confId0To63",
    "confId0to63",
)

HIGH_MASK_FIELD_ALIASES = (
    "conf_id64to95",
    "configMaskHigh",
    "config_mask_high",
    "unknown2",
    "maskHigh",
    "highMask",
    "confId64To95",
    "confId64to95",
)


# Text document import

def parse_document(
    text: str,
) -> ComboDocument:
    version = _read_int(
        text,
        "version",
        0,
    )

    bitmask = _read_int(
        text,
        "bitmask",
        0,
    )

    combos: List[Combo] = []

    combo_blocks = _extract_balanced_blocks(
        text,
        "combos",
    )

    for combo_number, combo_text in enumerate(
        combo_blocks,
        start=1,
    ):
        components: List[Component] = []

        component_blocks = (
            _extract_balanced_blocks(
                combo_text,
                "components",
            )
        )

        for component_number, component_text in enumerate(
            component_blocks,
            start=1,
        ):
            try:
                band = _read_int(
                    component_text,
                    "band",
                )

                bw_class_mimo_dl = _read_int(
                    component_text,
                    "bwClassMimoDl",
                    32768,
                )

                bw_class_mimo_ul = _read_int(
                    component_text,
                    "bwClassMimoUl",
                    0,
                )

            except ParseError as exc:
                raise ParseError(
                    "Invalid component "
                    f"{component_number} in combo "
                    f"{combo_number}: {exc}"
                ) from exc

            components.append(
                Component(
                    band=band,
                    bwClassMimoDl=bw_class_mimo_dl,
                    bwClassMimoUl=bw_class_mimo_ul,
                )
            )

        config_mask_low = _read_int_aliases(
            combo_text,
            LOW_MASK_FIELD_ALIASES,
            0,
        )

        config_mask_high = _read_int_aliases(
            combo_text,
            HIGH_MASK_FIELD_ALIASES,
            0,
        )

        if not (
            0
            <= config_mask_low
            <= 0xFFFFFFFFFFFFFFFF
        ):
            raise ParseError(
                "Combo "
                f"{combo_number}: conf_id0to63 "
                "must fit in uint64"
            )

        if not (
            0
            <= config_mask_high
            <= 0xFFFFFFFF
        ):
            raise ParseError(
                "Combo "
                f"{combo_number}: conf_id64to95 "
                "must fit in uint32"
            )

        bcs = _read_int(
            combo_text,
            "bcs",
            0,
        )

        if not 0 <= bcs <= 0xFFFFFFFF:
            raise ParseError(
                f"Combo {combo_number}: "
                "bcs must fit in uint32"
            )

        combos.append(
            Combo(
                components=components,
                bcs=bcs,
                configMaskLow=config_mask_low,
                configMaskHigh=config_mask_high,
            )
        )

    return ComboDocument(
        version=version,
        combos=combos,
        bitmask=bitmask,
    )


# Binary protobuf import

def parse_binary_document(
    data: bytes,
) -> ComboDocument:
    message_class = (
        build_shannon_lte_message_class()
    )

    message = message_class()

    try:
        message.ParseFromString(data)
    except Exception as exc:
        raise ParseError(
            "Could not parse binary protobuf: "
            f"{exc}"
        ) from exc

    if not message.IsInitialized():
        missing_fields = ", ".join(
            message.FindInitializationErrors()
        )

        raise ParseError(
            "Binary protobuf is missing required "
            f"fields: {missing_fields}"
        )

    document = ComboDocument(
        version=int(message.version),
        bitmask=int(message.bitmask),
    )

    for source_combo in message.combos:
        combo = Combo(
            bcs=(
                int(source_combo.bcs)
                if source_combo.HasField("bcs")
                else 0
            ),
            configMaskLow=int(
                source_combo.configMaskLow
            ),
            configMaskHigh=int(
                source_combo.configMaskHigh
            ),
        )

        for source_component in (
            source_combo.components
        ):
            combo.components.append(
                Component(
                    band=int(
                        source_component.band
                    ),
                    bwClassMimoDl=int(
                        source_component.bwClassMimoDl
                    ),
                    bwClassMimoUl=int(
                        source_component.bwClassMimoUl
                    ),
                )
            )

        document.combos.append(combo)

    return document


# Binary protobuf export

def format_binary_document(
    document: ComboDocument,
) -> bytes:
    if not (
        0
        <= document.version
        <= 0xFFFFFFFF
    ):
        raise ValueError(
            "Version must fit in uint32"
        )

    if not (
        0
        <= document.bitmask
        <= 0xFFFFFFFF
    ):
        raise ValueError(
            "Bitmask must fit in uint32"
        )

    message_class = (
        build_shannon_lte_message_class()
    )

    message = message_class()

    message.version = int(
        document.version
    )

    message.bitmask = int(
        document.bitmask
    )

    for combo_number, combo in enumerate(
        document.combos,
        start=1,
    ):
        if not (
            0
            <= combo.bcs
            <= 0xFFFFFFFF
        ):
            raise ValueError(
                f"Combo {combo_number}: "
                "BCS must fit in uint32"
            )

        if not (
            0
            <= combo.configMaskLow
            <= 0xFFFFFFFFFFFFFFFF
        ):
            raise ValueError(
                f"Combo {combo_number}: "
                "conf_id0to63 must fit in uint64"
            )

        if not (
            0
            <= combo.configMaskHigh
            <= 0xFFFFFFFF
        ):
            raise ValueError(
                f"Combo {combo_number}: "
                "conf_id64to95 must fit in uint32"
            )

        target_combo = message.combos.add()

        target_combo.bcs = int(
            combo.bcs
        )

        target_combo.configMaskLow = int(
            combo.configMaskLow
        )

        target_combo.configMaskHigh = int(
            combo.configMaskHigh
        )

        for component_number, component in enumerate(
            combo.components,
            start=1,
        ):
            int32_min = -0x80000000
            int32_max = 0x7FFFFFFF

            for field_name, value in (
                ("band", component.band),
                (
                    "bwClassMimoDl",
                    component.bwClassMimoDl,
                ),
                (
                    "bwClassMimoUl",
                    component.bwClassMimoUl,
                ),
            ):
                if not (
                    int32_min
                    <= value
                    <= int32_max
                ):
                    raise ValueError(
                        f"Combo {combo_number}, "
                        f"component {component_number}: "
                        f"{field_name} must fit in int32"
                    )

            target_component = (
                target_combo.components.add()
            )

            target_component.band = int(
                component.band
            )

            target_component.bwClassMimoDl = int(
                component.bwClassMimoDl
            )

            target_component.bwClassMimoUl = int(
                component.bwClassMimoUl
            )

    try:
        return message.SerializeToString()

    except Exception as exc:
        raise ValueError(
            "Could not serialize binary protobuf: "
            f"{exc}"
        ) from exc


# Text document export

def format_document(
    document: ComboDocument,
) -> str:
    """
    Export decoded protobuf text using these preferred names:

        conf_id0to63
        conf_id64to95

    Internal Python names remain:

        configMaskLow
        configMaskHigh
    """
    lines = [
        f"version: {document.version}"
    ]

    for combo in document.combos:
        lines.append("combos {")

        for component in combo.components:
            lines.extend(
                [
                    "  components {",
                    (
                        "    band: "
                        f"{component.band}"
                    ),
                    (
                        "    bwClassMimoDl: "
                        f"{component.bwClassMimoDl}"
                    ),
                    (
                        "    bwClassMimoUl: "
                        f"{component.bwClassMimoUl}"
                    ),
                    "  }",
                ]
            )

        lines.extend(
            [
                f"  bcs: {combo.bcs}",
                (
                    "  conf_id0to63: "
                    f"{combo.configMaskLow}"
                ),
                (
                    "  conf_id64to95: "
                    f"{combo.configMaskHigh}"
                ),
                "}",
            ]
        )

    lines.append(
        f"bitmask: {document.bitmask}"
    )

    return "\n".join(lines) + "\n"


def decode_bw_class(
    value: int,
) -> tuple[str, int]:
    if value == 0:
        return "", 0

    base_value = value & ~1

    class_map = {
        32768: "A",
        16384: "B",
        8192: "C",
        4096: "D",
        2048: "E",
        1024: "F",
    }

    class_letter = class_map.get(
        base_value,
        f"[{value}]",
    )

    mimo = 4 if value & 1 else 2

    return class_letter, mimo


def count_direction_components(
    combo: Combo,
    field_name: str,
) -> int:
    cc_count_by_class = {
        "A": 1,
        "B": 2,
        "C": 2,
        "D": 3,
        "E": 4,
        "F": 5,
    }

    total_ccs = 0

    for component in combo.components:
        raw_value = getattr(
            component,
            field_name,
        )

        if raw_value == 0:
            continue

        class_letter, _mimo = (
            decode_bw_class(raw_value)
        )

        total_ccs += cc_count_by_class.get(
            class_letter,
            1,
        )

    return total_ccs


def describe_direction_combo(
    combo: Combo,
    field_name: str,
) -> str:
    displayed_components: List[str] = []

    for component in combo.components:
        raw_value = getattr(
            component,
            field_name,
        )

        if raw_value == 0:
            continue

        class_letter, _mimo = (
            decode_bw_class(raw_value)
        )

        if class_letter == "A":
            displayed_components.append(
                str(component.band)
            )
        else:
            displayed_components.append(
                f"{component.band}{class_letter}"
            )

    if displayed_components:
        return " + ".join(
            displayed_components
        )

    return "—"


def describe_dl_mimo(
    combo: Combo,
) -> str:
    cc_count_by_class = {
        "A": 1,
        "B": 2,
        "C": 2,
        "D": 3,
        "E": 4,
        "F": 5,
    }

    mimo_values: List[str] = []

    for component in combo.components:
        raw_value = (
            component.bwClassMimoDl
        )

        if raw_value == 0:
            continue

        class_letter, mimo = (
            decode_bw_class(raw_value)
        )

        cc_count = cc_count_by_class.get(
            class_letter,
            1,
        )

        mimo_values.extend(
            [str(mimo)] * cc_count
        )

    if mimo_values:
        return " + ".join(mimo_values)

    return "—"


def describe_bcs_mask(
    mask: int,
) -> str:
    """
    Display BCS indices represented by the 32-bit
    MSB-first bitmask.
    """
    values = [
        str(index)
        for index in range(32)
        if mask & (1 << (31 - index))
    ]

    if values:
        return ", ".join(values)

    return "—"


def copy_combo(
    combo: Combo,
) -> Combo:
    return Combo(
        components=[
            Component(
                band=component.band,
                bwClassMimoDl=(
                    component.bwClassMimoDl
                ),
                bwClassMimoUl=(
                    component.bwClassMimoUl
                ),
            )
            for component in combo.components
        ],
        bcs=combo.bcs,
        configMaskLow=combo.configMaskLow,
        configMaskHigh=combo.configMaskHigh,
    )



# Automatic UL and ULCA rules
S5300_UL_AUTO_VALUE = 0xFFFF
SDL_BANDS = {29, 32, 75}
LAA_DL_ONLY_BANDS = {46}
NO_UL_BANDS = SDL_BANDS | LAA_DL_ONLY_BANDS
LOW_BANDS = {5, 8, 12, 13, 14, 17, 18, 19, 20, 26, 28, 29, 71}
TDD_BANDS = {38, 39, 40, 41, 42, 48}
NO_4X4_BANDS = LOW_BANDS | {21}
ALLOWED_LOW_BAND_MIXES = {
    frozenset({8, 20}),
    frozenset({20, 28}),
}


@dataclass
class UlVariantResult:
    created_count: int
    modified_original: bool
    message: str


def combo_uses_auto_pcc(
    combo: Combo,
) -> bool:
    return bool(combo.components) and all(
        component.bwClassMimoUl == S5300_UL_AUTO_VALUE
        for component in combo.components
    )


def blocked_ul_bands(
    combo: Combo,
) -> set[int]:
    # Downlink-only bands never receive uplink. Bands 7 and 38
    # are also blocked when both are present in the same combo.
    bands = {
        component.band
        for component in combo.components
    }

    blocked = set(NO_UL_BANDS)

    if 7 in bands and 38 in bands:
        blocked.update(
            {
                7,
                38,
            }
        )

    return blocked


def can_use_auto_pcc(
    combo: Combo,
) -> bool:
    if not combo.components:
        return False

    blocked = blocked_ul_bands(combo)

    return all(
        component.bwClassMimoDl != 0
        and component.band not in blocked
        for component in combo.components
    )


def first_dl_component_index(
    combo: Combo,
) -> Optional[int]:
    # Return the first downlink component that is legal for uplink.
    blocked = blocked_ul_bands(combo)

    for index, component in enumerate(
        combo.components
    ):
        if (
            component.bwClassMimoDl != 0
            and component.band not in blocked
        ):
            return index

    return None


def last_dl_index_by_band(
    combo: Combo,
) -> dict[int, int]:
    # Repeated bands use their final downlink component for uplink.
    result: dict[int, int] = {}

    for index, component in enumerate(
        combo.components
    ):
        if component.bwClassMimoDl != 0:
            result[component.band] = index

    return result

# Keep every DL component index for each band so repeated-band
# ULCA such as UL 1+1 can be generated
def dl_indices_by_band(
    combo: Combo,
) -> dict[int, list[int]]:
    result: dict[int, list[int]] = {}

    for index, component in enumerate(
        combo.components
    ):
        if component.bwClassMimoDl == 0:
            continue

        result.setdefault(
            component.band,
            [],
        ).append(index)

    return result


def valid_ul_pair(
    left: int,
    right: int,
    allow_fdd_aa_ulca: bool = False,
    allow_tdd_aa_ulca: bool = False,
    allow_fdd_tdd_ulca: bool = False,
) -> bool:
    if (
        left in NO_UL_BANDS
        or right in NO_UL_BANDS
    ):
        return False

    if (
        left in LOW_BANDS
        and right in LOW_BANDS
        and left != right
        and frozenset({left, right})
        not in ALLOWED_LOW_BAND_MIXES
    ):
        return False

    left_is_tdd = left in TDD_BANDS
    right_is_tdd = right in TDD_BANDS

    if left_is_tdd and right_is_tdd:
        return allow_tdd_aa_ulca

    if not left_is_tdd and not right_is_tdd:
        return allow_fdd_aa_ulca

    return allow_fdd_tdd_ulca


def clear_ul(
    combo: Combo,
) -> None:
    # Remove all uplink assignments from a combo.
    for component in combo.components:
        component.bwClassMimoUl = 0


def set_auto_pcc(
    combo: Combo,
) -> None:
    if not can_use_auto_pcc(combo):
        raise ValueError(
            "Auto PCC requires every DL component to support uplink."
        )

    for component in combo.components:
        component.bwClassMimoUl = S5300_UL_AUTO_VALUE


def set_ul_a_indices(combo: Combo, component_indices: tuple[int, ...]) -> None:
    clear_ul(combo)
    blocked = blocked_ul_bands(combo)

    for component_index in component_indices:
        if not (0 <= component_index < len(combo.components)):
            continue

        component = combo.components[component_index]

        if component.bwClassMimoDl == 0 or component.band in blocked:
            continue

        component.bwClassMimoUl = 32768


def set_single_class_c_ul(
    combo: Combo,
    component_index: int,
) -> None:
    # Class C UL
    clear_ul(combo)

    component = combo.components[
        component_index
    ]

    if component.band not in blocked_ul_bands(
        combo
    ):
        component.bwClassMimoUl = 8192


def dl_base_signature(
    combo: Combo,
) -> tuple:
    return tuple(
        sorted(
            (
                component.band,
                component.bwClassMimoDl,
            )
            for component in combo.components
        )
    )


def full_config_signature(
    combo: Combo,
) -> tuple:
    return tuple(
        sorted(
            (
                component.band,
                component.bwClassMimoDl,
                component.bwClassMimoUl,
            )
            for component in combo.components
        )
    )

def _candidate_ul_variants(
    source: Combo,
    include_ulca: bool,
    allow_fdd_aa_ulca: bool = False,
    allow_tdd_aa_ulca: bool = False,
    allow_fdd_tdd_ulca: bool = False,
    include_class_c_ul: bool = True,
    include_single_ul: bool = True,
) -> list[Combo]:
    indices_by_band = dl_indices_by_band(source)
    blocked = blocked_ul_bands(source)
    unique_bands = tuple(band for band in indices_by_band if band not in blocked)

    candidates: list[Combo] = []

    if include_single_ul:
        # Normal single-band Class-A UL.
        for band in unique_bands:
            indices = indices_by_band[band]
            if not indices:
                continue

            candidate = copy_combo(source)
            set_ul_a_indices(candidate, (indices[-1],))
            candidates.append(candidate)

    if include_ulca:
        # Inter-band A+A ULCA.
        for left_band, right_band in combinations(unique_bands, 2):
            if not valid_ul_pair(left_band, right_band, allow_fdd_aa_ulca, allow_tdd_aa_ulca, allow_fdd_tdd_ulca):
                continue

            left_indices = indices_by_band[left_band]
            right_indices = indices_by_band[right_band]
            if not left_indices or not right_indices:
                continue

            candidate = copy_combo(source)
            set_ul_a_indices(candidate, (left_indices[-1], right_indices[-1]))
            candidates.append(candidate)

        # Same-band A+A ULCA.
        for band in unique_bands:
            indices = indices_by_band[band]
            if len(indices) < 2:
                continue

            if not valid_ul_pair(band, band, allow_fdd_aa_ulca, allow_tdd_aa_ulca, allow_fdd_tdd_ulca):
                continue

            candidate = copy_combo(source)
            set_ul_a_indices(candidate, (indices[-2], indices[-1]))
            candidates.append(candidate)

    # Standalone Class-C UL is only generated when requested.
    if include_single_ul and include_class_c_ul:
        for index, component in enumerate(source.components):
            class_letter, _mimo = decode_bw_class(component.bwClassMimoDl)

            if class_letter == "C" and component.band not in blocked:
                candidate = copy_combo(source)
                set_single_class_c_ul(candidate, index)
                candidates.append(candidate)

    return candidates

def generate_ul_variants(
    document: ComboDocument,
    selected_index: int,
    include_ulca: bool,
    allow_fdd_aa_ulca: bool = False,
    allow_tdd_aa_ulca: bool = False,
    allow_fdd_tdd_ulca: bool = False,
    supports_auto_pcc: bool = False,
) -> UlVariantResult:
    if not (
        0
        <= selected_index
        < len(document.combos)
    ):
        raise ValueError(
            "Select a valid combination first."
        )

    selected_combo = document.combos[
        selected_index
    ]

    selected_has_valid_auto_pcc = (
        supports_auto_pcc
        and combo_uses_auto_pcc(selected_combo)
        and can_use_auto_pcc(selected_combo)
    )

    if first_dl_component_index(
        selected_combo
    ) is None:
        raise ValueError(
            "The selected combination has no "
            "DL band that is legal for uplink."
        )

    source = copy_combo(
        selected_combo
    )

    clear_ul(
        source
    )

    selected_dl_signature = dl_base_signature(
        selected_combo
    )

    existing = {
        full_config_signature(combo)
        for combo in document.combos
        if dl_base_signature(combo)
        == selected_dl_signature
    }

    candidates = _candidate_ul_variants(
        source,
        include_ulca=include_ulca,
        allow_fdd_aa_ulca=(
            allow_fdd_aa_ulca
        ),
        allow_tdd_aa_ulca=(
            allow_tdd_aa_ulca
        ),
        allow_fdd_tdd_ulca=(
            allow_fdd_tdd_ulca
        ),
        include_class_c_ul=True,
        include_single_ul=(
            not selected_has_valid_auto_pcc
        ),
    )

    unique_candidates: list[Combo] = []

    for candidate in candidates:
        signature = full_config_signature(
            candidate
        )

        has_ul = any(
            component.bwClassMimoUl != 0
            for component in candidate.components
        )

        if (
            not has_ul
            or signature in existing
        ):
            continue

        existing.add(
            signature
        )

        unique_candidates.append(
            candidate
        )

    if not unique_candidates:
        if (
            selected_has_valid_auto_pcc
            and not include_ulca
        ):
            message = (
                "Auto PCC already covers every legal "
                "single-PCC variant."
            )
        else:
            message = (
                "All requested legal UL variants "
                "already exist."
            )

        return UlVariantResult(
            created_count=0,
            modified_original=False,
            message=message,
        )

    selected_has_ul = any(
        component.bwClassMimoUl != 0
        for component in selected_combo.components
    )

    insert_at = selected_index + 1
    created_count = 0
    modified_original = False

    if not selected_has_ul:
        first_candidate = unique_candidates.pop(
            0
        )

        document.combos[
            selected_index
        ] = first_candidate

        created_count += 1
        modified_original = True

    for candidate in unique_candidates:
        document.combos.insert(
            insert_at,
            candidate,
        )

        insert_at += 1
        created_count += 1

    if include_ulca:
        mode_name = (
            "UL band, ULCA, and Class-C UL"
        )
    else:
        mode_name = (
            "UL band and Class-C UL"
        )

    if modified_original:
        message = (
            f"Generated {created_count} legal "
            f"{mode_name} variants; the selected "
            "no-UL combo was used as the first result."
        )
    else:
        message = (
            f"Generated {created_count} new legal "
            f"{mode_name} variants."
        )

    return UlVariantResult(
        created_count=created_count,
        modified_original=modified_original,
        message=message,
    )

def auto_fill_ul_bands(
    document: ComboDocument,
    use_auto_pcc: bool = False,
    supports_auto_pcc: bool = False,
    target_dl_signatures: Optional[
        set[tuple]
    ] = None,
) -> int:
    groups: dict[tuple, list[Combo]] = {}

    for combo in document.combos:
        signature = dl_base_signature(combo)

        if (
            target_dl_signatures is not None
            and signature not in target_dl_signatures
        ):
            continue

        groups.setdefault(
            signature,
            [],
        ).append(combo)

    existing = {
        full_config_signature(combo)
        for combo in document.combos
    }

    additions: list[Combo] = []
    for group in groups.values():
        source_combo = group[0]
        source = copy_combo(
            source_combo
        )

        clear_ul(
            source
        )

        has_valid_auto_pcc = any(
            supports_auto_pcc
            and combo_uses_auto_pcc(combo)
            and can_use_auto_pcc(combo)
            for combo in group
        )

        if has_valid_auto_pcc:
            continue

        if (
            supports_auto_pcc
            and use_auto_pcc
            and can_use_auto_pcc(source)
        ):
            candidate = copy_combo(source)
            set_auto_pcc(candidate)
            signature = full_config_signature(candidate)

            if signature not in existing:
                additions.append(candidate)
                existing.add(signature)

            continue

        candidates = _candidate_ul_variants(
            source,
            include_ulca=False,
            allow_fdd_aa_ulca=False,
            allow_tdd_aa_ulca=False,
            allow_fdd_tdd_ulca=False,
            include_class_c_ul=False,
            include_single_ul=True,
        )

        for candidate in candidates:
            signature = full_config_signature(
                candidate
            )

            has_ul = any(
                component.bwClassMimoUl != 0
                for component in candidate.components
            )

            if (
                not has_ul
                or signature in existing
            ):
                continue

            existing.add(
                signature
            )

            additions.append(
                candidate
            )

    document.combos.extend(
        additions
    )

    return len(additions)

def auto_fill_ulca(
    document: ComboDocument,
    allow_fdd_aa_ulca: bool = False,
    allow_tdd_aa_ulca: bool = False,
    allow_fdd_tdd_ulca: bool = False,
    use_auto_pcc: bool = False,
    supports_auto_pcc: bool = False,
    target_dl_signatures: Optional[
        set[tuple]
    ] = None,
) -> int:
    # Generate legal UL variants for every unique downlink combo.
    groups: dict[tuple, list[Combo]] = {}

    for combo in document.combos:
        signature = dl_base_signature(combo)

        if (
            target_dl_signatures is not None
            and signature not in target_dl_signatures
        ):
            continue

        groups.setdefault(
            signature,
            [],
        ).append(combo)

    existing = {
        full_config_signature(combo)
        for combo in document.combos
    }

    additions: list[Combo] = []
    for group in groups.values():
        source_combo = group[0]
        source = copy_combo(
            source_combo
        )

        clear_ul(
            source
        )

        has_valid_auto_pcc = any(
            supports_auto_pcc
            and combo_uses_auto_pcc(combo)
            and can_use_auto_pcc(combo)
            for combo in group
        )

        prefer_auto_pcc = (
            has_valid_auto_pcc
            or (
                use_auto_pcc
                and supports_auto_pcc
                and can_use_auto_pcc(source)
            )
        )

        if prefer_auto_pcc and not has_valid_auto_pcc:
            candidate = copy_combo(source)
            set_auto_pcc(candidate)
            signature = full_config_signature(candidate)

            if signature not in existing:
                additions.append(candidate)
                existing.add(signature)

        candidates = _candidate_ul_variants(
            source,
            include_ulca=True,
            allow_fdd_aa_ulca=(
                allow_fdd_aa_ulca
            ),
            allow_tdd_aa_ulca=(
                allow_tdd_aa_ulca
            ),
            allow_fdd_tdd_ulca=(
                allow_fdd_tdd_ulca
            ),
            include_class_c_ul=True,
            include_single_ul=(
                not prefer_auto_pcc
            ),
        )

        for candidate in candidates:
            signature = full_config_signature(
                candidate
            )

            has_ul = any(
                component.bwClassMimoUl != 0
                for component in candidate.components
            )

            if (
                signature in existing
                or not has_ul
            ):
                continue

            existing.add(
                signature
            )

            additions.append(
                candidate
            )

    document.combos.extend(
        additions
    )

    return len(additions)


def disable_ulca(
    document: ComboDocument,
    supports_auto_pcc: bool = False,
) -> int:
    # Keep at most one legal Class-A uplink assignment per combo.
    changed = 0

    for combo in document.combos:
        if (
            supports_auto_pcc
            and combo_uses_auto_pcc(combo)
        ):
            if can_use_auto_pcc(combo):
                continue

            clear_ul(combo)
            changed += 1

        blocked = blocked_ul_bands(
            combo
        )

        valid_ul_indices = [
            index
            for index, component in enumerate(
                combo.components
            )
            if (
                component.bwClassMimoUl != 0
                and component.band not in blocked
            )
        ]

        combo_changed = False

        for component in combo.components:
            if (
                component.bwClassMimoUl != 0
                and component.band in blocked
            ):
                component.bwClassMimoUl = 0
                combo_changed = True

        if valid_ul_indices:
            keep_index = valid_ul_indices[
                0
            ]

            for index, component in enumerate(
                combo.components
            ):
                if index == keep_index:
                    if (
                        component.bwClassMimoUl
                        != 32768
                    ):
                        component.bwClassMimoUl = (
                            32768
                        )
                        combo_changed = True

                elif (
                    component.bwClassMimoUl
                    != 0
                ):
                    component.bwClassMimoUl = 0
                    combo_changed = True

        if combo_changed:
            changed += 1

    return changed


# Validation checks
VALIDATION_DUPLICATE = "duplicate"
VALIDATION_7_38_UL = "band_7_38_ul"
VALIDATION_SDL_UL = "sdl_ul"
VALIDATION_SPATIAL_STREAMS = "spatial_streams"
VALIDATION_LOW_BAND_MIX = "low_band_mix"
VALIDATION_UL_CLASS = "ul_class"
VALIDATION_MISSING_UL = "missing_ul"
VALIDATION_NO_LEGAL_UL = "no_legal_ul"
VALIDATION_UNSUPPORTED_4X4 = "unsupported_4x4"


@dataclass
class ValidationIssue:
    issue_type: str
    combo_indices: list[int]
    message: str
    fixable: bool = True


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(
        default_factory=list
    )

    @property
    def is_valid(self) -> bool:
        return not self.issues

    @property
    def affected_indices(self) -> set[int]:
        result: set[int] = set()

        for issue in self.issues:
            result.update(
                issue.combo_indices
            )

        return result

    def issues_of_type(
        self,
        issue_type: str,
    ) -> list[ValidationIssue]:
        return [
            issue
            for issue in self.issues
            if issue.issue_type == issue_type
        ]


def combo_dl_spatial_streams(
    combo: Combo,
) -> int:
    cc_count_by_class = {
        "A": 1,
        "B": 2,
        "C": 2,
        "D": 3,
        "E": 4,
        "F": 5,
    }

    total = 0

    for component in combo.components:
        class_letter, mimo = decode_bw_class(
            component.bwClassMimoDl
        )

        if class_letter not in cc_count_by_class:
            continue

        total += (
            cc_count_by_class[class_letter]
            * mimo
        )

    return total


def combo_low_bands(
    combo: Combo,
) -> set[int]:
    return {
        component.band
        for component in combo.components
        if component.band in LOW_BANDS
    }

def combo_has_any_ul(
    combo: Combo,
) -> bool:
    return any(
        component.bwClassMimoUl != 0
        for component in combo.components
    )


def validate_document(
    document: ComboDocument,
) -> ValidationReport:
    issues: list[ValidationIssue] = []

    signature_first_index: dict[
        tuple,
        int,
    ] = {}

    duplicate_groups: dict[
        int,
        list[int],
    ] = {}

    for index, combo in enumerate(
        document.combos
    ):
        signature = full_config_signature(
            combo
        )

        first_index = signature_first_index.get(
            signature
        )

        if first_index is None:
            signature_first_index[
                signature
            ] = index
        else:
            duplicate_groups.setdefault(
                first_index,
                [first_index],
            ).append(index)

        bands = {
            component.band
            for component in combo.components
        }

        if 7 in bands and 38 in bands:
            invalid_indices = [
                component_index
                for component_index, component
                in enumerate(combo.components)
                if (
                    component.band in {7, 38}
                    and component.bwClassMimoUl != 0
                )
            ]

            if invalid_indices:
                issues.append(
                    ValidationIssue(
                        issue_type=VALIDATION_7_38_UL,
                        combo_indices=[index],
                        message=(
                            f"Combo {index + 1}: Bands 7 and 38 "
                            "coexist, but uplink is assigned to "
                            "Band 7 or Band 38."
                        ),
                    )
                )

        downlink_only_ul_bands = sorted({
            component.band
            for component in combo.components
            if (
                component.band in NO_UL_BANDS
                and component.bwClassMimoUl != 0
            )
        })

        if downlink_only_ul_bands:
            issues.append(
                ValidationIssue(
                    issue_type=VALIDATION_SDL_UL,
                    combo_indices=[index],
                    message=(
                        f"Combo {index + 1}: downlink-only band(s) "
                        "cannot have uplink: "
                        + ", ".join(
                            str(band)
                            for band in downlink_only_ul_bands
                        )
                        + "."
                    ),
                )
            )
            
        unsupported_4x4_components: list[str] = []

        for component in combo.components:
            if (
                component.band in NO_4X4_BANDS
                and component.bwClassMimoDl != 0
                and component.bwClassMimoDl & 1
            ):
                class_letter, _mimo = decode_bw_class(
                    component.bwClassMimoDl
                )

                unsupported_4x4_components.append(
                    f"{component.band}{class_letter}"
                )

        if unsupported_4x4_components:
            issues.append(
                ValidationIssue(
                    issue_type=(
                        VALIDATION_UNSUPPORTED_4X4
                    ),
                    combo_indices=[index],
                    message=(
                        f"Combo {index + 1}: "
                        "4×4 DL MIMO is assigned to "
                        "unsupported band component(s): "
                        + ", ".join(
                            unsupported_4x4_components
                        )
                        + "."
                    ),
                )
            )

        spatial_streams = (
            combo_dl_spatial_streams(
                combo
            )
        )

        if spatial_streams > 24:
            issues.append(
                ValidationIssue(
                    issue_type=(
                        VALIDATION_SPATIAL_STREAMS
                    ),
                    combo_indices=[index],
                    message=(
                        f"Combo {index + 1}: "
                        f"{spatial_streams} DL spatial "
                        "streams exceeds the limit of 24."
                    ),
                )
            )

        present_low_bands = (
            combo_low_bands(combo)
        )

        if (
            len(present_low_bands) > 1
            and frozenset(present_low_bands)
            not in ALLOWED_LOW_BAND_MIXES
        ):
            issues.append(
                ValidationIssue(
                    issue_type=VALIDATION_LOW_BAND_MIX,
                    combo_indices=[index],
                    message=(
                        f"Combo {index + 1}: unsupported low-band "
                        "combination "
                        + "+".join(
                            str(band)
                            for band
                            in sorted(
                                present_low_bands
                            )
                        )
                        + ". Only 8+20 and 20+28 are allowed."
                    ),
                    fixable=False,
                )
            )

        excessive_ul_classes: list[str] = []

        for component in combo.components:
            if component.bwClassMimoUl == 0:
                continue

            class_letter, _mimo = decode_bw_class(
                component.bwClassMimoUl
            )

            if class_letter in {
                "E",
                "F",
            }:
                excessive_ul_classes.append(
                    f"{component.band}{class_letter}"
                )

        if excessive_ul_classes:
            issues.append(
                ValidationIssue(
                    issue_type=VALIDATION_UL_CLASS,
                    combo_indices=[index],
                    message=(
                        f"Combo {index + 1}: UL class exceeds D: "
                        + ", ".join(
                            excessive_ul_classes
                        )
                        + "."
                    ),
                )
            )

        if not combo_has_any_ul(combo):
            legal_ul_index = (
                first_dl_component_index(
                    combo
                )
            )

            if legal_ul_index is None:
                issues.append(
                    ValidationIssue(
                        issue_type=VALIDATION_NO_LEGAL_UL,
                        combo_indices=[index],
                        message=(
                            f"Combo {index + 1}: uplink band unavailable"
                        ),
                        fixable=False,
                    )
                )
            else:
                issues.append(
                    ValidationIssue(
                        issue_type=VALIDATION_MISSING_UL,
                        combo_indices=[index],
                        message=(
                            f"Combo {index + 1}: uplink is missing."
                        ),
                    )
                )

    for indices in duplicate_groups.values():
        display_numbers = ", ".join(
            str(index + 1)
            for index in indices
        )

        issues.append(
            ValidationIssue(
                issue_type=VALIDATION_DUPLICATE,
                combo_indices=indices,
                message=(
                    "Duplicate at "
                    f"combos: {display_numbers}."
                ),
            )
        )

    return ValidationReport(
        issues=issues
    )

def _downgrade_combo_to_stream_limit(
    combo: Combo,
    maximum_streams: int = 24,
) -> bool:
    changed = False

    while (
        combo_dl_spatial_streams(combo)
        > maximum_streams
    ):
        candidates = [
            (
                index,
                component,
            )
            for index, component
            in enumerate(combo.components)
            if (
                component.bwClassMimoDl != 0
                and component.bwClassMimoDl & 1
            )
        ]

        if not candidates:
            break

        candidates.sort(
            key=lambda item: (
                -count_direction_components(
                    Combo(
                        components=[
                            item[1]
                        ]
                    ),
                    "bwClassMimoDl",
                ),
                item[0],
            )
        )

        component_index = candidates[
            0
        ][0]

        combo.components[
            component_index
        ].bwClassMimoDl &= ~1

        changed = True

    return changed


def fix_validation_issues(
    document: ComboDocument,
    report: Optional[
        ValidationReport
    ] = None,
    supports_auto_pcc: bool = False,
) -> dict[str, int]:
    if report is None:
        report = validate_document(
            document
        )

    results = {
        "duplicates_removed": 0,
        "invalid_ul_removed": 0,
        "missing_ul_filled": 0,
        "ul_classes_repaired": 0,
        "low_band_mimo_repaired": 0,
        "mimo_downgrades": 0,
        "unfixable": 0,
    }

    for issue in report.issues:
        if not issue.fixable:
            results["unfixable"] += 1

    for combo in document.combos:
        bands = {
            component.band
            for component in combo.components
        }

        if (
            supports_auto_pcc
            and combo_uses_auto_pcc(combo)
            and not can_use_auto_pcc(combo)
        ):
            results["invalid_ul_removed"] += len(
                combo.components
            )
            clear_ul(combo)

        for component in combo.components:
            invalid_7_38_ul = (
                7 in bands
                and 38 in bands
                and component.band in {
                    7,
                    38,
                }
                and component.bwClassMimoUl != 0
            )

            invalid_downlink_only_ul = (
                component.band in NO_UL_BANDS
                and component.bwClassMimoUl != 0
            )
            
            if (
                component.band in NO_4X4_BANDS
                and component.bwClassMimoDl != 0
                and component.bwClassMimoDl & 1
            ):
                component.bwClassMimoDl &= ~1

                results[
                    "low_band_mimo_repaired"
                ] += 1

            if (
                invalid_7_38_ul
                or invalid_downlink_only_ul
            ):
                component.bwClassMimoUl = 0
                results[
                    "invalid_ul_removed"
                ] += 1

            if component.bwClassMimoUl != 0:
                class_letter, _mimo = (
                    decode_bw_class(
                        component.bwClassMimoUl
                    )
                )

                if class_letter in {
                    "E",
                    "F",
                }:
                    component.bwClassMimoUl = 4096
                    results[
                        "ul_classes_repaired"
                    ] += 1

        if not combo_has_any_ul(combo):
            legal_index = (
                first_dl_component_index(
                    combo
                )
            )

            if legal_index is not None:
                combo.components[
                    legal_index
                ].bwClassMimoUl = 32768

                results[
                    "missing_ul_filled"
                ] += 1

        if _downgrade_combo_to_stream_limit(
            combo
        ):
            results[
                "mimo_downgrades"
            ] += 1

    seen: set[tuple] = set()
    unique: list[Combo] = []

    for combo in document.combos:
        signature = full_config_signature(
            combo
        )

        if signature in seen:
            results[
                "duplicates_removed"
            ] += 1
            continue

        seen.add(
            signature
        )

        unique.append(
            combo
        )

    document.combos = unique

    return results

def repair_and_deduplicate(
    document: ComboDocument,
    supports_auto_pcc: bool = False,
) -> tuple[int, int]:
    # Remove impossible uplink, fill missing uplink, and remove
    # exact DL/class/MIMO/UL duplicates even when metadata differs.
    repaired = 0

    for combo in document.combos:
        if (
            supports_auto_pcc
            and combo_uses_auto_pcc(combo)
            and not can_use_auto_pcc(combo)
        ):
            clear_ul(combo)
            repaired += 1

        blocked = blocked_ul_bands(
            combo
        )

        for component in combo.components:
            if (
                component.band in blocked
                and component.bwClassMimoUl != 0
            ):
                component.bwClassMimoUl = 0
                repaired += 1

        if not any(
            component.bwClassMimoUl != 0
            for component in combo.components
        ):
            component_index = (
                first_dl_component_index(
                    combo
                )
            )

            if component_index is not None:
                combo.components[
                    component_index
                ].bwClassMimoUl = 32768

                repaired += 1

    seen: set[tuple] = set()
    unique: list[Combo] = []
    duplicates = 0

    for combo in document.combos:
        signature = full_config_signature(
            combo
        )

        if signature in seen:
            duplicates += 1
            continue

        seen.add(
            signature
        )

        unique.append(
            combo
        )

    document.combos = unique

    return repaired, duplicates
