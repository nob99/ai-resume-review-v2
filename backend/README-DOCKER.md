# Backend Docker Setup

This document describes how to run the AI Resume Review backend in Docker containers.

## Quick Start

1. **Ensure you have the required environment file:**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

2. **Start all services (databases + backend):**
   ```bash
   # From the project root directory
   docker-compose -f docker-compose.dev.yml up -d
   ```

3. **Check service health:**
   ```bash
   # View all running containers
   docker-compose -f docker-compose.dev.yml ps

   # Check backend health
   curl http://localhost:8000/health

   # View logs
   docker-compose -f docker-compose.dev.yml logs backend
   ```

## Architecture

The Docker setup includes:

- **Backend Service**: FastAPI application with hot-reload enabled
- **PostgreSQL**: Main database (port 5432)
- **Redis**: Cache and rate limiting (port 6379)
- **PgAdmin**: Database management UI (port 8080)

All services are connected via the `ai-resume-review-network`.

## Development Workflow

### Hot Reload
The backend container mounts the source code as a volume, enabling hot-reload:
- Edit files in `backend/app/` locally
- Changes are automatically detected and reloaded
- No need to rebuild the container for code changes

### Viewing Logs
```bash
# Follow backend logs
docker-compose -f docker-compose.dev.yml logs -f backend

# View all service logs
docker-compose -f docker-compose.dev.yml logs -f
```

### Accessing the Services
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **PgAdmin**: http://localhost:8080
  - Email: `dev@airesumereview.com`
  - Password: `dev_pgadmin_123`

### Running Tests
```bash
# Run tests inside the container
docker-compose -f docker-compose.dev.yml exec backend pytest

# Run with coverage
docker-compose -f docker-compose.dev.yml exec backend pytest --cov=app
```

## Container Management

### Stop Services
```bash
# Stop all services
docker-compose -f docker-compose.dev.yml down

# Stop and remove volumes (WARNING: deletes data)
docker-compose -f docker-compose.dev.yml down -v
```

### Rebuild Backend
```bash
# After Dockerfile or dependency changes
docker-compose -f docker-compose.dev.yml build backend

# Force rebuild without cache
docker-compose -f docker-compose.dev.yml build --no-cache backend
```

### Access Container Shell
```bash
# Access backend container
docker-compose -f docker-compose.dev.yml exec backend bash

# Access as root (for troubleshooting)
docker-compose -f docker-compose.dev.yml exec -u root backend bash
```

## Troubleshooting

### Backend Won't Start
1. Check logs: `docker-compose -f docker-compose.dev.yml logs backend`
2. Ensure `.env` file exists with required variables
3. Verify database is healthy: `docker-compose -f docker-compose.dev.yml ps`

### Database Connection Issues
1. Ensure PostgreSQL is running and healthy
2. Check connection settings in docker-compose.yml
3. Verify migrations ran successfully

### Port Conflicts
If ports are already in use:
1. Stop conflicting services, or
2. Change ports in docker-compose.yml

## Production Considerations

This setup is optimized for development. For production:

1. Remove volume mounts for source code
2. Disable hot-reload in the command
3. Use production environment variables
4. Implement proper secrets management
5. Add monitoring and logging aggregation
6. Use managed databases in cloud (GCP Cloud SQL)

## Security Notes

- Never commit `.env` files with real credentials
- The default passwords in docker-compose.yml are for development only
- Use proper secrets management for production
- Backend runs as non-root user (appuser) for security