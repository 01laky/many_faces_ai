# Embeddings (AI-UP15)

**`EmbedText`** RPC calls Ollama **`/api/embeddings`**.

## Limits

| Env | Default | Meaning |
| --- | ------- | ------- |
| `OLLAMA_EMBED_MAX_BATCH` | `8` | Max texts per request |
| `OLLAMA_EMBED_MAX_CHARS` | `8000` | Per-text character cap |
| `OLLAMA_MODEL_EMBED` | falls back to `OLLAMA_MODEL` | Embedding model |

## Errors

Stable gRPC **`EmbedTextResponse.error`** strings: `texts required`, `batch exceeds N`, `embeddings unavailable`, `missing embedding vector`.

No raw prompt text is returned in usage or metrics payloads.
