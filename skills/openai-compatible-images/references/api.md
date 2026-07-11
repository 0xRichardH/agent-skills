# OpenAI-Compatible Images API Reference

Read this file only when the default generate/edit commands are insufficient.

## Routes

- `POST /v1/images/generations` accepts JSON.
- `POST /v1/images/edits` accepts multipart form data or JSON.
- Authenticate with `Authorization: Bearer <api-key>`.
Endpoint availability and accepted models are provider-defined. Configure the model explicitly rather than relying on a provider's default.

## Generation fields

`prompt` and a configured model are required by this skill. Common optional fields:

- `n`
- `size`
- `quality`
- `background`
- `output_format`: commonly `png`, `jpeg`, or `webp`
- `output_compression`
- `moderation`
- `partial_images`
- `response_format`: `b64_json` or `url`
- `stream`
- `aspect_ratio` and `resolution` when supported by the provider

## Edit fields

Multipart edits require `prompt` and at least one `image` or `image[]`. Optional fields include:

- `model`
- `mask`
- `n`
- `size`
- `quality`
- `background`
- `output_format`
- `output_compression`
- `input_fidelity`
- `moderation`
- `partial_images`
- `response_format`
- `stream`

JSON edits commonly use `images: [{"image_url":"..."}]` and optional `mask: {"image_url":"..."}`. Support for file IDs and exact field names is provider-dependent; the bundled client uses multipart uploads for broader compatibility.

## Responses

Non-streaming responses guarantee `created` and `data`. Each data item may contain `b64_json` or `url`; a `url` may be a base64 data URL rather than a hosted URL. Optional metadata includes `revised_prompt`, `background`, `output_format`, `quality`, `size`, and `usage`.

Generation streaming events:

- `image_generation.partial_image`
- `image_generation.completed`

Edit streaming events:

- `image_edit.partial_image`
- `image_edit.completed`

Events contain `b64_json` or a data `url` according to `response_format`. The bundled client intentionally uses non-streaming responses; implement streaming only when partial previews are an explicit requirement.
