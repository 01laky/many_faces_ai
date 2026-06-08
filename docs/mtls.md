# mTLS (AI-UP12)

**Status in v0.9.0:** documentation + existing AIH1 TLS hooks only. Full mutual TLS remains **`TRACK-AIH1-MTLS`**.

## Current (token + optional server TLS)

| Env                                        | Purpose                                                   |
| ------------------------------------------ | --------------------------------------------------------- |
| `GRPC_TLS_CERT_FILE` / `GRPC_TLS_KEY_FILE` | Server TLS credentials                                    |
| `AI_WORKER_EXPECTED_TOKEN`                 | Metadata **`x-ai-worker-token`**                          |
| `MFAI_HARDENED_PROFILE`                    | Require token; HTTPS-only outbound except loopback policy |
| `MFAI_ALLOW_INSECURE_GRPC`                 | Dev-only plaintext gRPC                                   |

## Planned mTLS spike

1. Client cert CA bundle on backend **`AiGrpcService`** channel.
2. Worker requires client cert when **`MFAI_REQUIRE_CLIENT_CERT=1`**.
3. Extend **`scripts/smoke-grpc-tls.sh`** with mTLS path.

Dev compose continues token-only until explicitly enabled.
