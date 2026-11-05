"""Decode local images and compare explicit material identifiers, without control IO.

A decoded label and a detected part are separate observations. In particular,
matching a box/lot/task label never establishes an individual part's identity.
Payload parsing defaults to exact UTF-8: no trimming, case folding or guessed
GS1/customer conventions are applied.
"""

from __future__ import annotations

import json
from typing import Any, Mapping


IDENTITY_SCOPES = ("piece", "box", "lot", "task", "unconfirmed")
DEFAULT_PARSER = {"type": "exact_utf8"}


class CodeDecodingError(RuntimeError):
    """The decoder could not process an image; this is distinct from no read."""


def decode_codes(image_array: Any) -> list[dict]:
    """Return ZXing-C++ observations from a uint8 gray/RGB/RGBA image.

    The caller supplies RGB, not OpenCV BGR. Invalid UTF-8 remains an explicit
    observation with its original bytes; it is not replaced by lossy text.
    Missing dependencies and decoder failures raise ``CodeDecodingError``.
    A successfully processed image with no code returns an empty list.
    """
    try:
        import numpy as np
        import zxingcpp
        from PIL import Image

        image = np.asarray(image_array)
        if image.dtype != np.uint8 or image.ndim not in (2, 3):
            raise ValueError("Expected a uint8 gray/RGB/RGBA image")
        if image.shape[0] < 1 or image.shape[1] < 1:
            raise ValueError("Image dimensions must be positive")
        if image.ndim == 3 and image.shape[2] not in (3, 4):
            raise ValueError("Expected three RGB or four RGBA channels")
        # ZXing assumes BGR for ndarray input. PIL carries its RGB/RGBA mode,
        # so callers can keep the same RGB contract as the perception model.
        observations = zxingcpp.read_barcodes(Image.fromarray(np.ascontiguousarray(image)))
        codes = []
        for barcode in observations:
            raw_bytes = bytes(barcode.bytes)
            try:
                raw_value = raw_bytes.decode("utf-8", errors="strict")
                error = None
            except UnicodeDecodeError:
                raw_value = None
                error = "payload_not_utf8"
            position = barcode.position
            codes.append({
                "raw_value": raw_value,
                "raw_bytes_hex": raw_bytes.hex(),
                "format": str(barcode.format),
                "position": [[int(getattr(position, corner).x),
                              int(getattr(position, corner).y)]
                             for corner in ("top_left", "top_right", "bottom_right", "bottom_left")],
                "decoding_error": error,
            })
        return codes
    except Exception as error:
        raise CodeDecodingError(f"{type(error).__name__}: {error}") from error


def parser_configuration(parser: Mapping | None = None) -> dict:
    """Validate the deliberately small, explicitly selected payload contract."""
    config = dict(DEFAULT_PARSER if parser is None else parser)
    kind = config.get("type")
    if kind == "exact_utf8":
        if set(config) != {"type"}:
            raise ValueError("exact_utf8 accepts only the type field")
    elif kind == "json_field":
        if set(config) != {"type", "field"}:
            raise ValueError("json_field requires exactly type and field")
        if not isinstance(config["field"], str) or not config["field"]:
            raise ValueError("json_field.field must be a nonempty top-level field name")
    else:
        raise ValueError("Parser type must be exact_utf8 or json_field")
    return config


def _parse_code(code: dict, parser: dict) -> str:
    if code.get("decoding_error"):
        raise ValueError(f"Decoder observation is invalid: {code['decoding_error']}")
    value = code.get("raw_value")
    if not isinstance(value, str):
        raise ValueError("Each code requires a string raw_value")
    if "raw_bytes_hex" in code:
        payload = code["raw_bytes_hex"]
        if not isinstance(payload, str):
            raise ValueError("raw_bytes_hex must be a hexadecimal string")
        decoded = bytes.fromhex(payload).decode("utf-8", errors="strict")
        if value != decoded:
            raise ValueError("raw_value differs from its UTF-8 source bytes")
    if parser["type"] == "json_field":
        parsed = json.loads(value)
        if not isinstance(parsed, dict) or parser["field"] not in parsed:
            raise ValueError("JSON payload does not contain the configured material field")
        value = parsed[parser["field"]]
    if not isinstance(value, str) or value == "":
        raise ValueError("Parsed material identifier must be a nonempty string")
    return value


def compare_codes(codes: list[dict], expected: str | None, scope: str,
                  *, parser: Mapping | None = None) -> dict:
    """Parse observations, then compare unique identifiers within a stated scope.

    Results are MATCH, MISMATCH, NO_READ, AMBIGUOUS, PROCESSING_ERROR or UNKNOWN.
    UNKNOWN is mandatory if there is no expected identifier or the association
    scope is unconfirmed. Two distinct identifiers are ambiguous even if one
    equals the expected value. Duplicate observations of the same identifier
    may match. A malformed observation cannot be silently ignored.
    """
    result = {
        "decoder": "zxing-cpp", "parser": None,
        "identity_scope": scope, "expected_material": expected,
        "recognized_material": None, "recognized_material_candidates": [],
        "result": "PROCESSING_ERROR", "codes": [], "exceptions": [],
        "piece_identity_verified": False,
        "association_status": "UNCONFIRMED" if scope == "unconfirmed" else "DECLARED_BY_CALLER",
        "scope_note": "Code comparison does not establish visual part identity or a grasp permission.",
    }
    try:
        result["parser"] = parser_configuration(parser)
        if scope not in IDENTITY_SCOPES:
            raise ValueError(f"identity scope must be one of {IDENTITY_SCOPES}")
        if expected is not None and (not isinstance(expected, str) or expected == ""):
            raise ValueError("Expected material must be a nonempty string or null")
        if not isinstance(codes, list) or any(not isinstance(code, dict) for code in codes):
            raise ValueError("codes must be a list of dictionaries")
        result["codes"] = [dict(code) for code in codes]
        identifiers = sorted({_parse_code(code, result["parser"]) for code in codes})
        result["recognized_material_candidates"] = identifiers
        if not identifiers:
            result["result"] = "NO_READ"
        elif len(identifiers) > 1:
            result["result"] = "AMBIGUOUS"
        else:
            result["recognized_material"] = identifiers[0]
            if expected is None or scope == "unconfirmed":
                result["result"] = "UNKNOWN"
            else:
                result["result"] = "MATCH" if identifiers[0] == expected else "MISMATCH"
    except Exception as error:
        result["exceptions"].append({"type": type(error).__name__, "message": str(error)})
    return result
