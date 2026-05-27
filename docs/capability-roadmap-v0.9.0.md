# AI worker capability roadmap v0.9.0

Release **0.9.0** implements the Python worker slice of **AI-UP1…UP20** (backend/client wiring for UP4, UP10, UP19 remains follow-up).

## Index

| Topic | Doc |
| ----- | --- |
| LLM moderation | [moderation-llm-phase3.md](./moderation-llm-phase3.md) |
| Search hits in Generate | [search-integration.md](./search-integration.md) |
| Embeddings RPC | [embeddings.md](./embeddings.md) |
| mTLS (deferred spike) | [mtls.md](./mtls.md) |
| Media URL pass | [moderation-media-pass.md](./moderation-media-pass.md) |
| Availability contract | [../../docs/guides/ai-availability-contract.md](../../docs/guides/ai-availability-contract.md) |

## New RPCs

- `GenerateStream`, `BuildFaceContextSnapshot`, `ChatRiskScore`, `GenerateReport`, `EmbedText`, `ExplainDecision`

## Tests

- `tests/test_capability_roadmap_up.py` — AI-UP1…UP20 edge cases
- `tests/test_moderation_sanitize_corpus.py` — shared corpus (AI-UP17)
- Monorepo: `node scripts/verify-moderation-corpus-parity.mjs`

