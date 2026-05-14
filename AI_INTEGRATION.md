# AI integration — what is in place and how it works

> **Note:** Default **`Generate`** integration today uses **Qwen** via `services/ai_model_service.py` and `README.md` (Model Selection). The DistilGPT-2 walkthrough in §1–§2 below is a **minimal historical sketch** of the transformers stack; prefer the main README for current defaults. **`ReviewContent`** moderation is implemented in `server.py` with tests in `test_server.py`.

## 1. Open-weight model for Python

- **Model:** **DistilGPT-2** (Hugging Face: `distilgpt2`)
- **Why this choice:**
  - Runs locally on CPU, no API key or external services
  - Small footprint (~82M parameters, ~80 MB), good for demos and dev
  - Apache 2.0 license
  - Standard stack: `transformers` + `torch`

## 2. What was added

### 2.1 Service that talks to the model

- **File:** `services/ai_model_service.py`
- **Class:** `AIModelService`
- **Behavior:**
  - **Lazy loading:** weights load on first `generate()` so the server starts quickly
  - **`generate(prompt, max_new_tokens=50, ...)`** — continues the given prompt and returns prompt + generated continuation
  - Optional: `do_sample`, `temperature` (randomness / creativity)
  - Important parts of the service code are commented inline

### 2.2 gRPC integration

- **Proto:** canonical **`many_faces_proto/proto/health.proto`** defines:
  - **RPC:** `Generate(GenerateRequest) returns (GenerateResponse)`
  - **GenerateRequest:** `prompt` (string), `max_new_tokens` (int32, optional)
  - **GenerateResponse:** `text` (generated text), `error` (optional failure message)
- **Server:** `server.py`:
  - On startup, creates `AIModelService` (weights not loaded yet)
  - `HealthServiceServicer` implements `Generate`:
    - checks `AIModelService` availability,
    - calls `_ai_service.generate(prompt, max_new_tokens=...)`,
    - returns `GenerateResponse(text=..., error=...)` or an error string
  - If `transformers`/`torch` are missing, the server still runs but `Generate` returns an error in `error`

### 2.3 Dependencies and Docker

- **requirements.txt:** `transformers`, `torch`, `accelerate`
- **Dockerfile.dev:** copies `services/` into the image
- **Proto:** after editing **`many_faces_proto`** `health.proto`, regenerate Python stubs (`./scripts/generate_proto.sh`) and bump the **`many_faces_proto`** submodule where this repo is consumed.

## 3. Request flow

1. **Server start**
   - Load gRPC code from `proto/` and register `HealthService` (HealthCheck + Generate).
   - Construct `AIModelService()` — still no model weights in memory.

2. **First Generate call**
   - Client calls `Generate(prompt="The weather today is", max_new_tokens=30)`.
   - Server calls `_ai_service.generate(...)`.
   - Inside `AIModelService.generate()`, first call runs `_get_pipeline()`:
     - download or load cached `distilgpt2`,
     - build a `transformers` `text-generation` pipeline.
   - Pipeline produces continuation; returned as `GenerateResponse.text`.

3. **Later Generate calls**
   - Model stays in memory — inference only.

4. **Errors**
   - Empty `prompt` → `GenerateResponse(error="prompt is required")`.
   - Missing `transformers`/`torch` → `GenerateResponse(error="AIModelService not available...")`.
   - Exception during generation → logged; client gets `GenerateResponse(text="", error=str(e))`.

## 4. How to run and test

- **Local (with generated protos and deps installed):**
  ```bash
  pip install -r requirements.txt
  ./generate_proto.sh   # or generate per README
  python server.py
  ```
- **Docker (recommended):**

  ```bash
  ./rebuild-dev.sh
  ./start-dev.sh
  ```

  Proto generation runs during build; `services/` is copied into the image.

- **Test Generate (e.g. grpcurl):**
  ```bash
  grpcurl -plaintext -d '{"prompt": "The weather today is", "max_new_tokens": 20}' localhost:50051 health.HealthService/Generate
  ```

## 5. ReviewContent (user content moderation)

The **`ReviewContent`** RPC is defined in **`many_faces_proto/proto/health.proto`** and implemented in `server.py` (`HealthServiceServicer.ReviewContent`). Untrusted title, body, and media URL are normalized first via `moderation_input_sanitize.py`. Tests live in `test_server.py` and `test_moderation_input_sanitize.py`. End-to-end product reference: [`docs/guides/ai-assisted-content-approval.md`](../docs/guides/ai-assisted-content-approval.md) in the **`many_faces_main`** monorepo.

## 6. Summary

| Piece      | Location                          | Role                                     |
| ---------- | --------------------------------- | ---------------------------------------- |
| Open model | DistilGPT-2 (Hugging Face)        | Local text generation without an API key |
| Service    | `services/ai_model_service.py`    | Load weights, `generate()`               |
| gRPC       | `many_faces_proto` `health.proto`, `server.py` | `Generate` RPC and handler               |
| Deps       | `requirements.txt`, Dockerfile    | `transformers`, `torch`, `accelerate`    |
