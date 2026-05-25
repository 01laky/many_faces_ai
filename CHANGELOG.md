# Changelog

All notable changes to **`many_faces_ai`** are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) — **version headings only, no dates**. SemVer: [`VERSION`](./VERSION).

### Release index

| Version       | Theme                                 |
| ------------- | ------------------------------------- |
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

[Unreleased]: https://github.com/01laky/many_faces_ai/compare/v0.8.1...HEAD
[0.8.1]: https://github.com/01laky/many_faces_ai/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/01laky/many_faces_ai/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/01laky/many_faces_ai/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/01laky/many_faces_ai/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/01laky/many_faces_ai/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/01laky/many_faces_ai/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/01laky/many_faces_ai/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/01laky/many_faces_ai/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/01laky/many_faces_ai/releases/tag/v0.1.0
