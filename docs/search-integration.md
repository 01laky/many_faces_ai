# Search integration (AI-UP5)

The AI worker does **not** call Elasticsearch HTTP. Search hits are supplied by **`many_faces_backend`** as JSON on **`GenerateRequest.search_hits_json`**.

## Prompt prefix

`format_search_hits_for_prompt` renders up to 10 hits:

```text
# Search hits (cite only these ids)

- id=1 title=Blog A
```

Invalid JSON is ignored (graceful degrade).

## Future: search-worker gRPC

`services/search_worker_client.py` holds a stub for **`many_faces_elastic`** gRPC (port **50052**). Set **`SEARCH_WORKER_GRPC_ADDRESS`** when the client is wired; until then the backend must pass hits inline.

## Environment

| Variable | Purpose |
| -------- | ------- |
| `SEARCH_WORKER_GRPC_ADDRESS` | e.g. `search-worker:50052` (stub in v0.9.0) |
| `SEARCH_WORKER_TOKEN` | Optional metadata token for worker auth |
