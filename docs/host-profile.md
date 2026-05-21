# AI worker host profile

The Python gRPC worker collects a **host profile** locally when the backend calls `GetHostProfile`. The backend persists the snapshot on startup and exposes it to operators in **Admin → Settings → AI configuration → AI worker host**.

## What is collected

- OS, hostname, CPU, GPU (via `nvidia-smi` when available), RAM/swap, disk partitions
- Ollama runtime details (`/api/tags`, `/api/show`, `/api/ps`, env `OLLAMA_NUM_CTX`, `OLLAMA_NUM_GPU`)
- Stable `workerInstanceId` (hashed — no MAC addresses in clear text)

## Windows AI-only machine

On a Windows PC that runs **only** the AI worker, Linux Docker cannot execute `nvidia-smi.exe` or read real GPU/RAM from inside the container. Use the Windows host collector before starting the container:

```powershell
cd many_faces_ai
.\scripts\start-ai-docker.ps1
```

This runs `collect_windows_host_profile.ps1` on Windows (RTX, hostname, RAM), writes `.host-profile-snapshot.d/host_profile_injected.json`, then `docker compose -f ../docker-compose.dev.yml -f ../docker-compose.ai-windows.yml up -d --build ai-demo-dev`.

After restart, refresh the Mac backend (`docker compose restart be-demo-dev`) so Admin loads the new profile.

## Automatic collection at container start

No manual scripts are required. Every `ai-demo-dev` start/restart runs `scripts/entrypoint.sh`, which calls `scripts/refresh_host_snapshot.py` before the gRPC server starts.

Refresh order:

1. **Host agent (Mac / native host)** — POST `http://host.docker.internal:9765/v1/collect` when `host-profile-agent` is running on the physical machine. `start-all-dev.sh` starts this agent automatically when `ENABLE_AI=1`.
2. **Docker Desktop Windows host probing** — when `C:` is mounted (`/run/desktop/mnt/host/c` or `/mnt/c`), the entrypoint runs `nvidia-smi.exe` and PowerShell on the Windows host (RTX 3050, real hostname, RAM).
3. **Fallback** — container-scope profile if neither path is available.

Snapshot file (bind-mounted):

`many_faces_ai/.host-profile-snapshot.d/host_profile_injected.json` → `/app/injected/host_profile_injected.json`

Inside the running container, `collect_host_profile()` merges this injected snapshot with live Ollama `aiRuntime`.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST_PROFILE_INJECTED_PATH` | `/app/injected/host_profile_injected.json` | JSON snapshot path inside the container |
| `HOST_PROFILE_AGENT_URL` | `http://host.docker.internal:9765` | Host-side collector HTTP endpoint |
| `HOST_PROFILE_AGENT_PORT` | `9765` | Port for `host_profile_agent.py` on the physical machine |
| `HOST_NVIDIA_SMI_PATHS` | — | Extra comma-separated `nvidia-smi` paths (Windows `.exe` in Docker) |
| `HOST_PROFILE_SCOPE` | `auto` | Force `host` or `container` when building snapshots |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama HTTP API |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct-q4_K_M` | Configured model name |

## Dev topology (Mac backend + Windows AI)

1. On Windows: `docker compose -f docker-compose.dev.yml up -d ai-demo-dev` — entrypoint collects RTX/host info automatically.
2. On Mac with `start-all-dev.sh`: host agent starts automatically; entrypoint refreshes snapshot on each AI container start.
3. Point backend `AI_SERVICE_GRPC_ADDRESS` at the Windows host IP.
4. Restart backend — Admin Settings shows host GPU/hostname.

## grpcurl smoke test

```bash
grpcurl -plaintext -import-path many_faces_proto/proto -proto health.proto \
  -d '{}' localhost:50051 health.HealthService/GetHostProfile
```

Expect `"scope":"host"` and `"injectedFromHost":true` after a successful automatic refresh.

## Tests

```bash
pytest tests/test_host_profile_collector.py tests/test_host_profile_refresh.py -q
```
