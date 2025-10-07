"""
FastAPI main application for AI Resume Review Platform.
Implements secure authentication with rate limiting and comprehensive security features.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from database.connection import init_database, close_database, get_db_health
from app.core.rate_limiter import rate_limiter
from app.core.security import SecurityError
from app.core.config import get_settings

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting AI Resume Review Platform Backend")
    
    try:
        # Initialize database
        init_database()
        logger.info("Database initialized")

        # Initialize rate limiter (optional - graceful degradation)
        try:
            await rate_limiter.connect()
            if rate_limiter.redis_client:
                logger.info("✓ Rate limiter initialized with Redis")
            else:
                logger.warning("⚠ Rate limiter running without Redis (rate limiting disabled)")
        except Exception as e:
            logger.warning(f"⚠ Rate limiter initialization failed: {e}")
            logger.warning("  Continuing without rate limiting (acceptable for MVP)")

        # Initialize async infrastructure
        from app.core.database import init_postgres
        await init_postgres()
        logger.info("PostgreSQL async connection initialized")
        
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Resume Review Platform Backend")

    try:
        # Close rate limiter (if connected)
        try:
            await rate_limiter.disconnect()
            logger.info("Rate limiter disconnected")
        except Exception as e:
            logger.warning(f"Error disconnecting rate limiter: {e}")

        # Close database
        close_database()
        logger.info("Database connections closed")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    logger.info("Application shutdown completed")


# Create FastAPI application
app = FastAPI(
    title="AI Resume Review Platform API",
    description="""
    Secure authentication and user management API for the AI Resume Review Platform.
    
    ## Features
    
    * **Secure Authentication**: JWT-based authentication with bcrypt password hashing
    * **Rate Limiting**: DDoS protection with Redis-based distributed rate limiting  
    * **Password Security**: Comprehensive password validation and strength checking
    * **User Management**: Role-based access control (consultant/admin)
    * **Account Security**: Account lockout protection and admin management
    * **API Documentation**: Complete OpenAPI 3.0 specification
    
    ## Security
    
    * All passwords are hashed using bcrypt with 12 rounds
    * JWT tokens with configurable expiration
    * Rate limiting on all authentication endpoints
    * Account lockout after 5 failed login attempts
    * Admin-only password reset functionality
    * Comprehensive input validation and sanitization
    
    ## Getting Started
    
    1. Register a new user account via `/auth/register`
    2. Login to receive a JWT access token via `/auth/login`
    3. Include the token in the Authorization header: `Bearer <token>`
    4. Access protected endpoints with your authenticated requests
    
    ## Rate Limits
    
    * Login: 5 attempts per 15 minutes
    * Registration: 3 attempts per hour
    * Password Reset: 3 attempts per hour  
    * General API: 100 requests per hour
    """,
    version="1.0.0",
    contact={
        "name": "AI Resume Review Team",
        "email": "dev@airesumereview.com",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:8000",  # Local development
        "https://ai-resume-review-v2-frontend-prod-864523342928.us-central1.run.app",  # Cloud Run frontend
        "https://ai-resume-review-v2-backend-prod-wnjxxf534a-uc.a.run.app",  # Cloud Run backend
        "https://airesumereview.com",  # Future production domain
        "https://www.airesumereview.com",  # Future production www domain
        "https://api.airesumereview.com",  # Future production API domain
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Proxy headers middleware for Cloud Run
class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle X-Forwarded-* headers from Cloud Run reverse proxy.
    This ensures FastAPI generates HTTPS URLs in redirects instead of HTTP.

    Cloud Run terminates TLS and forwards requests to containers over HTTP,
    but includes X-Forwarded-Proto and X-Forwarded-Host headers to indicate
    the original protocol and host. This middleware updates the request scope
    so FastAPI knows the request came via HTTPS.
    """
    async def dispatch(self, request: Request, call_next):
        # Trust X-Forwarded-Proto header from Cloud Run
        forwarded_proto = request.headers.get("x-forwarded-proto")
        if forwarded_proto:
            request.scope["scheme"] = forwarded_proto
            logger.debug(f"Updated request scheme to: {forwarded_proto}")

        # Trust X-Forwarded-Host header from Cloud Run
        forwarded_host = request.headers.get("x-forwarded-host")
        if forwarded_host:
            # Parse host and port if present
            if ":" in forwarded_host:
                host, port = forwarded_host.rsplit(":", 1)
                request.scope["server"] = (host, int(port))
            else:
                # Use default port based on scheme
                port = 443 if request.scope.get("scheme") == "https" else 80
                request.scope["server"] = (forwarded_host, port)
            logger.debug(f"Updated request server to: {request.scope['server']}")

        response = await call_next(request)
        return response

# Add proxy headers middleware
app.add_middleware(ProxyHeadersMiddleware)

# Include API routers
from app.features.auth.api import router as auth_router
from app.features.candidate.api import router as candidate_router
from app.features.resume_upload.api import router as resume_upload_router
from app.features.resume_analysis.api import router as analysis_router
from app.features.admin.api import router as admin_router
from app.features.profile.api import router as profile_router

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(profile_router, prefix="/api/v1/profile", tags=["profile"])
app.include_router(candidate_router, prefix="/api/v1/candidates", tags=["candidates"])
app.include_router(resume_upload_router, prefix="/api/v1/resume_upload", tags=["resumes"])
app.include_router(analysis_router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])

logger.info("All API routes registered successfully")

# Global exception handlers
@app.exception_handler(Exception)
async def handle_exceptions(request: Request, exc: Exception):
    """
    Unified exception handler for all errors.
    Handles both expected client errors (4xx) and unexpected server errors (5xx).
    """
    client_ip = request.client.host if request.client else "unknown"

    # Handle expected client errors (400-level)
    if isinstance(exc, (SecurityError, ValueError)):
        logger.warning(f"Client error: {str(exc)} - IP: {client_ip}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Bad Request", "message": str(exc)}
        )

    if isinstance(exc, RequestValidationError):
        logger.warning(f"Validation error: {exc.errors()} - IP: {client_ip}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Validation Error", "detail": exc.errors()}
        )

    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail}
        )

    # Handle unexpected server errors (500-level)
    logger.error(f"Unexpected error: {str(exc)} - IP: {client_ip}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal Server Error", "message": "An unexpected error occurred"}
    )


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the current status of the application and its dependencies.
    """
    try:
        # Check database health
        db_health = get_db_health()
        
        # Check rate limiter health
        rate_limiter_health = {
            "status": "healthy" if rate_limiter.redis_client else "unavailable",
            "redis_connected": rate_limiter.redis_client is not None
        }
        
        overall_status = "healthy"
        if db_health["status"] != "healthy":
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": "2024-11-30T12:00:00Z",  # Would use datetime.utcnow().isoformat()
            "version": "1.0.0",
            "services": {
                "database": db_health,
                "rate_limiter": rate_limiter_health
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "type": "health_check_error"
            }
        )


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": "AI Resume Review Platform API",
        "version": "1.0.0", 
        "description": "Secure authentication and user management API",
        "documentation": "/docs",
        "health": "/health",
        "features": [
            "JWT Authentication",
            "Bcrypt Password Hashing",  
            "Rate Limiting",
            "Account Security",
            "Role-based Access Control",
            "Admin Management"
        ]
    }


# Startup message - moved to lifespan function for proper async handling
# The new infrastructure initialization is now handled in the lifespan function above


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )