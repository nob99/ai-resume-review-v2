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

from app.api.auth import router as auth_router
from app.api.upload import router as upload_router
from app.database.connection import init_database, close_database, get_db_health
from app.core.rate_limiter import rate_limiter
from app.core.security import SecurityError

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
        
        # Initialize rate limiter
        await rate_limiter.connect()
        logger.info("Rate limiter initialized")
        
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Resume Review Platform Backend")
    
    try:
        # Close rate limiter
        await rate_limiter.disconnect()
        logger.info("Rate limiter disconnected")
        
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
        "https://*.airesumereview.com",  # Production domains
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers with API versioning
app.include_router(auth_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")

# Global exception handlers
@app.exception_handler(SecurityError)
async def security_error_handler(request: Request, exc: SecurityError):
    """Handle security errors."""
    client_ip = request.client.host if request.client else "unknown"
    logger.warning(f"Security error: {str(exc)} - IP: {client_ip}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Security Error",
            "message": str(exc),
            "type": "security_error"
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    client_ip = request.client.host if request.client else "unknown"
    logger.warning(f"Validation error: {exc.errors()} - IP: {client_ip}")
    
    # Ensure error details are JSON serializable
    errors = []
    for error in exc.errors():
        serializable_error = {}
        for key, value in error.items():
            if isinstance(value, bytes):
                serializable_error[key] = value.decode('utf-8', errors='replace')
            else:
                serializable_error[key] = value
        errors.append(serializable_error)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": errors
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    client_ip = request.client.host if request.client else "unknown"
    logger.error(f"Unexpected error: {str(exc)} - IP: {client_ip}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "type": "server_error"
        }
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


# Startup message
@app.on_event("startup")
async def startup_message():
    """Log startup message."""
    logger.info("🚀 AI Resume Review Platform API is ready!")
    logger.info("📚 Documentation: http://localhost:8000/docs")
    logger.info("🏥 Health Check: http://localhost:8000/health")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )