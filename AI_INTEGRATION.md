# AI integration — what is in place and how it works

`many_faces_ai` is now a lightweight gRPC adapter. It does not load Hugging Face,
PyTorch, or Transformers models in-process. Text generation is delegated to a local
Ollama server over HTTP.

## 1. Model runtime

- **Runtime:** Ollama
- **Default model:** `qwen2.5:7b-instruct-q4_K_M`
- **Why:** keeps the app's existing gRPC contract while letting Ollama handle GGUF
  quantization, GPU offload, CPU/RAM fallback, context size, and model caching.

Recommended Windows RTX 3050 4GB / 10GB RAM / 8 thread starting point:

```bash
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M
OLLAMA_NUM_CTX=4096
OLLAMA_NUM_THREAD=8
OLLAMA_NUM_GPU=20
OLLAMA_NUM_BATCH=128
```

## 2. Service behavior

- **File:** `services/ai_model_service.py`
- **Class:** `AIModelService`
- **Behavior:**
  - checks model availability with Ollama `/api/show`
  - maps backend prompts to Ollama chat messages
  - preserves operator dashboard/timeseries JSON as system context
  - calls Ollama `/api/chat` with `stream=false`
  - returns generated text to the existing gRPC `Generate` response

## 3. Request flow

1. Backend calls `Generate(prompt, max_new_tokens, stats_context_json?)` over gRPC.
2. `server.py` prepends optional operator statistics JSON before the prompt.
3. `AIModelService` parses prompt/history into chat messages.
4. `AIModelService` calls Ollama `/api/chat`.
5. Response text is sanitized and returned to the backend.

## 4. Dependencies and Docker

- **requirements.txt:** gRPC/protobuf/test/lint dependencies only
- **Dockerfile.dev:** builds the gRPC adapter image and generated proto stubs
- **No:** `torch`, `transformers`, `accelerate`, Hugging Face model cache

## 5. How to run and test

1. Start Ollama and pull the model:

   ```bash
   ollama pull qwen2.5:7b-instruct-q4_K_M
   ```

2. Start the gRPC adapter:

   ```bash
   docker compose -f docker-compose.dev.yml up -d --build ai-demo-dev
   ```

3. Verify:

   ```bash
   docker logs ai-demo-dev --tail 100
   ```

## 6. ReviewContent

The `ReviewContent` RPC is still implemented in `server.py` as a deterministic
keyword/media fallback. It does not depend on Ollama.
