# AI Demo - gRPC Server

Python gRPC server providing health check functionality for the AI Demo service.

## Features

- gRPC server with health check endpoint
- Docker support for development
- Health check RPC method that returns service status

## Technologies

- Python 3.11
- gRPC
- Protocol Buffers

## Running

### Running in Docker container (recommended for development)

```bash
./start-dev.sh
```

Or manually:

```bash
docker-compose -f ../docker-compose.dev.yml up -d ai-demo-dev
```

### Local run (without Docker)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Generate gRPC code from proto files:
   ```bash
   ./generate_proto.sh
   ```

3. Run the server:
   ```bash
   python server.py
   ```

The server will listen on port 50051 by default (configurable via PORT environment variable).

## gRPC Service

### Health Check

- **Method**: `HealthCheck`
- **Request**: `HealthCheckRequest` (empty)
- **Response**: `HealthCheckResponse` with status and message
- **Port**: 50051 (default)

## Development

### Generating gRPC Code

To regenerate Python code from `.proto` files:

```bash
./generate_proto.sh
```

This generates:
- `proto/health_pb2.py` - Protocol buffer message classes
- `proto/health_pb2_grpc.py` - gRPC service stubs
