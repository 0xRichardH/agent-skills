---
name: openai-compatible-images
description: Generate or edit images through OpenAI-compatible image APIs. Load when the user wants an image created, transformed, masked, or composed and the work should use a configured OpenAI-compatible endpoint rather than a built-in image tool.
---

# OpenAI-Compatible Images

Turn an image request into saved image files through an OpenAI-compatible API. Use the bundled client so request construction, base64 decoding, data-URL handling, and file naming stay deterministic.

## Workflow

1. Resolve the endpoint and credentials from `OPENAI_BASE_URL` and `OPENAI_API_KEY`. The endpoint may be either the API root or include `/v1`.
2. Resolve the model from an explicit user choice or `OPENAI_IMAGE_MODEL`. If neither is available, ask for an image model rather than guessing.
3. Choose the branch:
   - **Generate** when the user supplies no source image.
   - **Edit** when the user supplies one or more source images; add `--mask` only when a mask is supplied.
4. Translate the request into a concrete prompt that preserves the user's subject, composition, style, text, and constraints. Keep requested wording exact when text must appear in the image.
5. Run `scripts/images.py generate` or `scripts/images.py edit`. Prefer non-streaming `b64_json`; it yields durable local artifacts across compatibility providers.
6. Verify that every reported output path exists and is a non-empty image. Return the paths plus the model and material options used. Completion means every requested image has been saved or the upstream error has been reported with its response body.

## Commands

Generate:

```bash
python scripts/images.py generate \
  --prompt "A red cat sitting beside a window" \
  --size 1024x1024 \
  --output-dir ./generated
```

Edit one or more images:

```bash
python scripts/images.py edit \
  --prompt "Change the cat from red to blue" \
  --image ./cat.png \
  --output-dir ./edited
```

Use repeated `--image` flags for composition and `--mask ./mask.png` for masked edits. Pass provider-specific fields with `--extra key=value`; use JSON values for numbers, booleans, arrays, or objects.

Read [`references/api.md`](references/api.md) when selecting provider-specific fields, diagnosing an upstream compatibility issue, or implementing streaming. Run `python scripts/images.py --help` for the complete local interface.

## Defaults and Boundaries

- Model precedence: explicit `--model`, then `OPENAI_IMAGE_MODEL`; absence is a configuration error.
- Default output directory: `./generated-images`.
- Default format: `png`; the response's declared format takes precedence.
- Edits use multipart uploads because that is the broadest compatible form and avoids loading source images into model context.
- Treat a returned `url` as either an HTTP URL or a data URL; the client handles both.
- Keep credentials in environment variables and out of prompts, command output, and generated files.
