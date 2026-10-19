#!/usr/bin/env python3
"""Generate synthetic QR inputs and exercise actual local ZXing-C++ decoding."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

if __package__:
    from .material import CodeDecodingError, compare_codes, decode_codes
else:
    from material import CodeDecodingError, compare_codes, decode_codes


MATERIAL_A = "APP2-SYNTHETIC-MATERIAL-A"
MATERIAL_B = "APP2-SYNTHETIC-MATERIAL-B"
ZXING_VERSION = "3.1.1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New directory; includes inputs/*.png and result.json")
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        parser.error("output-dir already exists; prior evidence must not be overwritten")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "schema_version": "app2-code-smoke-1.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FAIL", "synthetic_input": True,
        "physical_control": "NOT_CONNECTED", "piece_identity_verified": False,
        "configuration": {
            "required_zxing_cpp_version": ZXING_VERSION,
            "format": "QRCode", "scale": 8, "add_quiet_zones": True,
            "payload_parser": {"type": "exact_utf8"}, "identity_scope": "box",
            "materials": [MATERIAL_A, MATERIAL_B],
        },
        "versions": {}, "inputs": {}, "cases": {},
        "sources": [
            "https://pypi.org/project/zxing-cpp/3.1.1/",
            "https://github.com/zxing-cpp/zxing-cpp/blob/master/wrappers/python/zxing.cpp",
        ],
        "limitations": [
            "Synthetic QR infrastructure check, not validation of customer labels or part identity.",
            "No confidence metric is provided by this decoder contract.",
            "PROCESSING_ERROR checks rejection of an invalid image; it does not simulate hardware faults.",
        ],
    }
    try:
        import numpy as np
        from PIL import Image
        import zxingcpp

        result["versions"] = {name: importlib.metadata.version(name)
                              for name in ("zxing-cpp", "numpy", "Pillow")}
        if result["versions"]["zxing-cpp"] != ZXING_VERSION:
            raise RuntimeError(f"Expected zxing-cpp {ZXING_VERSION}; found {result['versions']['zxing-cpp']}")
        inputs = output / "inputs"
        inputs.mkdir()

        def qr(payload: str) -> Image.Image:
            barcode = zxingcpp.create_barcode(payload, zxingcpp.BarcodeFormat.QRCode)
            bitmap = zxingcpp.write_barcode_to_image(barcode, scale=8, add_quiet_zones=True)
            return Image.fromarray(np.asarray(bitmap)).convert("RGB")

        qr_a, qr_b = qr(MATERIAL_A), qr(MATERIAL_B)
        margin = 40
        width = max(640, qr_a.width + 2 * margin)
        height = max(400, qr_a.height + 2 * margin)
        known = Image.new("RGB", (width, height), "white")
        known.paste(qr_a, ((width - qr_a.width) // 2, (height - qr_a.height) // 2))
        blank = Image.new("RGB", known.size, "white")
        ambiguous = Image.new("RGB", (qr_a.width + qr_b.width + 3 * margin,
                                      max(qr_a.height, qr_b.height) + 2 * margin), "white")
        ambiguous.paste(qr_a, (margin, margin))
        ambiguous.paste(qr_b, (2 * margin + qr_a.width, margin))
        arrays = {}
        for name, image in (("known", known), ("blank", blank), ("ambiguous", ambiguous)):
            path = inputs / f"{name}.png"
            image.save(path)
            # Exercise the saved file, which is also the input to integrated GPU demos.
            with Image.open(path) as saved:
                arrays[name] = np.asarray(saved.convert("RGB")).copy()
            result["inputs"][name] = {"path": str(path), "sha256": sha256(path),
                                      "width": image.width, "height": image.height,
                                      "synthetic": True}
        observations = {name: decode_codes(image) for name, image in arrays.items()}
        if [code["raw_value"] for code in observations["known"]] != [MATERIAL_A]:
            raise AssertionError("Known QR did not yield exactly the generated payload")
        if {code["raw_value"] for code in observations["ambiguous"]} != {MATERIAL_A, MATERIAL_B}:
            raise AssertionError("Ambiguous input did not yield both distinct QR payloads")
        for case, source, expected in (("MATCH", "known", MATERIAL_A),
                                       ("MISMATCH", "known", MATERIAL_B),
                                       ("NO_READ", "blank", MATERIAL_A),
                                       ("AMBIGUOUS", "ambiguous", MATERIAL_A)):
            comparison = compare_codes(observations[source], expected, "box")
            result["cases"][case] = {"input": source, "comparison": comparison,
                                      "expected_result": case, "passed": comparison["result"] == case}
        try:
            decode_codes(np.zeros((0, 0), dtype=np.uint8))
        except CodeDecodingError as error:
            comparison = compare_codes([{"raw_value": None, "decoding_error": str(error)}], MATERIAL_A, "box")
            result["cases"]["PROCESSING_ERROR"] = {
                "input": "invalid_zero_dimension_image", "comparison": comparison,
                "expected_result": "PROCESSING_ERROR", "passed": comparison["result"] == "PROCESSING_ERROR",
                "decoder_exception": {"type": type(error).__name__, "message": str(error)},
            }
        else:
            raise AssertionError("Invalid image was accepted instead of producing a processing error")
        for case, expected, scope in (("UNKNOWN_EXPECTED", None, "box"),
                                      ("UNKNOWN_SCOPE", MATERIAL_A, "unconfirmed")):
            comparison = compare_codes(observations["known"], expected, scope)
            result["cases"][case] = {"input": "known", "comparison": comparison,
                                      "expected_result": "UNKNOWN", "passed": comparison["result"] == "UNKNOWN"}
        result["status"] = "PASS" if all(case["passed"] for case in result["cases"].values()) else "FAIL"
    except Exception as error:
        result["exception"] = {"type": type(error).__name__, "message": str(error)}
    result["source_sha256"] = {
        name: sha256(Path(__file__).parent / name) for name in ("code_smoke.py", "material.py")}
    (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2,
                                                   sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(output),
                      "cases_passed": sum(case["passed"] for case in result["cases"].values())}))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
