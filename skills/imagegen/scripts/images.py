#!/usr/bin/env python3
"""Generate and edit images through an OpenAI-compatible Images API."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "http://localhost:8317"
FORMAT_EXTENSIONS = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "webp": "webp"}
CONTENT_EXTENSIONS = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/webp": "webp"}


def env_value(primary: str, fallback: str | None = None, default: str | None = None) -> str | None:
    return os.getenv(primary) or (os.getenv(fallback) if fallback else None) or default


def api_url(base_url: str, route: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/{route.lstrip('/')}"
    return f"{base}/v1/{route.lstrip('/')}"


def parse_extra(value: str) -> tuple[str, Any]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("extra fields must use key=value")
    key, raw = value.split("=", 1)
    if not key:
        raise argparse.ArgumentTypeError("extra field key cannot be empty")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = raw
    return key, parsed


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prompt", required=True, help="Image prompt or edit instruction")
    parser.add_argument("--model", default=env_value("OPENAI_IMAGE_MODEL"))
    parser.add_argument("--base-url", default=env_value("OPENAI_BASE_URL", default=DEFAULT_BASE_URL))
    parser.add_argument("--api-key", default=env_value("OPENAI_API_KEY"))
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--size")
    parser.add_argument("--quality")
    parser.add_argument("--background")
    parser.add_argument("--output-format", choices=sorted(FORMAT_EXTENSIONS))
    parser.add_argument("--output-compression", type=int)
    parser.add_argument("--moderation")
    parser.add_argument("--input-fidelity")
    parser.add_argument("--response-format", choices=("b64_json", "url"), default="b64_json")
    parser.add_argument("--extra", action="append", default=[], type=parse_extra, metavar="KEY=VALUE")
    parser.add_argument("--output-dir", type=Path, default=Path("generated-images"))
    parser.add_argument("--output-prefix", default="image")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate images from a prompt")
    add_common_arguments(generate)
    generate.add_argument("--aspect-ratio")
    generate.add_argument("--resolution")

    edit = subparsers.add_parser("edit", help="Edit or compose source images")
    add_common_arguments(edit)
    edit.add_argument("--image", action="append", required=True, type=Path, help="Source image; repeat as needed")
    edit.add_argument("--mask", type=Path)
    return parser


def request_headers(api_key: str | None) -> dict[str, str]:
    if not api_key:
        raise ValueError("missing API key: set OPENAI_API_KEY or pass --api-key")
    return {"Authorization": f"Bearer {api_key}", "User-Agent": "imagegen-skill/1.0"}


def optional_fields(args: argparse.Namespace) -> dict[str, Any]:
    names = (
        "size", "quality", "background", "output_format", "output_compression",
        "moderation", "input_fidelity", "aspect_ratio", "resolution",
    )
    fields = {name: getattr(args, name) for name in names if hasattr(args, name) and getattr(args, name) is not None}
    fields.update(dict(args.extra))
    return fields


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={**headers, "Content-Type": "application/json"}, method="POST")
    return open_json(request)


def multipart_body(fields: dict[str, Any], files: list[tuple[str, Path]]) -> tuple[bytes, str]:
    boundary = f"----openai-images-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            str(value).lower().encode() if isinstance(value, bool) else str(value).encode(),
            b"\r\n",
        ])
    for name, path in files:
        if not path.is_file():
            raise ValueError(f"input file does not exist: {path}")
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'.encode(),
            f"Content-Type: {mime}\r\n\r\n".encode(),
            path.read_bytes(),
            b"\r\n",
        ])
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def post_multipart(url: str, headers: dict[str, str], fields: dict[str, Any], files: list[tuple[str, Path]]) -> tuple[dict[str, Any], str | None]:
    body, content_type = multipart_body(fields, files)
    request = urllib.request.Request(url, data=body, headers={**headers, "Content-Type": content_type}, method="POST")
    return open_json(request)


def open_json(request: urllib.request.Request) -> tuple[dict[str, Any], str | None]:
    try:
        with urllib.request.urlopen(request) as response:
            content_type = response.headers.get_content_type()
            payload = json.loads(response.read().decode("utf-8"))
            return payload, content_type
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"image API returned HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"could not reach image API: {error.reason}") from error


def decode_data_url(url: str) -> tuple[bytes, str | None]:
    match = re.fullmatch(r"data:([^;,]+)?(;base64)?,(.*)", url, re.DOTALL)
    if not match:
        raise ValueError("invalid data URL returned by image API")
    mime, base64_flag, data = match.groups()
    raw = base64.b64decode(data) if base64_flag else urllib.parse.unquote_to_bytes(data)
    return raw, mime


def fetch_image_url(url: str) -> tuple[bytes, str | None]:
    if url.startswith("data:"):
        return decode_data_url(url)
    with urllib.request.urlopen(url) as response:
        return response.read(), response.headers.get_content_type()


def extension_for(response: dict[str, Any], mime: str | None) -> str:
    declared = str(response.get("output_format", "")).lower()
    return FORMAT_EXTENSIONS.get(declared) or CONTENT_EXTENSIONS.get(mime or "") or "png"


def save_outputs(response: dict[str, Any], output_dir: Path, prefix: str) -> list[Path]:
    items = response.get("data")
    if not isinstance(items, list) or not items:
        raise RuntimeError(f"image API returned no image data: {json.dumps(response, ensure_ascii=False)}")
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"unexpected image item: {item!r}")
        if item.get("b64_json"):
            raw = base64.b64decode(item["b64_json"])
            mime = None
        elif item.get("url"):
            raw, mime = fetch_image_url(item["url"])
        else:
            raise RuntimeError(f"image item contains neither b64_json nor url: {json.dumps(item)}")
        if not raw:
            raise RuntimeError(f"image item {index} decoded to an empty file")
        path = output_dir / f"{prefix}-{index}.{extension_for(response, mime)}"
        path.write_bytes(raw)
        paths.append(path.resolve())
    return paths


def run(args: argparse.Namespace) -> int:
    if not args.model:
        raise ValueError("missing image model: set OPENAI_IMAGE_MODEL or pass --model")
    headers = request_headers(args.api_key)
    common: dict[str, Any] = {
        "model": args.model,
        "prompt": args.prompt,
        "n": args.n,
        "response_format": args.response_format,
        **optional_fields(args),
    }
    if args.command == "generate":
        response, _ = post_json(api_url(args.base_url, "images/generations"), headers, common)
    else:
        fields = common
        files = [("image[]", path) for path in args.image]
        if args.mask:
            files.append(("mask", args.mask))
        response, _ = post_multipart(api_url(args.base_url, "images/edits"), headers, fields, files)

    paths = save_outputs(response, args.output_dir, args.output_prefix)
    result = {
        "model": args.model,
        "outputs": [str(path) for path in paths],
        "revised_prompts": [item.get("revised_prompt") for item in response.get("data", []) if item.get("revised_prompt")],
        "usage": response.get("usage"),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    try:
        return run(build_parser().parse_args())
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError, base64.binascii.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
