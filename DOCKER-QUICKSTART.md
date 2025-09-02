# Docker Quick Start Guide

## 🚀 One-Command Start

```bash
# Start all services (frontend, backend, database, redis)
./scripts/docker-dev.sh up
```

This will start:
- ✅ Frontend (Next.js) - http://localhost:3000
- ✅ Backend (FastAPI) - http://localhost:8000
- ✅ PostgreSQL Database - localhost:5432
- ✅ Redis Cache - localhost:6379
- ✅ PgAdmin - http://localhost:8080

## 📋 Prerequisites

- Docker Desktop installed and running
- Docker Compose v3.8+
- Ports 3000, 8000, 5432, 6379, 8080 available

## 🎯 Common Tasks

### View Logs
```bash
# All services
./scripts/docker-dev.sh logs

# Specific service
./scripts/docker-dev.sh logs frontend
./scripts/docker-dev.sh logs backend
```

### Access Container Shell
```bash
# Frontend shell
./scripts/docker-dev.sh shell frontend

# Backend shell
./scripts/docker-dev.sh shell backend

# PostgreSQL client
./scripts/docker-dev.sh shell postgres

# Redis CLI
./scripts/docker-dev.sh shell redis
```

### Stop Services
```bash
# Stop all services
./scripts/docker-dev.sh down

# Stop specific service
./scripts/docker-frontend.sh stop
```

### Rebuild After Changes
```bash
# Rebuild all services
./scripts/docker-dev.sh build

# Rebuild specific service
./scripts/docker-frontend.sh build
```

## 🔧 Service-Specific Commands

### Frontend Only
```bash
# Start frontend
./scripts/docker-frontend.sh start

# Run tests
./scripts/docker-frontend.sh test

# Run linter
./scripts/docker-frontend.sh lint

# View logs
./scripts/docker-frontend.sh logs
```

### Backend Already Containerized
Backend was containerized in Sprint 002. See `backend/README-DOCKER.md` for details.

## 🌐 Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | - |
| Backend API | http://localhost:8000 | - |
| API Docs | http://localhost:8000/docs | - |
| PgAdmin | http://localhost:8080 | dev@airesumereview.com / dev_pgadmin_123 |

## 🛠️ Troubleshooting

### Port Already in Use
```bash
# Check what's using port 3000
lsof -i :3000

# Kill process using port
kill -9 <PID>
```

### Container Won't Start
```bash
# Check container status
./scripts/docker-dev.sh status

# View detailed logs
docker-compose -f docker-compose.dev.yml logs --tail=100 <service>

# Clean rebuild
./scripts/docker-dev.sh clean
./scripts/docker-dev.sh build
./scripts/docker-dev.sh up
```

### Frontend Can't Connect to Backend
- Check both services are running: `./scripts/docker-dev.sh status`
- Frontend uses `http://backend:8000` internally (Docker network)
- Browser uses `http://localhost:8000` externally

## 📁 Project Structure

```
ai-resume-review-v2/
├── docker-compose.dev.yml    # Development orchestration
├── scripts/
│   ├── docker-dev.sh        # All services management
│   └── docker-frontend.sh   # Frontend-specific commands
├── frontend/
│   ├── Dockerfile           # Production build
│   ├── Dockerfile.dev       # Development build
│   └── .dockerignore       # Build exclusions
└── backend/
    ├── Dockerfile          # Production build
    └── .dockerignore       # Build exclusions
```

## 🔄 Hot Reload

Both frontend and backend support hot reload in development:
- Frontend: Edit files in `frontend/src/` - changes appear immediately
- Backend: Edit files in `backend/app/` - server restarts automatically

## 🧹 Cleanup

```bash
# Stop and remove all containers and volumes
./scripts/docker-dev.sh clean

# Remove specific service data
docker volume rm ai-resume-review-postgres-data
docker volume rm ai-resume-review-redis-data
```

## 📚 More Information

- Frontend Docker details: `frontend/DOCKER-README.md`
- Backend Docker details: `backend/README-DOCKER.md`
- Architecture overview: `docs/design/architecture.md`