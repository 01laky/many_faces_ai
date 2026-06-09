# Changelog

All notable changes to **`many_faces_ai`** are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) — **version headings only, no dates**. SemVer: [`VERSION`](./VERSION).

### Release index

| Version       | Theme                                 |
| ------------- | ------------------------------------- |
| [0.10.0](#0100) | 7B performance: streaming, helper   |
| [0.9.0](#090) | Capability roadmap AI-UP1…UP20        |
| [0.8.0](#080) | Phase A refactor, proto pin           |
| [0.7.0](#070) | AIH1 gRPC TLS and token               |
| [0.6.0](#060) | Live stats, host profile              |
| [0.5.0](#050) | Ollama adapter, operator chat quality |
| [0.4.0](#040) | Operator stats RPCs, shared proto     |
| [0.3.0](#030) | Content review RPC                    |
| [0.2.0](#020) | DistilGPT-2, verify-ci                |
| [0.1.0](#010) | gRPC HealthService foundation         |

## [Unreleased]

### Added

### Changed

### Fixed

---

## [0.10.0]

### Added

- **7B performance optimizations.** True token streaming: `GenerateStream` now streams from Ollama (`/api/chat` with `stream:true`), yielding each content delta as a `GenerateStreamChunk` and a final `is_final` chunk; a mid-stream failure yields one terminal error chunk and an immediate streaming failure falls back to the previous chunked behaviour (never hard-fails).
- Per-call generation overrides threaded from the proto `GenerateRequest` (new `temperature`, `stop`, `model` fields) into the Ollama options — used by the backend for the terse per-bundle map step (low temperature + stop sequences) and for routing a decision to the CPU-resident helper model (per-call model override, no instance mutation).
- Optional **helper model** support: a `helper` model-routing profile (`OLLAMA_MODEL_HELPER`) and `scripts/pull_helper_model.py`, run best-effort from the entrypoint, that pulls the helper model only if absent (the host Ollama store persists across container rebuilds) and no-ops when unset.
- Extended pytest coverage for keep-alive default/override, per-call temperature/stop/model, true streaming (multi-delta + final, mid-stream error, fallback), and the helper pull script. Full suite **283 passing**.

### Changed

- `OLLAMA_KEEP_ALIVE` defaults to `-1` (model resident on a dedicated PC); the worker also sends `keep_alive=-1` on `/api/chat` and `/api/embeddings` so the model never unloads after idle.

### Fixed

---

## [0.9.0]

### Added

- Capability roadmap v0.9.0 (**AI-UP1…UP20**): LLM moderation path, Phase B `RpcHandlers`,
  `BuildFaceContextSnapshot`, `ChatRiskScore`, `GenerateStream`, `GenerateReport`, `EmbedText`,
  `ExplainDecision`; model routing, Ollama circuit breaker, metrics/trace/usage helpers.
- Proto extensions: `search_hits_json`, `error_code`, moderation eligibility fields; deprecate
  `OperatorStatsChat` in comments.
- Docs: `docs/capability-roadmap-v0.9.0.md` and topic guides (LLM, search, embeddings, mTLS, media).
- Tests: `tests/test_capability_roadmap_up.py`, `tests/test_moderation_sanitize_corpus.py`.
- Monorepo script: `scripts/verify-moderation-corpus-parity.mjs` (AI-UP17).

### Changed

- `server.py` delegates RPCs to `handlers/rpc_handlers.py`; health JSON includes `schemaVersion`.
- `Generate` validates prompt before composing search/stats blocks; English error strings.
- Chat risk scorer flags spam and external links per AI-UP4 policy.

### Fixed

- `ReviewContent` logging uses `title_len`/`body_len` only (AIH1 redaction).
- Dynamic `_ai_service` resolution for tests and runtime monkeypatching.

---

## [0.8.2]

### Added

- Add README shield badges (version, CI, stack tech) via sync-readme-badges.py.

### Added

- Add README shield badges (version, CI, stack tech) via sync-readme-badges.py.

### Changed

### Fixed

---

## [0.8.1]

### Changed

- Document project author (Ladislav Kostolny, 01laky@gmail.com) in README and standard manifests.

### Added

### Changed

- Document project author (Ladislav Kostolny, 01laky@gmail.com) in README and standard manifests.

### Fixed

---

## [0.8.0]

### Changed

- Phase A DRY extract from server.py; pinned many_faces_proto for search RPCs.

### Fixed

- Ruff lint in live stats module.

## [0.7.0]

### Added

- Optional x-ai-worker-token on gRPC; TLS and token smoke script; AIH1 hardening.

## [0.6.0]

### Added

- Live stats planner/stitch helpers; GetHostProfile hardware collector; Windows host profile support.

### Fixed

- Operator chat prompt turn separation; UTC clock in system prompt.

## [0.5.0]

### Added

- Qwen3 defaults; operator dashboard stats in system prompt; response_locale on GenerateRequest.

### Changed

- Replaced in-container Qwen with Ollama adapter.

## [0.4.0]

### Added

- FetchPublicStats and OperatorStatsChat RPCs; nested many_faces_proto submodule.

## [0.3.0]

### Added

- ReviewContent RPC and moderation sanitizer mirroring backend.

## [0.2.0]

### Added

- DistilGPT-2 integration; verify-ci script; gRPC stub generation fixes.

## [0.1.0]

### Added

- Python gRPC HealthService; Docker dev stack; Ruff and pytest health tests.

[Unreleased]: https://github.com/01laky/many_faces_ai/compare/v0.10.0...HEAD
[0.8.2]: https://github.com/01laky/many_faces_ai/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/01laky/many_faces_ai/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/01laky/many_faces_ai/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/01laky/many_faces_ai/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/01laky/many_faces_ai/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/01laky/many_faces_ai/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/01laky/many_faces_ai/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/01laky/many_faces_ai/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/01laky/many_faces_ai/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/01laky/many_faces_ai/releases/tag/v0.1.0
[0.10.0]: https://github.com/01laky/many_faces_ai/compare/v0.9.0...v0.10.0
