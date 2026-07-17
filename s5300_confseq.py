"""S5300 confseq LTE CA bundle import, export, and JSON interchange."""

import binascii
import json
import os
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from lz4.block import compress, decompress

from utils import Combo, ComboDocument, Component, ParseError


CLZ4_HEADER = struct.Struct("<4sIII")
CLZ4_MAGIC = b"CLZ4"
COMBOS_PER_SEGMENT = 1000
S5300_JSON_FORMAT = "shannon-lte-editor/s5300-confseq-v1"
FAMILY_RE = re.compile(r"^(lte_ca(?:_0x[0-9A-Fa-f]+)?)_common$")
FAMILY_NAME_RE = re.compile(r"^lte_ca(?:_0x[0-9A-Fa-f]+)?$")
COMBO_FIELDS = (
    "NUM_BAND",
    "BAND",
    "DL_BW_CLASS_BIT_MAP",
    "UL_BW_CLASS_BIT_MAP",
    "SET_BITMAP",
    "CATEGORY_ARRAY",
)


def _message_class(descriptor, pool):
    if hasattr(message_factory, "GetMessageClass"):
        return message_factory.GetMessageClass(descriptor)
    return message_factory.MessageFactory(pool).GetPrototype(descriptor)


def build_confseq_message_class():
    descriptor = descriptor_pb2.FileDescriptorProto()
    descriptor.name = "s5300_confseq.proto"
    descriptor.syntax = "proto3"

    value_message = descriptor.message_type.add()
    value_message.name = "ValueGroup"
    value_field = value_message.field.add()
    value_field.name = "value"
    value_field.number = 3
    value_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    value_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT64

    item_message = descriptor.message_type.add()
    item_message.name = "NvItem"
    id_field = item_message.field.add()
    id_field.name = "id"
    id_field.number = 1
    id_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    id_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT64
    item_field = item_message.field.add()
    item_field.name = "item"
    item_field.number = 2
    item_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    item_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    item_field.type_name = ".ValueGroup"

    root_message = descriptor.message_type.add()
    root_message.name = "ConfseqData"
    for name, number in (("Revision", 1), ("Name", 2)):
        field = root_message.field.add()
        field.name = name
        field.number = number
        field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
        field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    nvitem_field = root_message.field.add()
    nvitem_field.name = "nvitem"
    nvitem_field.number = 4
    nvitem_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    nvitem_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    nvitem_field.type_name = ".NvItem"

    pool = descriptor_pool.DescriptorPool()
    pool.Add(descriptor)
    return _message_class(pool.FindMessageTypeByName("ConfseqData"), pool)


CONFSEQ_MESSAGE = build_confseq_message_class()


@dataclass(frozen=True)
class Clz4Metadata:
    checksum: int
    trailing: bytes


@dataclass
class ConfseqProfile:
    path: Path
    raw: bytes
    message: object
    clz4: Optional[Clz4Metadata]


@dataclass
class S5300Bundle:
    source_dir: Path
    family: str
    profiles: dict[str, ConfseqProfile]
    document: ComboDocument


def nv_crc(name: str) -> int:
    return binascii.crc32(name.encode("utf-8")) & 0xFFFFFFFF


def decode_confseq_blob(raw: bytes):
    if raw.startswith(b"-----"):
        return None
    if not raw.startswith(CLZ4_MAGIC):
        return raw, None
    if len(raw) < CLZ4_HEADER.size:
        raise ParseError("Truncated CLZ4 header")
    magic, raw_size, compressed_size, checksum = CLZ4_HEADER.unpack(
        raw[:CLZ4_HEADER.size]
    )
    end = CLZ4_HEADER.size + compressed_size
    if magic != CLZ4_MAGIC or end > len(raw):
        raise ParseError("Invalid CLZ4 header sizes")
    try:
        data = decompress(
            raw[CLZ4_HEADER.size:end],
            uncompressed_size=raw_size,
        )
    except Exception as exc:
        raise ParseError(f"Could not decompress CLZ4 confseq: {exc}") from exc
    return data, Clz4Metadata(checksum=checksum, trailing=raw[end:])


def encode_confseq_blob(data: bytes, metadata: Optional[Clz4Metadata]) -> bytes:
    if metadata is None:
        return data
    compressed = compress(data, store_size=False)
    return (
        CLZ4_HEADER.pack(
            CLZ4_MAGIC,
            len(data),
            len(compressed),
            metadata.checksum,
        )
        + compressed
        + metadata.trailing
    )


def parse_confseq_file(path: Path) -> Optional[ConfseqProfile]:
    raw = path.read_bytes()
    decoded = decode_confseq_blob(raw)
    if decoded is None:
        return None
    data, metadata = decoded
    message = CONFSEQ_MESSAGE()
    try:
        message.ParseFromString(data)
    except Exception as exc:
        raise ParseError(f"Could not parse confseq {path.name}: {exc}") from exc
    if not message.Name:
        raise ParseError(f"Confseq has no profile name: {path.name}")
    return ConfseqProfile(path=path, raw=raw, message=message, clz4=metadata)


def scan_confseq_directory(directory: Path) -> dict[str, ConfseqProfile]:
    directory = Path(directory)
    if not directory.is_dir():
        raise ParseError(f"Confseq directory does not exist: {directory}")
    result = {}
    for path in sorted(item for item in directory.iterdir() if item.is_file()):
        profile = parse_confseq_file(path)
        if profile is None:
            continue
        if profile.message.Name in result:
            raise ParseError(f"Duplicate confseq profile name: {profile.message.Name}")
        result[profile.message.Name] = profile
    if not result:
        raise ParseError(f"No confseq profiles found in {directory}")
    return result


def discover_s5300_families(directory: Path) -> list[str]:
    profiles = scan_confseq_directory(directory)
    families = []
    for profile_name in profiles:
        match = FAMILY_RE.match(profile_name)
        if not match:
            continue
        family = match.group(1)
        required = required_profile_names(family)
        if all(name in profiles for name in required):
            families.append(family)
    return sorted(set(families))


def required_profile_names(family: str) -> tuple[str, ...]:
    base = (f"{family}_0", f"{family}_1", f"{family}_common")
    return base + tuple(f"{name}.common" for name in base)


def _clone_message(message):
    clone = CONFSEQ_MESSAGE()
    clone.ParseFromString(message.SerializeToString())
    return clone


def _profile_signature(message):
    return tuple(
        (item.id, tuple(tuple(group.value) for group in item.item))
        for item in message.nvitem
    )


def _nv_index(message):
    result = {}
    for item in message.nvitem:
        if item.id in result:
            raise ParseError(
                f"Profile {message.Name} contains duplicate NV CRC {item.id}"
            )
        result[item.id] = item
    return result


def _values(item) -> tuple[int, ...]:
    result = []
    for group in item.item:
        if len(group.value) > 1:
            raise ParseError(
                f"NV CRC {item.id} contains multiple values in one item group"
            )
        result.append(int(group.value[0]) if group.value else 0)
    return tuple(result)


def _required_values(index, name: str, profile_name: str) -> tuple[int, ...]:
    crc = nv_crc(name)
    if crc not in index:
        raise ParseError(f"Missing {name} in profile {profile_name}")
    return _values(index[crc])


def _combo_nv_name(combo_id: int, field: str) -> str:
    return f"UECAPA_REL10_CA_COMB_{combo_id}_{field}"


def _segment_profile_name(family: str, combo_id: int) -> str:
    segment = 0 if combo_id <= COMBOS_PER_SEGMENT else 1
    return f"{family}_{segment}"


def _validate_document(document: ComboDocument) -> None:
    if not document.combos:
        raise ValueError("S5300 document must contain at least one LTE CA combo")
    if len(document.combos) > COMBOS_PER_SEGMENT * 2:
        raise ValueError("S5300 confseq supports at most 2000 LTE CA combos")
    for combo_id, combo in enumerate(document.combos, start=1):
        if not combo.components:
            raise ValueError(f"Combo {combo_id} contains no LTE band components")
        if not 0 <= combo.bcs <= 0xFFFFFFFF:
            raise ValueError(f"Combo {combo_id} BCS must fit in uint32")
        if not 0 <= combo.configMaskLow <= 0xFFFFFFFFFFFFFFFF:
            raise ValueError(f"Combo {combo_id} low category mask must fit in uint64")
        if not 0 <= combo.configMaskHigh <= 0xFFFFFFFF:
            raise ValueError(f"Combo {combo_id} high category mask must fit in uint32")
        for component in combo.components:
            for label, value in (
                ("band", component.band),
                ("DL class", component.bwClassMimoDl),
                ("UL class", component.bwClassMimoUl),
            ):
                if not -0x80000000 <= value <= 0x7FFFFFFF:
                    raise ValueError(
                        f"Combo {combo_id} component {label} must fit in int32"
                    )


def load_s5300_bundle(directory: Path, family: str) -> S5300Bundle:
    all_profiles = scan_confseq_directory(directory)
    names = required_profile_names(family)
    missing = [name for name in names if name not in all_profiles]
    if missing:
        raise ParseError(f"Missing S5300 profile files: {', '.join(missing)}")
    profiles = {name: all_profiles[name] for name in names}

    for primary in names[:3]:
        mirror = f"{primary}.common"
        if _profile_signature(profiles[primary].message) != _profile_signature(
            profiles[mirror].message
        ):
            raise ParseError(f"S5300 mirror profile differs: {primary} / {mirror}")

    common_name = f"{family}_common"
    common_index = _nv_index(profiles[common_name].message)
    combo_count_values = _required_values(
        common_index,
        "UECAPA_REL10_CA_COMB_NUM",
        common_name,
    )
    if len(combo_count_values) != 1 or combo_count_values[0] <= 0:
        raise ParseError(f"Invalid LTE combo count in {common_name}")
    combo_count = combo_count_values[0]

    segment_indices = {
        f"{family}_{segment}": _nv_index(profiles[f"{family}_{segment}"].message)
        for segment in (0, 1)
    }
    for segment in (0, 1):
        profile_name = f"{family}_{segment}"
        start = 1 if segment == 0 else COMBOS_PER_SEGMENT + 1
        end = min(combo_count, COMBOS_PER_SEGMENT * (segment + 1))
        expected_ids = {
            nv_crc(_combo_nv_name(combo_id, field))
            for combo_id in range(start, end + 1)
            for field in COMBO_FIELDS
        }
        actual_ids = set(segment_indices[profile_name])
        unexpected = actual_ids - expected_ids
        missing_ids = expected_ids - actual_ids
        if unexpected or missing_ids:
            raise ParseError(
                f"Profile {profile_name} is not a pure LTE combo segment: "
                f"{len(unexpected)} unexpected and {len(missing_ids)} missing NVs"
            )

    document = ComboDocument(version=0, bitmask=0)
    for combo_id in range(1, combo_count + 1):
        profile_name = _segment_profile_name(family, combo_id)
        index = segment_indices[profile_name]
        values = {
            field: _required_values(
                index,
                _combo_nv_name(combo_id, field),
                profile_name,
            )
            for field in COMBO_FIELDS
        }
        if values["NUM_BAND"] != (len(values["BAND"]),):
            raise ParseError(f"Combo {combo_id} NUM_BAND does not match BAND")
        component_count = values["NUM_BAND"][0]
        if len(values["DL_BW_CLASS_BIT_MAP"]) != component_count:
            raise ParseError(f"Combo {combo_id} DL component count mismatch")
        if len(values["UL_BW_CLASS_BIT_MAP"]) != component_count:
            raise ParseError(f"Combo {combo_id} UL component count mismatch")
        if len(values["SET_BITMAP"]) != 1:
            raise ParseError(f"Combo {combo_id} has invalid SET_BITMAP")
        if len(values["CATEGORY_ARRAY"]) != 2:
            raise ParseError(f"Combo {combo_id} has invalid CATEGORY_ARRAY")

        document.combos.append(Combo(
            components=[
                Component(band=band, bwClassMimoDl=dl, bwClassMimoUl=ul)
                for band, dl, ul in zip(
                    values["BAND"],
                    values["DL_BW_CLASS_BIT_MAP"],
                    values["UL_BW_CLASS_BIT_MAP"],
                )
            ],
            bcs=values["SET_BITMAP"][0] & 0xFFFFFFFF,
            configMaskLow=values["CATEGORY_ARRAY"][0] & 0xFFFFFFFFFFFFFFFF,
            configMaskHigh=values["CATEGORY_ARRAY"][1] & 0xFFFFFFFF,
        ))

    _validate_document(document)
    return S5300Bundle(
        source_dir=Path(directory),
        family=family,
        profiles=profiles,
        document=document,
    )


def _signed_int64(value: int) -> int:
    return value - (1 << 64) if value >= (1 << 63) else value


def _append_nv(message, name: str, values) -> None:
    item = message.nvitem.add()
    item.id = nv_crc(name)
    for raw_value in values:
        value = int(raw_value)
        group = item.item.add()
        if value:
            group.value.append(value)


def _build_segment_message(template, document, family: str, segment: int):
    message = CONFSEQ_MESSAGE()
    message.Revision = template.Revision
    message.Name = template.Name
    start = 1 if segment == 0 else COMBOS_PER_SEGMENT + 1
    end = min(len(document.combos), COMBOS_PER_SEGMENT * (segment + 1))
    if start > end:
        return message
    for combo_id in range(start, end + 1):
        combo = document.combos[combo_id - 1]
        _append_nv(message, _combo_nv_name(combo_id, "NUM_BAND"), [
            len(combo.components)
        ])
        _append_nv(message, _combo_nv_name(combo_id, "BAND"), [
            component.band for component in combo.components
        ])
        _append_nv(message, _combo_nv_name(combo_id, "DL_BW_CLASS_BIT_MAP"), [
            component.bwClassMimoDl for component in combo.components
        ])
        _append_nv(message, _combo_nv_name(combo_id, "UL_BW_CLASS_BIT_MAP"), [
            component.bwClassMimoUl for component in combo.components
        ])
        _append_nv(message, _combo_nv_name(combo_id, "SET_BITMAP"), [combo.bcs])
        _append_nv(message, _combo_nv_name(combo_id, "CATEGORY_ARRAY"), [
            _signed_int64(combo.configMaskLow),
            combo.configMaskHigh,
        ])
    return message


def _update_common_message(template, combo_count: int):
    message = _clone_message(template)
    target_crc = nv_crc("UECAPA_REL10_CA_COMB_NUM")
    matches = [item for item in message.nvitem if item.id == target_crc]
    if len(matches) != 1:
        raise ParseError(
            f"Profile {template.Name} must contain one LTE combo count NV"
        )
    del matches[0].item[:]
    group = matches[0].item.add()
    group.value.append(combo_count)
    return message


def export_s5300_bundle(
    bundle: S5300Bundle,
    document: ComboDocument,
    output_dir: Path,
) -> list[Path]:
    _validate_document(document)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []

    for profile_name, profile in bundle.profiles.items():
        base_name = profile_name.removesuffix(".common")
        if base_name == f"{bundle.family}_0":
            message = _build_segment_message(
                profile.message, document, bundle.family, 0
            )
        elif base_name == f"{bundle.family}_1":
            message = _build_segment_message(
                profile.message, document, bundle.family, 1
            )
        elif base_name == f"{bundle.family}_common":
            message = _update_common_message(profile.message, len(document.combos))
        else:
            raise ValueError(f"Unexpected S5300 profile in bundle: {profile_name}")

        data = encode_confseq_blob(message.SerializeToString(), profile.clz4)
        destination = output_dir / profile.path.name
        temp = destination.with_name(destination.name + ".tmp")
        temp.write_bytes(data)
        os.replace(temp, destination)
        written.append(destination)

    reloaded = load_s5300_bundle(output_dir, bundle.family)
    if document_to_dict(reloaded.document) != document_to_dict(document):
        raise ValueError("Exported S5300 confseq bundle failed round-trip validation")
    return sorted(written)


def document_to_dict(document: ComboDocument) -> dict:
    _validate_document(document)
    return {
        "combos": [
            {
                "components": [
                    {
                        "band": component.band,
                        "bwClassMimoDl": component.bwClassMimoDl,
                        "bwClassMimoUl": component.bwClassMimoUl,
                    }
                    for component in combo.components
                ],
                "bcs": combo.bcs,
                "configMaskLow": combo.configMaskLow,
                "configMaskHigh": combo.configMaskHigh,
            }
            for combo in document.combos
        ]
    }


def document_from_dict(data: dict) -> ComboDocument:
    try:
        combos_data = data["combos"]
        document = ComboDocument(
            version=0,
            bitmask=0,
            combos=[
                Combo(
                    components=[
                        Component(
                            band=int(component["band"]),
                            bwClassMimoDl=int(component["bwClassMimoDl"]),
                            bwClassMimoUl=int(component["bwClassMimoUl"]),
                        )
                        for component in combo["components"]
                    ],
                    bcs=int(combo["bcs"]),
                    configMaskLow=int(combo["configMaskLow"]),
                    configMaskHigh=int(combo["configMaskHigh"]),
                )
                for combo in combos_data
            ],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ParseError(f"Invalid S5300 JSON document: {exc}") from exc
    _validate_document(document)
    return document


def format_s5300_json(document: ComboDocument, family: str) -> str:
    payload = {
        "format": S5300_JSON_FORMAT,
        "family": family,
        "comboCount": len(document.combos),
        **document_to_dict(document),
    }
    return json.dumps(payload, indent=2, ensure_ascii=True) + "\n"


def parse_s5300_json(text: str):
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid S5300 JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ParseError("S5300 JSON root must be an object")
    if payload.get("format") != S5300_JSON_FORMAT:
        raise ParseError("Unsupported S5300 JSON format identifier")
    family = payload.get("family")
    if not isinstance(family, str) or not FAMILY_NAME_RE.fullmatch(family):
        raise ParseError("S5300 JSON has an invalid LTE CA family")
    document = document_from_dict(payload)
    if payload.get("comboCount") != len(document.combos):
        raise ParseError("S5300 JSON comboCount does not match the combo array")
    return family, document
