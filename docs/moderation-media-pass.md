# Moderation media URL pass (AI-UP8)

Phase 1 metadata pass before optional vision (phase 2 deferred).

## Behavior

`media_url_flags` uses **`validate_public_fetch_url`** (AIH1 SSRF policy):

- Empty URL → no flags.
- Blocked host/scheme → **`suspicious_media_url`** + reason flag.
- Executable/archive extensions → **`unknown_content_type`**.

In dev, HTTP loopback may be allowed unless **`MFAI_HARDENED_PROFILE=1`**.

## ReviewContent integration

Flags merge into rules classifier output. Boundary flags **`image_analysis_boundary`** / **`video_analysis_boundary`** still trigger LLM when **`MFAI_LLM_MODERATION=1`**.

Vision model scoring (AI-UP8 phase 2) is not wired in v0.9.0.
