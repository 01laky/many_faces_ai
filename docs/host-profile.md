# AI worker host profile

The Python gRPC worker collects a **host profile** locally when the backend calls `GetHostProfile`. The backend persists the snapshot on startup and exposes it to operators in **Admin → Settings → AI configuration → AI worker host**.

## What is collected

- OS, hostname, CPU, GPU (via `nvidia-smi` when available), RAM/swap, disk partitions
- Ollama runtime details (`/api/tags`, `/api/show`, `/api/ps`, env `OLLAMA_NUM_CTX`, `OLLAMA_NUM_GPU`)
- Stable `workerInstanceId` (hashed — no MAC addresses in clear text)

## Docker with real host hardware (Option A)

When `ai-demo-dev` runs in Docker without GPU passthrough, live collection inside the container only sees the Linux cgroup (no RTX card, container hostname). Use a **host snapshot** collected on the physical machine before `docker compose up`:

1. On the Windows/Mac/Linux **host** (not inside the container), run:

   ```bash
   # Mac / Linux
   ./many_faces_ai/scripts/collect_host_snapshot.sh

   # Windows PowerShell
   .\many_faces_ai\scripts\collect-host-profile.ps1
   ```

   This writes `many_faces_ai/.host-profile.snapshot.json` with `scope: host`, real GPU/RAM/OS, and no stale Ollama block.

2. Start or restart the AI container (snapshot is bind-mounted read-only):

   ```bash
   docker compose -f docker-compose.dev.yml up -d ai-demo-dev
   ```

   Or use the helper:

   ```bash
   ./many_faces_ai/scripts/start-ai-docker.sh   # Mac/Linux
   .\many_faces_ai\scripts\start-ai-docker.ps1  # Windows
   ```

3. Inside the container, `collect_host_profile()` merges the injected snapshot for hardware/OS and probes Ollama live for `aiRuntime`. Admin shows **host** scope with RTX 3050 (or whatever the host script detected).

`scripts/start-all-dev.sh` runs the snapshot step automatically when `ENABLE_AI=1`.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST_PROFILE_SCOPE` | `auto` | `host`, `container`, or auto-detect Docker/Kubernetes (host snapshot script forces `host`) |
| `HOST_PROFILE_INJECTED_PATH` | `/app/host_profile_injected.json` | JSON snapshot path inside the container |
| `HOST_PROFILE_USE_INJECTED` | auto in Docker | Set `1` to force merge outside Docker; `0` to ignore injection |
| `HOST_PROFILE_SNAPSHOT_FILE` | `many_faces_ai/.host-profile.snapshot.json` | Output path for host-side collector scripts |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama HTTP API |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct-q4_K_M` | Configured model name |

## Dev topology (Mac backend + Windows AI)

1. On Windows: run `collect-host-profile.ps1`, then `start-ai-docker.ps1` (or root `start-all-dev.sh` on Mac side after snapshot on Windows).
2. Point backend `AI_SERVICE_GRPC_ADDRESS` at the Windows host (direct IP or `host.docker.internal:50051` via socat relay).
3. Restart the backend — startup refresh calls `GetHostProfile` and upserts PostgreSQL.
4. Admin Settings shows the **Windows** hostname/GPU, while `grpcAddressConfigured` shows what the Mac backend used to connect.

## grpcurl smoke test

Reflection is disabled; pass the proto file explicitly:

```bash
grpcurl -plaintext -import-path many_faces_proto/proto -proto health.proto \
  -d '{}' localhost:50051 health.HealthService/GetHostProfile
```

Expect `"scope":"host"` and `"injectedFromHost":true` when the snapshot mount is active.

## Tests

```bash
pytest tests/test_host_profile_collector.py -q
```
