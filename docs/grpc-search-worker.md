# gRPC search-worker (shared contract with many_faces_elastic)

The Python **many_faces_ai** service does **not** call Elasticsearch HTTP for shipping search paths. When AI features need query or index access to the search projection, they should use the same **gRPC** contract as **many_faces_backend**, implemented by the Go **search-worker** colocated with Elasticsearch in the **`many_faces_elastic`** submodule.

## Canonical proto

Source of truth (versioned RPCs):

```text
many_faces_elastic/proto/manyfaces/search/v1/search.proto
```

Today this defines `SearchService.Ping` for reachability checks. Future RPCs (`Search`, `IndexDocument`, …) will be added here first, then:

1. Regenerate **Go** stubs under `many_faces_elastic/gen/…` for the worker.
2. Regenerate **C#** stubs via `Grpc.Tools` in `many_faces_backend` (already wired to the shared proto path).
3. Regenerate **Python** stubs with `grpcio-tools` (same pattern as **`many_faces_proto/proto/health.proto`** and `scripts/generate_proto.sh` in this repo — add a second `.proto` include path or symlink policy and document it next to the shell script).

## Authentication

The worker may require the `x-search-worker-token` metadata header when `SEARCH_WORKER_EXPECTED_TOKEN` is set. **many_faces_ai** must send its own service identity secret (distinct from end-user JWTs) when calling the worker — align with `many_faces_elastic` README and monorepo security docs.

## Transport (TLS / mTLS)

When the worker is started with `SEARCH_WORKER_GRPC_TLS_CERT_FILE` and `SEARCH_WORKER_GRPC_TLS_KEY_FILE`, use **TLS** from the Python client (channel credentials over `https://` or equivalent). For **mTLS**, also supply a client certificate trusted by the CA in `SEARCH_WORKER_GRPC_MTLS_CLIENT_CA_FILE`. Operator reference: monorepo [`docs/guides/elasticsearch-grpc-tls-mtls.md`](../../docs/guides/elasticsearch-grpc-tls-mtls.md).

## Non-goals

- Duplicating business rules or face ACL inside the worker (authorization stays in **many_faces_backend** for user-driven flows).
- Opening Elasticsearch HTTP from this Python process for production traffic without an explicit, documented exception.
