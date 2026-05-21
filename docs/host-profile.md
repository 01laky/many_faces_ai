# AI worker host profile

The Python gRPC worker collects a **host profile** locally when the backend calls `GetHostProfile`. The backend persists the snapshot on startup and exposes it to operators in **Admin → Settings → AI configuration → AI worker host**.

## What is collected

- OS, hostname, CPU, GPU (via `nvidia-smi` when available), RAM/swap, disk partitions
- Ollama runtime details (`/api/tags`, `/api/show`, `/api/ps`, env `OLLAMA_NUM_CTX`, `OLLAMA_NUM_GPU`)
- Stable `workerInstanceId` (hashed — no MAC addresses in clear text)

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST_PROFILE_SCOPE` | `auto` | `host`, `container`, or auto-detect Docker/Kubernetes |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama HTTP API |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct-q4_K_M` | Configured model name |

## Dev topology (Mac backend + Windows AI)

1. Run `many_faces_ai` on the Windows machine (bare metal or Docker with GPU passthrough).
2. Point backend `AI_SERVICE_GRPC_ADDRESS` at the Windows host (direct IP or `host.docker.internal:50051` via socat relay).
3. Restart the backend — startup refresh calls `GetHostProfile` and upserts PostgreSQL.
4. Admin Settings shows the **Windows** hostname/GPU, while `grpcAddressConfigured` shows what the Mac backend used to connect.

## grpcurl smoke test

Reflection is disabled; pass the proto file explicitly:

```bash
grpcurl -plaintext -import-path many_faces_proto/proto -proto health.proto \
  -d '{}' localhost:50051 health.HealthService/GetHostProfile
```

## Tests

```bash
pytest tests/test_host_profile_collector.py -q
```
