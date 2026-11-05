#!/usr/bin/env python3
"""Evaluate a saved image with ER 2; never connects to robot controls.

--check is local only. --run explicitly sends the selected image and prompt to
Google. API keys are read from environment variables and never stored. Outputs
are private evidence, not annotations or control commands.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


MODEL = "gemini-robotics-er-2-preview"
SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "observed_count": {"type": "INTEGER"},
        "objects": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "id": {"type": "INTEGER"},
                    "box_yxyx": {"type": "ARRAY", "items": {"type": "INTEGER"}},
                    "description": {"type": "STRING"},
                },
                "required": ["id", "box_yxyx", "description"],
            },
        },
        "identification_limitations": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["observed_count", "objects", "identification_limitations"],
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def validate_result(value):
    if not isinstance(value, dict):
        raise ValueError("Result must be an object")
    count = value.get("observed_count")
    objects = value.get("objects")
    if type(count) is not int or count < 0 or not isinstance(objects, list):
        raise ValueError("Invalid count or objects")
    if count != len(objects):
        raise ValueError("Count does not match object list")
    identifiers = set()
    for obj in objects:
        identifier = obj.get("id")
        if type(identifier) is not int or identifier in identifiers:
            raise ValueError("Invalid or duplicate object ID")
        identifiers.add(identifier)
        box = obj.get("box_yxyx")
        if not isinstance(box, list) or len(box) != 4:
            raise ValueError("Bounding box needs four coordinates")
        if any(type(v) is not int or not 0 <= v <= 1000 for v in box):
            raise ValueError("Invalid normalized bounding box")
        if not (box[0] < box[2] and box[1] < box[3]):
            raise ValueError("Empty or reversed bounding box")
        if not isinstance(obj.get("description"), str):
            raise ValueError("Missing description")
    limitations = value.get("identification_limitations")
    if not isinstance(limitations, list) or any(not isinstance(v, str) for v in limitations):
        raise ValueError("Invalid identification limitations")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Validate local inputs; no network")
    mode.add_argument("--run", action="store_true", help="Send the selected image to Google")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--key-env", choices=["GOOGLE_API_KEY", "GEMINI_API_KEY"], default="GOOGLE_API_KEY")
    args = parser.parse_args()
    data = args.image.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    else:
        parser.error("Only PNG/JPEG images are accepted")
    if len(data) > 8_000_000:
        parser.error("Image exceeds the 8 MB pilot limit")
    prompt = args.prompt_file.read_text().strip()
    if not prompt or len(prompt) > 16_000:
        parser.error("Prompt must contain 1 to 16000 characters")
    key = os.environ.get(args.key_env)
    metadata = {
        "model": MODEL,
        "image_path": str(args.image.resolve()),
        "image_sha256": hashlib.sha256(data).hexdigest(),
        "image_bytes": len(data),
        "mime_type": mime,
        "prompt": prompt,
        "key_env_name": args.key_env,
        "credential_present": bool(key),
        "robot_control": False,
    }
    if args.check:
        print(json.dumps({k: v for k, v in metadata.items() if k != "prompt"}))
        return 0 if key else 2
    if not key:
        parser.error("Selected API-key environment variable is empty")
    if args.output_dir is None:
        parser.error("--run requires --output-dir (new directory)")
    args.output_dir.mkdir(parents=True, mode=0o700, exist_ok=False)

    def save(name, value):
        path = args.output_dir / name
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        path.chmod(0o600)

    save("request-metadata.json", metadata)
    payload = {
        "contents": [{"role": "user", "parts": [
            {"text": prompt},
            {"inlineData": {"mimeType": mime, "data": base64.b64encode(data).decode("ascii")}},
        ]}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
            "responseSchema": SCHEMA,
        },
    }
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    start = time.monotonic()
    try:
        with build_opener(NoRedirect()).open(request, timeout=45) as response:
            body = json.load(response)
    except HTTPError as exc:
        try:
            error = json.loads(exc.read(100_000)).get("error", {})
        except (ValueError, UnicodeError):
            error = {}
        safe_error = {
            "http_status": exc.code,
            "status": error.get("status"),
            "reasons": [x.get("reason") for x in error.get("details", []) if isinstance(x, dict) and x.get("reason")],
            "elapsed_s": time.monotonic() - start,
        }
        save("error.json", safe_error)
        print(json.dumps(safe_error))
        return 2
    except (URLError, TimeoutError):
        safe_error = {"status": "NETWORK_OR_TIMEOUT", "elapsed_s": time.monotonic() - start}
        save("error.json", safe_error)
        print(json.dumps(safe_error))
        return 2
    elapsed = time.monotonic() - start
    save("response.json", body)
    candidates = body.get("candidates", [])
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    output = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    try:
        result = json.loads(output)
        validate_result(result)
    except (ValueError, TypeError, AttributeError):
        save("validation.json", {"valid": False, "elapsed_s": elapsed, "finish_reason": candidates[0].get("finishReason") if candidates else None})
        print(json.dumps({"status": "INVALID_OUTPUT", "elapsed_s": elapsed}))
        return 2
    save("result.json", result)
    summary = {"valid": True, "elapsed_s": elapsed, "observed_count": result["observed_count"], "model_version": body.get("modelVersion"), "usage": body.get("usageMetadata"), "robot_control": False}
    save("validation.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
