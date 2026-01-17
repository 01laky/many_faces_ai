# AI Demo - gRPC Server

Python gRPC server providing health check functionality for the AI Demo service.

## Overview

The AI Demo (ai_demo) is a Python-based gRPC server that provides health check functionality for AI services. The backend API (be_demo) connects to this service on startup to verify that AI services are available and operational.

## Features

- **gRPC Server**
  - High-performance RPC communication
  - Protocol Buffers for data serialization
  - Health check endpoint

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

## gRPC Service

### Health Check

The service provides a `HealthCheck` RPC method:

- **Method**: `HealthCheck`
- **Request**: `HealthCheckRequest` (empty message)
- **Response**: `HealthCheckResponse` with:
  - `status` - Service status (e.g., "success")
  - `message` - Status message (e.g., "AI Demo service is running")
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

1. **Start database**: Ensure PostgreSQL is running (via `db_demo` or root `start-all-dev.sh`)

2. **Start AI Demo**: Run `./start-dev.sh` or use root `start-all-dev.sh` to start all services

3. **Make code changes**: Edit `server.py` or `proto/health.proto`

4. **Test changes**: 
   - Check service is responding: `docker logs ai-demo-dev`
   - Verify backend can connect (check backend logs)

5. **Rebuild if needed**: `./rebuild-dev.sh` (if proto files changed)

6. **Stop services**: Run `./stop-dev.sh` or root `stop-all-dev.sh`

## Integration with Root Project

This AI Demo is part of the `_mfai_demo` monorepo and integrates with:

- **Backend API**: `be_demo` (ASP.NET Core) - connects on startup for health check

Use root-level scripts to manage all services:
- `start-all-dev.sh` - Start all services with live status screen
- `stop-all-dev.sh` - Stop all services
- `clear-all-dev.sh` - Clear all containers and volumes
- `status-all.sh` - Show status of all services
- `rebuild-all-dev.sh` - Rebuild all Docker images

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
