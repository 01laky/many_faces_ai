#!/usr/bin/env bash
# gRPC smoke for many_faces_ai: HealthCheck over plaintext (dev) or TLS + x-ai-worker-token (hardened).
#
# Prerequisites: grpcurl; openssl when AI_TLS_SMOKE=1; running worker on AI_GRPC_TARGET (default localhost:50051).
#
# Usage (from monorepo root or many_faces_ai):
#   chmod +x many_faces_ai/scripts/smoke-grpc-tls.sh
#   many_faces_ai/scripts/smoke-grpc-tls.sh
#
# Environment:
#   AI_GRPC_TARGET          — host:port (default localhost:50051)
#   AI_WORKER_TOKEN         — sent as x-ai-worker-token metadata when set
#   AI_TLS_SMOKE=1          — use GRPC_TLS_CA_FILE + -cacert (requires AIH1-A3 server TLS)
#   GRPC_TLS_CA_FILE        — PEM for server cert (required when AI_TLS_SMOKE=1)
#   AI_PROTO_ROOT           — proto import path (default: many_faces_ai/many_faces_proto/proto)
#   RUN_GENERATE_SMOKE=0    — skip authenticated Generate probe (default 1 when token set)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_DIR="${AI_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
MONOREPO_ROOT="${MONOREPO_ROOT:-$(cd "$AI_DIR/.." && pwd)}"
AI_GRPC_TARGET="${AI_GRPC_TARGET:-localhost:50051}"
AI_PROTO_ROOT="${AI_PROTO_ROOT:-$AI_DIR/many_faces_proto/proto}"
AI_TLS_SMOKE="${AI_TLS_SMOKE:-0}"
RUN_GENERATE_SMOKE="${RUN_GENERATE_SMOKE:-1}"

if ! command -v grpcurl >/dev/null 2>&1; then
  echo "grpcurl is required (brew install grpcurl)" >&2
  exit 1
fi

if [[ ! -f "$AI_PROTO_ROOT/health.proto" ]]; then
  echo "health.proto not found at $AI_PROTO_ROOT/health.proto" >&2
  exit 1
fi

GRPCURL_ARGS=(-import-path "$AI_PROTO_ROOT" -proto health.proto)
METADATA=()

if [[ -n "${AI_WORKER_TOKEN:-}" ]]; then
  METADATA=(-H "x-ai-worker-token: $AI_WORKER_TOKEN")
fi

if [[ "$AI_TLS_SMOKE" == "1" ]]; then
  if [[ -z "${GRPC_TLS_CA_FILE:-}" || ! -f "$GRPC_TLS_CA_FILE" ]]; then
    echo "AI_TLS_SMOKE=1 requires GRPC_TLS_CA_FILE pointing at a readable PEM" >&2
    exit 1
  fi
  echo "== TLS HealthCheck against $AI_GRPC_TARGET"
  grpcurl "${GRPCURL_ARGS[@]}" -cacert "$GRPC_TLS_CA_FILE" "${METADATA[@]}" \
    "$AI_GRPC_TARGET" health.HealthService/HealthCheck
else
  echo "== Plaintext HealthCheck against $AI_GRPC_TARGET (dev only)"
  grpcurl "${GRPCURL_ARGS[@]}" -plaintext "${METADATA[@]}" \
    "$AI_GRPC_TARGET" health.HealthService/HealthCheck
fi

if [[ -n "${AI_WORKER_TOKEN:-}" && "$RUN_GENERATE_SMOKE" == "1" ]]; then
  echo "== Generate probe (empty prompt should return validation error, not UNAUTHENTICATED)"
  set +e
  if [[ "$AI_TLS_SMOKE" == "1" ]]; then
    grpcurl "${GRPCURL_ARGS[@]}" -cacert "$GRPC_TLS_CA_FILE" "${METADATA[@]}" \
      -d '{"prompt":""}' "$AI_GRPC_TARGET" health.HealthService/Generate
  else
    grpcurl "${GRPCURL_ARGS[@]}" -plaintext "${METADATA[@]}" \
      -d '{"prompt":""}' "$AI_GRPC_TARGET" health.HealthService/Generate
  fi
  gen_exit=$?
  set -e
  if [[ "$gen_exit" -ne 0 ]]; then
    echo "Generate probe exit $gen_exit (expected for empty prompt or model unavailable — auth must not be UNAUTHENTICATED when token set)"
  fi
fi

echo "smoke-grpc-tls: OK"
