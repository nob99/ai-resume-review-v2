# Frontend Docker Documentation

## Overview

The frontend is containerized using Docker with both development and production configurations. The setup follows the same patterns as the backend for consistency.

## Quick Start

### Using Helper Scripts

```bash
# Start all services (frontend, backend, database, redis)
./scripts/docker-dev.sh up

# Start only frontend
./scripts/docker-frontend.sh start

# View frontend logs
./scripts/docker-frontend.sh logs

# Stop all services
./scripts/docker-dev.sh down
```

### Using Docker Compose Directly

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Start only frontend with dependencies
docker-compose -f docker-compose.dev.yml up -d frontend

# View logs
docker-compose -f docker-compose.dev.yml logs -f frontend

# Stop services
docker-compose -f docker-compose.dev.yml down
```

## Architecture

### Container Structure

- **Base Image**: Node.js 20 Alpine (lightweight)
- **Port**: 3000
- **User**: Non-root user (nextjs:1001)
- **Network**: Shared `ai-resume-review-network` with backend

### Development Setup

The development setup uses `Dockerfile.dev` with:
- Hot reload enabled via volume mounts
- Source code mounted as read-only
- Node modules installed in container
- Environment variables for API connection

### Production Setup

The production setup uses multi-stage `Dockerfile` with:
- Dependency installation stage
- Build stage with Next.js standalone output
- Minimal runtime stage with only necessary files
- Health checks and proper signal handling

## Environment Variables

### Required Variables

- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000)
- `NODE_ENV`: Environment (development/production)
- `PORT`: Server port (default: 3000)

### Docker Network Communication

**Important**: Frontend API calls are made from the browser (client-side), not server-side, so they must use external URLs:

- **Browser requests**: `http://localhost:8000` (external Docker port)
- **Internal Docker communication**: `http://backend:8000` (only for server-to-server)

The `NEXT_PUBLIC_API_URL` environment variable is used by the browser and must use `localhost:8000`.

## File Structure

```
frontend/
├── Dockerfile              # Production multi-stage build
├── Dockerfile.dev          # Development build with hot reload
├── .dockerignore          # Exclude unnecessary files
├── .env.example           # Environment variable template
└── src/
    └── app/
        └── api/
            └── health/    # Health check endpoint
```

## Health Checks

The frontend includes health checks at `/api/health` that return:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-02T10:00:00.000Z",
  "service": "frontend",
  "version": "0.1.0"
}
```

## Volume Mounts (Development)

- `./frontend/src:/app/src:ro` - Source code (read-only)
- `./frontend/public:/app/public:ro` - Static assets
- `./frontend/.next:/app/.next` - Build output (writable for hot reload)

## Common Commands

### Development

```bash
# Build frontend image
./scripts/docker-frontend.sh build

# Run tests in container
./scripts/docker-frontend.sh test

# Run linter
./scripts/docker-frontend.sh lint

# Open shell in container
./scripts/docker-frontend.sh shell
```

### Troubleshooting

```bash
# Check container status
docker-compose -f docker-compose.dev.yml ps

# View detailed logs
docker-compose -f docker-compose.dev.yml logs --tail=100 frontend

# Inspect container
docker inspect ai-resume-review-frontend-dev

# Clean rebuild
./scripts/docker-frontend.sh clean
./scripts/docker-frontend.sh build
./scripts/docker-frontend.sh start
```

## Performance Optimization

1. **Multi-stage builds** reduce final image size
2. **Layer caching** speeds up rebuilds
3. **Alpine Linux** base for minimal footprint
4. **Standalone output** includes only necessary files
5. **.dockerignore** prevents copying unnecessary files

## Security Best Practices

1. **Non-root user** (nextjs:1001) runs the application
2. **Read-only mounts** for source code in development
3. **No secrets** in Docker images
4. **Health checks** for container monitoring
5. **Minimal base image** reduces attack surface

## Integration with Backend

The frontend automatically connects to the backend through Docker's internal network:

- Frontend URL: `http://localhost:3000`
- Backend API: `http://backend:8000` (internal)
- Database: Accessed only by backend
- Redis: Accessed only by backend

## Next Steps

1. Test the containerized setup:
   ```bash
   ./scripts/docker-dev.sh up
   ```

2. Verify health check:
   ```bash
   curl http://localhost:3000/api/health
   ```

3. Check hot reload by editing a file in `src/`

4. Access the application at http://localhost:3000