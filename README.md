# AI Demo - gRPC Server

Python gRPC server providing health check functionality for the AI Demo service.

## Overview

The AI Demo (ai_demo) is a Python-based gRPC server that provides health check functionality for AI services. The backend API (be_demo) connects to this service on startup to verify that AI services are available and operational.

In the broader Many Faces AI architecture, this submodule is intended to become the AI workspace for application-aware intelligence. Today it provides the gRPC service foundation, health checks, and local text generation experiments; the longer-term direction is to connect AI features to the product context, operational reports, feature management, and safety-sensitive chat workflows.

The goal is for the AI service to understand the application's structure instead of acting as a generic text generator. Future capabilities can use face configuration, page layouts, grid components, roles, content modules, and backend metadata as context for more useful responses. That makes the service a natural place for application-context summaries, admin-facing insights, feature recommendations, and guided diagnostics across the MFAI platform.

This README describes both the current service and the intended direction. The application-context, reporting, feature-management, and chat-security capabilities described below are roadmap items unless explicitly implemented in code.

## Planned Role In MFAI

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
- **Explainable recommendations:** responses that include the reason, confidence, and source context behind each recommendation.
- **Audit-friendly logging:** request metadata and model decisions logged in a way that supports review without leaking sensitive user content unnecessarily.
- **Human approval flow:** AI can suggest moderation or configuration changes, but admin/backend workflows should approve any action that affects users or access rules.

## Features

- **gRPC Server**
  - High-performance RPC communication
  - Protocol Buffers for data serialization
  - Health check endpoint
  - **AI text generation** — `Generate` RPC with local DistilGPT-2 (no API key)

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
ai_demo/
├── proto/                  # Protocol buffer definitions
│   ├── health.proto        # Health check service definition
│   ├── health_pb2.py       # Generated Python message classes
│   └── health_pb2_grpc.py  # Generated gRPC service stubs
├── server.py               # gRPC server implementation
├── services/               # AI model service
│   ├── __init__.py
│   └── ai_model_service.py # DistilGPT-2 wrapper (generate)
├── generate_proto.sh       # Script to generate Python code from proto files
├── requirements.txt        # Python dependencies
├── Dockerfile.dev          # Development Dockerfile
├── start-dev.sh            # Start development script
├── stop-dev.sh             # Stop development script
├── clear-dev.sh            # Clear containers script
├── rebuild-dev.sh          # Rebuild Docker images script
└── README.md               # This file
```

## Running

### Running in Docker Container (Recommended)

The easiest way to run the AI Demo server in development:

```bash
./start-dev.sh
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
./stop-dev.sh
```

Or manually:

```bash
docker-compose -f docker-compose.dev.yml stop ai-demo-dev
docker-compose -f docker-compose.dev.yml rm -f ai-demo-dev
```

### Clearing Everything

```bash
./clear-dev.sh
```

This removes containers and images.

### Rebuilding Docker Images

To perform a clean rebuild of Docker images:

```bash
./rebuild-dev.sh
```

**Note**: This only builds images, it does NOT start containers. Use `./start-dev.sh` to start containers after rebuilding.

### Local Development (Without Docker)

1. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Generate gRPC code from proto files**:

   ```bash
   ./generate_proto.sh
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

From `ai_demo/`:

```bash
python3 -m venv .venv
.venv/bin/pip install grpcio grpcio-tools protobuf pytest grpcio-testing
.venv/bin/pytest test_server.py -v
```

Pinned versions in `requirements.txt` target **Python 3.11**. On **Python 3.13+**, installing those exact pins may try to build grpcio from source; use the unconstrained `grpcio` / `grpcio-tools` / `grpcio-testing` lines above (or matching wheels) so `pytest` can run. Generated stubs under `proto/` (`health_pb2.py`, `health_pb2_grpc.py`) must exist—run `./generate_proto.sh` or build via Docker. gRPC tests use the `grpc` marker (see `pytest.ini`).

## gRPC Service

### Health Check

The service provides a `HealthCheck` RPC method:

- **Method**: `HealthCheck`
- **Request**: `HealthCheckRequest` (empty message)
- **Response**: `HealthCheckResponse` with:
  - `status` - Service status (e.g., "success")
  - `message` - Status message (e.g., "AI Demo service is running")

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

The service runs on the `mfai_demo_dev-network` Docker network, allowing other services (like the backend API) to connect using the service name `ai-demo-dev` or container name.

## Development

### Generating gRPC Code

Proto files are automatically generated during Docker image build. To regenerate manually:

**In Docker** (during build):

```bash
python -m grpc_tools.protoc -I./proto --python_out=./proto --grpc_python_out=./proto ./proto/health.proto
```

**Locally**:

```bash
./generate_proto.sh
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

2. **Regenerate proto files**: `./generate_proto.sh`

3. **Implement method in `server.py`**:

   ```python
   def NewMethod(self, request, context):
       return health_pb2.NewMethodResponse(status="ok")
   ```

4. **Rebuild Docker image**: `./rebuild-dev.sh`

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

The backend API (be_demo) calls the health check on startup. Check backend logs to verify the connection:

```bash
docker logs be-demo-dev | grep -i "ai service"
```

## Development Workflow

1. **Start database**: Ensure PostgreSQL is running (via `db_demo` or monorepo `./scripts/start-all-dev.sh`)

2. **Start AI Demo**: Run `./start-dev.sh` or use monorepo `./scripts/start-all-dev.sh` to start all services

3. **Make code changes**: Edit `server.py` or `proto/health.proto`

4. **Test changes**:
   - Check service is responding: `docker logs ai-demo-dev`
   - Verify backend can connect (check backend logs)

5. **Rebuild if needed**: `./rebuild-dev.sh` (if proto files changed)

6. **Stop services**: Run `./stop-dev.sh` or monorepo `./scripts/stop-all-dev.sh`

## Integration with Root Project

This AI Demo is part of the `_mfai_demo` monorepo and integrates with:

- **Backend API**: `be_demo` (ASP.NET Core) - connects on startup for health check

Use root-level scripts to manage all services:

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
./clear-dev.sh
```

### Proto Files Not Generated

If you see `ModuleNotFoundError` for proto files:

- Proto files are generated during Docker build
- Check `Dockerfile.dev` for proto generation steps
- If needed, manually run `./generate_proto.sh` before starting container

### Backend Cannot Connect

- Ensure AI Demo container is running: `docker ps | grep ai-demo-dev`
- Check network: Both services should be on `mfai_demo_dev-network`
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
