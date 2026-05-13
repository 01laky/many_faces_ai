# Many Faces AI service - gRPC Server

Python gRPC server providing **health checks**, optional **local Qwen text generation**, and structured **`ReviewContent`** responses for the user-content moderation pipeline used by **many_faces_backend** (`many_faces_backend/`).

## Overview

The Many Faces AI service (**many_faces_ai**; monorepo path `many_faces_ai/`) is a Python-based gRPC server. The backend API (**many_faces_backend** / `many_faces_backend/`) connects on startup for **health verification**, optional **Qwen-backed `Generate`**, and the **`ReviewContent`** contract used by the user-content moderation worker.

In the broader Many Faces AI architecture, this submodule is the AI workspace for application-aware intelligence. **Implemented today:** gRPC `Health`, `Generate` (local Qwen), and `ReviewContent` — a deterministic classifier over text and media URL metadata that returns approve / reject / needs-human-review with confidence, risk, flags, reasons, and optional **`image_analysis_boundary`** / **`video_analysis_boundary`** policy flags (placeholders for heavier CV models; this reference classifier does not treat them as sole auto-reject triggers). The longer-term direction is richer context snapshots, admin reports, and chat-security RPCs.

The goal is for the AI service to understand the application's structure instead of acting as a generic text generator. Future capabilities can use face configuration, page layouts, grid components, roles, content modules, and backend metadata as context for more useful responses. That makes the service a natural place for application-context summaries, admin-facing insights, feature recommendations, and guided diagnostics across the MFAI platform.

This README describes both the current service and the intended direction. The application-context, reporting, feature-management, and chat-security capabilities described below are roadmap items unless explicitly implemented in code.

## Role In MFAI

- **Application context intelligence:** build structured summaries of faces, pages, modules, routes, roles, and configuration so AI features can reason about the real app state.
- **Operational reports:** generate human-readable reports for admins, such as face health, missing configuration, inactive modules, content gaps, usage patterns, or security-relevant anomalies.
- **Feature management support:** help evaluate which features are enabled, incomplete, duplicated, risky, or ready to expose for a specific face or user role.
- **Chat security assistance:** support moderation, abuse detection, unsafe-content review, suspicious-message reporting, and policy-aware chat diagnostics.
- **Admin decision support:** provide explanations and recommendations that help operators understand what is configured, what is missing, and what should be reviewed next.
- **Developer diagnostics:** eventually assist with debugging cross-service behaviour by summarizing backend responses, frontend grid schemas, AI service state, and integration errors.
- **Safety-first AI boundaries:** keep AI outputs advisory by default, with backend-controlled enforcement for permissions, moderation decisions, and sensitive operations.

## Suggested Future Capabilities

The following areas would make the AI submodule more useful as the platform grows:

- **Context snapshots:** a backend-provided payload describing faces, routes, page schemas, available modules, roles, capabilities, and recent operational signals.
- **Report generation RPCs:** typed gRPC methods for generating admin reports instead of overloading free-form text generation.
- **Feature review workflows:** AI-assisted checks for whether a face has complete pages, useful grid composition, required modules, and safe defaults.
- **Chat risk scoring:** structured review of chat messages or conversations for spam, harassment, suspicious links, prompt-injection attempts, or policy violations.
- **Content approval recommendations:** implemented via `ReviewContent` (see below); backend owns enqueue, validation, and final status.
- **Explainable recommendations:** responses that include the reason, confidence, and source context behind each recommendation.
- **Audit-friendly logging:** request metadata and model decisions logged in a way that supports review without leaking sensitive user content unnecessarily.
- **Human approval flow:** AI can suggest moderation or configuration changes, but admin/backend workflows should approve any action that affects users or access rules.

## AI-Assisted Content Approval Role

The content approval workflow uses this service as an **advisory** reviewer for regular FE user-created albums, blogs, and reels. The service **never** publishes or deletes rows in PostgreSQL: it only answers `ReviewContent`. **many_faces_backend** (`many_faces_backend/`) enqueues Redis jobs, calls gRPC, validates ranges and policy, retries with backoff, and only `SUPER_ADMIN` (or future explicit auto-policy) may set final `ApprovalStatus`. Full process guide: [`docs/guides/ai-assisted-content-approval.md`](../docs/guides/ai-assisted-content-approval.md). Agent prompt for untrusted-content defenses (sanitization, heuristics, tests): [`docs/prompts/moderation-content-prompt-injection-defense-agent-prompt.md`](../docs/prompts/moderation-content-prompt-injection-defense-agent-prompt.md).

Target responsibilities:

- Receive bounded review requests from the backend worker (content type, titles, descriptions, media URLs, moderation version).
- Classify using deterministic rules plus URL heuristics; attach **boundary** flags when image/video analysis would require a heavier model later.
- **`ReviewContent` input path:** untrusted title, body, and media URL are normalized in-process via `moderation_input_sanitize.py` (control and bidi stripping, length caps) before keyword classification — mirroring the backend sanitizer for defense in depth.
- Return a structured decision: `approve`, `reject`, or `needs_human_review`.
- Include confidence, risk level, flags, internal reason, safe user-facing message, model version, and trace id.
- Avoid autonomous side effects; all durable state changes stay in the API.
- Support auditability with stable trace metadata; automated tests live in `many_faces_ai/test_server.py`.

Safety rule:

- AI recommends.
- Backend validates the recommendation.
- Admin/superadmin or explicit backend policy finalizes the moderation decision.

This keeps the AI service useful without making it an uncontrolled publisher.

## Features

- **gRPC Server**
  - High-performance RPC communication
  - Protocol Buffers for data serialization
  - Health check endpoint
  - **AI text generation** - `Generate` RPC with local Qwen (no API key)
  - **Content review** - `ReviewContent` RPC for structured moderation recommendations

- **Docker Support**
  - Containerized development environment
  - Automatic proto file generation during build
  - Network integration with other services

- **Health Check RPC**
  - Returns service status and availability
  - Used by backend API for startup health verification

## Technologies

- **Python 3.11** - Programming language
- **gRPC** - High-performance RPC framework
- **Protocol Buffers** - Data serialization
- **grpcio** - Python gRPC library
- **grpcio-tools** - Protocol buffer compiler

## Project Structure

```
many_faces_ai/
├── proto/                  # Protocol buffer definitions
│   ├── health.proto        # Health check service definition
│   ├── health_pb2.py       # Generated Python message classes
│   └── health_pb2_grpc.py  # Generated gRPC service stubs
├── scripts/                # Shell helpers (proto generation, Docker dev, lint, verify-ci)
├── server.py               # gRPC server implementation
├── moderation_input_sanitize.py  # Untrusted-field normalization before ReviewContent
├── test_server.py          # gRPC servicer tests (pytest)
├── test_moderation_input_sanitize.py  # Unit tests for sanitizer
├── services/               # AI model service
│   ├── __init__.py
│   └── ai_model_service.py # Qwen wrapper (generate)
├── requirements.txt        # Python dependencies
├── Dockerfile.dev          # Development Dockerfile
└── README.md               # This file
```

## Running

Local and Docker flows are covered below under **Model Selection** and **Running in Docker Container**.

## Model Selection

The default local LLM is:

- `Qwen/Qwen3-4B-Instruct-2507`

This is a free/open-weight Qwen3 instruct model and a practical default for local development. Larger Qwen variants such as `Qwen/Qwen3-30B-A3B-Instruct-2507` can provide stronger reasoning, but they require significantly more memory and are better served through a dedicated inference runtime such as vLLM.

You can override the model without changing code:

```bash
export MFAI_AI_MODEL_NAME="Qwen/Qwen3-0.6B"
```

Use a smaller Qwen model for low-memory laptops, and a larger Qwen3 model for stronger admin/chat reasoning when hardware allows.

### Running in Docker Container (Recommended)

The easiest way to run the Many Faces AI server in development:

```bash
./scripts/start-dev.sh
```

This script will:

1. Check if proto files exist (if not, they will be generated during Docker build)
2. Build Docker image (if needed)
3. Start the gRPC server container
4. Make the server available at `localhost:50051`

### Using Root Docker Compose

```bash
# From root directory
docker-compose -f docker-compose.dev.yml up -d ai-demo-dev
```

### Stopping Services

```bash
./scripts/stop-dev.sh
```

Or manually:

```bash
docker-compose -f docker-compose.dev.yml stop ai-demo-dev
docker-compose -f docker-compose.dev.yml rm -f ai-demo-dev
```

### Clearing Everything

```bash
./scripts/clear-dev.sh
```

This removes containers and images.

### Rebuilding Docker Images

To perform a clean rebuild of Docker images:

```bash
./scripts/rebuild-dev.sh
```

**Note**: This only builds images, it does NOT start containers. Use `./scripts/start-dev.sh` to start containers after rebuilding.

### Local Development (Without Docker)

1. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Generate gRPC code from proto files**:

   ```bash
   ./scripts/generate_proto.sh
   ```

   This generates:
   - `proto/health_pb2.py` - Protocol buffer message classes
   - `proto/health_pb2_grpc.py` - gRPC service stubs

3. **Run the server**:

   ```bash
   python server.py
   ```

   The server will listen on port 50051 by default (configurable via `PORT` environment variable).

### Local unit tests (pytest)

From `many_faces_ai/`:

```bash
python3 -m venv .venv
.venv/bin/pip install grpcio grpcio-tools protobuf pytest grpcio-testing
.venv/bin/pytest test_server.py -v
```

Pinned versions in `requirements.txt` target **Python 3.11**. On **Python 3.13+**, installing those exact pins may try to build grpcio from source; use the unconstrained `grpcio` / `grpcio-tools` / `grpcio-testing` lines above (or matching wheels) so `pytest` can run. Generated stubs under `proto/` (`health_pb2.py`, `health_pb2_grpc.py`) must exist—run `./scripts/generate_proto.sh` or build via Docker. gRPC tests use the `grpc` marker (see `pytest.ini`).

## gRPC Service

### Health Check

The service provides a `HealthCheck` RPC method:

- **Method**: `HealthCheck`
- **Request**: `HealthCheckRequest` (empty message)
- **Response**: `HealthCheckResponse` with:
  - `status` - Service status (e.g., "success")
  - `message` - Status message (e.g., "Many Faces AI service service is running")

### Generate (AI text generation)

- **Method**: `Generate`
- **Request**: `GenerateRequest` with `prompt` (string), optional `max_new_tokens` (int32)
- **Response**: `GenerateResponse` with `text` (generated text), optional `error` (if failed)
- Uses local **DistilGPT-2** model (Hugging Face); no API key. See **AI_INTEGRATION.md** for details.

- **Port**: 50051 (default, configurable via `PORT` environment variable)

### Protocol Buffer Definition

```protobuf
syntax = "proto3";

service HealthService {
  rpc HealthCheck(HealthCheckRequest) returns (HealthCheckResponse);
}

message HealthCheckRequest {}

message HealthCheckResponse {
  string status = 1;
  string message = 2;
}
```

## Configuration

### Environment Variables

- `PORT` - gRPC server port (default: `50051`)

Configured in `docker-compose.dev.yml`:

```yaml
environment:
  - PORT=50051
```

### Network Configuration

The service runs on the `many_faces_main_dev-network` Docker network, allowing other services (like the backend API) to connect using the service name `ai-demo-dev` or container name.

## Development

### Generating gRPC Code

Proto files are automatically generated during Docker image build. To regenerate manually:

**In Docker** (during build):

```bash
python -m grpc_tools.protoc -I./proto --python_out=./proto --grpc_python_out=./proto ./proto/health.proto
```

**Locally**:

```bash
./scripts/generate_proto.sh
```

This generates:

- `proto/health_pb2.py` - Protocol buffer message classes
- `proto/health_pb2_grpc.py` - gRPC service stubs

### Adding New RPC Methods

1. **Update `proto/health.proto`**:

   ```protobuf
   service HealthService {
     rpc HealthCheck(HealthCheckRequest) returns (HealthCheckResponse);
     rpc NewMethod(NewMethodRequest) returns (NewMethodResponse);  // Add new method
   }
   ```

2. **Regenerate proto files**: `./scripts/generate_proto.sh`

3. **Implement method in `server.py`**:

   ```python
   def NewMethod(self, request, context):
       return health_pb2.NewMethodResponse(status="ok")
   ```

4. **Rebuild Docker image**: `./scripts/rebuild-dev.sh`

## Testing

### Manual Testing

Use a gRPC client tool (e.g., `grpcurl`) to test the service:

```bash
# List services
grpcurl -plaintext localhost:50051 list

# Call HealthCheck
grpcurl -plaintext -d '{}' localhost:50051 HealthService/HealthCheck
```

### From Backend API

The backend API (**many_faces_backend** / `many_faces_backend/`) calls the health check on startup. Check backend logs to verify the connection:

```bash
docker logs be-demo-dev | grep -i "ai service"
```

## Development Workflow

1. **Start database**: Ensure PostgreSQL is running (via `many_faces_database` or monorepo `./scripts/start-all-dev.sh`)

2. **Start Many Faces AI service**: Run `./scripts/start-dev.sh` or use monorepo `./scripts/start-all-dev.sh` to start all services

3. **Make code changes**: Edit `server.py` or `proto/health.proto`

4. **Test changes**:
   - Check service is responding: `docker logs ai-demo-dev`
   - Verify backend can connect (check backend logs)

5. **Rebuild if needed**: `./scripts/rebuild-dev.sh` (if proto files changed)

6. **Stop services**: Run `./scripts/stop-dev.sh` or monorepo `./scripts/stop-all-dev.sh`

## Integration with Root Project

This Many Faces AI service is part of the **`many_faces_main`** monorepo (`many_faces_ai/` submodule on GitHub: `many_faces_ai`) and integrates with:

- **Backend API**: **many_faces_backend** (`many_faces_backend/`, ASP.NET Core) — connects on startup for health check

From the **many_faces_main** repository root, use the orchestration scripts to manage all services:

- `./scripts/start-all-dev.sh` - Start all services with live status screen
- `./scripts/stop-all-dev.sh` - Stop all services
- `./scripts/clear-all-dev.sh` - Clear all containers and volumes
- `./scripts/status-all.sh` - Show status of all services
- `./scripts/rebuild-all-dev.sh` - Rebuild all Docker images

## Troubleshooting

### Port Already Allocated

If port 50051 is already in use:

```bash
# Find process using port
lsof -ti:50051

# Kill process
lsof -ti:50051 | xargs kill -9

# Or use clear script
./scripts/clear-dev.sh
```

### Proto Files Not Generated

If you see `ModuleNotFoundError` for proto files:

- Proto files are generated during Docker build
- Check `Dockerfile.dev` for proto generation steps
- If needed, manually run `./scripts/generate_proto.sh` before starting container

### Backend Cannot Connect

- Ensure Many Faces AI service container is running: `docker ps | grep ai-demo-dev`
- Check network: Both services should be on `many_faces_main_dev-network`
- Verify port: Default is 50051
- Check backend logs: `docker logs be-demo-dev | grep -i ai`

### Service Not Responding

- Check container logs: `docker logs ai-demo-dev`
- Verify container is running: `docker ps | grep ai-demo-dev`
- Check health: `docker inspect ai-demo-dev --format '{{.State.Status}}'`

## Additional Notes

- **Proto Generation**: Proto files are generated during Docker build, not locally
- **Network Access**: Service is accessible from other containers on the same Docker network
- **Production**: For production, consider adding authentication, TLS, and more comprehensive health checks

## Monorepo documentation

This repository is a **git submodule** of [`many_faces_main`](https://github.com/01laky/many_faces_main). Central guides and the documentation hub:

- [docs/README.md](https://github.com/01laky/many_faces_main/blob/main/docs/README.md)  
- [docs/guides/ai-assisted-content-approval.md](https://github.com/01laky/many_faces_main/blob/main/docs/guides/ai-assisted-content-approval.md) — end-to-end moderation pipeline  
- [docs/guides/development.md](https://github.com/01laky/many_faces_main/blob/main/docs/guides/development.md) — `scripts/lint-all.sh`, CI expectations  
- [docs/guides/git-submodules.md](https://github.com/01laky/many_faces_main/blob/main/docs/guides/git-submodules.md) — submodule workflow  
