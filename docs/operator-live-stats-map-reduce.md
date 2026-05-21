# Operator live stats — live map-reduce (v1)

Canonical reference for **admin operator AI `live` stats mode** (map-reduce over 61 EF entity bundles).

## Architecture (Option B — backend orchestrator)

| Stage | Where | What |
| --- | --- | --- |
| 1 | **Backend** (`OperatorAiLiveStatsPrefetcher`) | Prefetch **all 61** entity bundles from DB into cache (**not** LLM) |
| 2 | **Backend + `Generate` gRPC** | Planner LLM call returns JSON `{"indices":[...]}` |
| 3 | **Backend** | Per-index barrier — wait until bundle JSON ready |
| 4 | **Backend + `Generate` gRPC** | Queued per-bundle AI (max **N** parallel, default **2**) |
| 5 | **Backend** (`OperatorAiLiveStatsStitch`) | Deterministic stitch → one operator reply |

Python modules `live_stats_planner.py` and `live_stats_stitch.py` mirror parse/stitch logic for unit tests; **orchestration runs in C#** today.

## Key backend types

- `many_faces_backend/BeDemo.Api/Services/OperatorAi/OperatorAiEntityBundleCatalog.cs` — indices 0–60
- `OperatorAiEntityBundleLoader.cs` — aggregate queries per entity
- `OperatorAiLiveStatsOrchestrator.cs` — full pipeline
- `ChatHub.SendToAiWithOperatorStats(..., maxParallelBundleAiCalls?)` — `live` branch only

## Configuration

`OperatorAi` section in backend `appsettings.json`:

- `MaxParallelBundleAiCalls` (default 2)
- `MaxSelectedBundleIndices` (default 4)
- `LiveTotalTimeoutSeconds`, `LivePrefetchTimeoutSeconds`, token limits

Admin browser: `localStorage` key `admin_ai_live_max_parallel_bundle_calls` (1–8).

## Tests

```bash
# Backend
dotnet test --filter FullyQualifiedName~OperatorAiLiveStats

# Python (from many_faces_ai/)
PYTHONPATH=. pytest tests/test_live_stats.py -q

# Admin
yarn test --run src/utils/__tests__/adminAiLiveParallelSettings.test.ts
```

## Related

- Agent prompt: `docs/prompts/admin-operator-ai-live-stats-bundle-map-reduce-agent-prompt.md`
- Runbook: `docs/guides/backend-stats-and-admin-ai-runbook.md` (update when deploying)
