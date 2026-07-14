# OpenAI-Compatible Images API Reference

Read this file only when the default generate/edit commands are insufficient.

## Routes

- `POST /v1/images/generations` accepts JSON.
- `POST /v1/images/edits` accepts multipart form data or JSON.
- Authenticate with `Authorization: Bearer <api-key>`.

Endpoint availability and accepted models are provider-defined. Configure the model explicitly rather than relying on a provider's default. The Image API is the right branch for one-shot generation and edits; conversational multi-turn image workflows belong to a compatible Responses API and are outside the bundled client's scope.

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

For current OpenAI GPT Image models, `size`, `quality`, and `background` may accept `auto`. Popular sizes include `1024x1024`, `1536x1024`, and `1024x1536`; newer models may accept additional resolutions. JPEG is generally faster than PNG. `output_compression` applies to JPEG and WebP and ranges from 0 to 100.

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

For OpenAI GPT Image masks, the mask and first input image must have the same dimensions and format, be under 50 MB, and the mask must contain an alpha channel. The mask is guidance rather than a pixel-exact boundary. When multiple input images are supplied, the mask applies to the first image. `input_fidelity` is model-dependent and should be omitted when the selected model fixes fidelity internally.

## Responses

Non-streaming responses guarantee `created` and `data`. Each data item may contain `b64_json` or `url`; a `url` may be a base64 data URL rather than a hosted URL. Optional metadata includes `revised_prompt`, `background`, `output_format`, `quality`, `size`, and `usage`.

Generation streaming events:

- `image_generation.partial_image`
- `image_generation.completed`

Edit streaming events:

- `image_edit.partial_image`
- `image_edit.completed`

Events contain `b64_json` or a data `url` according to `response_format`. The bundled client intentionally uses non-streaming responses; implement streaming only when partial previews are an explicit requirement. Partial images may add cost.

## Errors

Preserve the upstream response body and request ID for diagnostics. Retry transient rate-limit and server failures only when the provider indicates they are retryable. Image user errors—including moderation blocks, invalid masks, unsupported fields, and unsupported output options—require changing the prompt or request rather than repeating it unchanged.
