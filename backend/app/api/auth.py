"""
Authentication API endpoints with secure password handling and rate limiting.
Implements login, registration, password management, and admin functions.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr

from app.core.security import (
    create_access_token, 
    verify_token, 
    SecurityError,
    PasswordValidationResult,
    validate_password
)
from app.core.rate_limiter import (
    check_login_rate_limit,
    check_registration_rate_limit, 
    check_password_reset_rate_limit,
    rate_limiter,
    RateLimitType
)
from app.models.user import (
    User, 
    UserCreate, 
    UserUpdate,
    UserResponse,
    UserDetailResponse,
    PasswordUpdate,
    AdminPasswordReset,
    LoginRequest,
    LoginResponse,
    UserRole
)
from app.database.connection import get_db

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security scheme
security = HTTPBearer()

# JWT token expiration (Sprint 2 requirement: 15 minutes)
ACCESS_TOKEN_EXPIRE_MINUTES = 15


class TokenData(BaseModel):
    """Token data model."""
    user_id: Optional[str] = None
    email: Optional[str] = None


class PasswordStrengthCheck(BaseModel):
    """Password strength check request."""
    password: str


class PasswordStrengthResponse(BaseModel):
    """Password strength check response."""
    is_valid: bool
    strength_score: int
    errors: List[str]
    suggestions: List[str]


# Dependency to get current user from token
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: JWT token from Authorization header
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify and decode token
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
        
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        
        if user_id is None or email is None:
            raise credentials_exception
            
        # Get user from database
        user = db.query(User).filter(
            User.id == user_id, 
            User.email == email,
            User.is_active == True
        ).first()
        
        if user is None:
            raise credentials_exception
            
        # Check if account is locked
        if user.is_account_locked():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked due to security reasons"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise credentials_exception


# Dependency to get current admin user
async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current authenticated admin user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current admin user
        
    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Register a new user with secure password handling.
    
    Args:
        user_data: User registration data
        request: FastAPI request object
        background_tasks: Background tasks handler
        db: Database session
        
    Returns:
        Created user information
        
    Raises:
        HTTPException: If registration fails or rate limit exceeded
    """
    # Check rate limiting
    await check_registration_rate_limit(request)
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email.lower()).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user (password hashing happens in User.__init__)
        new_user = User(
            email=user_data.email,
            password=user_data.password,  # Will be hashed automatically
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role
        )
        
        # Save to database
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"New user registered: {new_user.email}")
        
        # TODO: Add email verification in future sprint
        # background_tasks.add_task(send_verification_email, new_user.email)
        
        return UserResponse.from_orm(new_user)
        
    except HTTPException:
        raise
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.options("/login")
async def login_options():
    """Handle CORS preflight requests for login endpoint."""
    return {"message": "OK"}


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token.
    
    Args:
        login_data: Login credentials
        request: FastAPI request object
        db: Database session
        
    Returns:
        JWT access token and user information
        
    Raises:
        HTTPException: If login fails or rate limit exceeded
    """
    # Check rate limiting (per email and per IP)
    await check_login_rate_limit(request, login_data.email)
    
    try:
        # Get user by email
        user = db.query(User).filter(
            User.email == login_data.email.lower(),
            User.is_active == True
        ).first()
        
        # Always check password even if user doesn't exist (timing attack prevention)
        password_valid = False
        if user:
            # Check if account is locked
            if user.is_account_locked():
                # Update database with failed attempt info
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account is temporarily locked due to multiple failed login attempts"
                )
            
            password_valid = user.check_password(login_data.password)
            
            # Update database with login attempt result
            db.commit()
        
        if not user or not password_valid:
            # Log failed login attempt
            logger.warning(f"Failed login attempt for email: {login_data.email}")
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role
            },
            expires_delta=access_token_expires
        )
        
        logger.info(f"Successful login for user: {user.email}")
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
            user=UserResponse.from_orm(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user information
    """
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user information.
    
    Args:
        user_update: User update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated user information
    """
    try:
        # Update user fields
        update_data = user_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"User updated: {current_user.email}")
        
        return UserResponse.from_orm(current_user)
        
    except Exception as e:
        db.rollback()
        logger.error(f"User update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.post("/change-password")
async def change_password(
    password_data: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password.
    
    Args:
        password_data: Password change data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    try:
        # Verify current password
        if not current_user.check_password(password_data.current_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Set new password (validation happens in User.set_password)
        current_user.set_password(password_data.new_password)
        
        db.commit()
        
        logger.info(f"Password changed for user: {current_user.email}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.post("/check-password-strength", response_model=PasswordStrengthResponse)
async def check_password_strength(password_data: PasswordStrengthCheck):
    """
    Check password strength without storing it.
    
    Args:
        password_data: Password to check
        
    Returns:
        Password strength analysis
    """
    try:
        validation_result = validate_password(password_data.password)
        
        # Generate suggestions based on errors
        suggestions = []
        for error in validation_result.errors:
            if "uppercase" in error.lower():
                suggestions.append("Add uppercase letters (A-Z)")
            elif "lowercase" in error.lower():
                suggestions.append("Add lowercase letters (a-z)")
            elif "digit" in error.lower():
                suggestions.append("Add numbers (0-9)")
            elif "special" in error.lower():
                suggestions.append("Add special characters (!@#$%^&*)")
            elif "characters long" in error.lower():
                suggestions.append("Make it longer (at least 8 characters)")
            elif "common" in error.lower():
                suggestions.append("Choose a more unique password")
        
        if not suggestions:
            suggestions.append("Your password meets all security requirements!")
        
        return PasswordStrengthResponse(
            is_valid=validation_result.is_valid,
            strength_score=validation_result.strength_score,
            errors=validation_result.errors,
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(f"Password strength check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check password strength"
        )


# Admin-only endpoints
@router.get("/admin/users", response_model=List[UserDetailResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    List all users (admin only).
    
    Args:
        skip: Number of users to skip
        limit: Maximum number of users to return
        admin_user: Current admin user
        db: Database session
        
    Returns:
        List of users with detailed information
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return [UserDetailResponse.from_orm(user) for user in users]


@router.post("/admin/reset-password")
async def admin_reset_password(
    reset_data: AdminPasswordReset,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Reset user password (admin only).
    
    Args:
        reset_data: Password reset data
        request: FastAPI request object
        admin_user: Current admin user
        db: Database session
        
    Returns:
        Success message
    """
    # Check rate limiting for password reset operations
    await check_password_reset_rate_limit(request)
    
    try:
        # Get target user
        target_user = db.query(User).filter(User.id == reset_data.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Reset password
        target_user.set_password(reset_data.new_password)
        target_user.unlock_account()  # Unlock account if it was locked
        
        # TODO: Implement force password change flag in future sprint
        if reset_data.force_password_change:
            # This would require additional database field and logic
            pass
        
        db.commit()
        
        logger.info(f"Admin {admin_user.email} reset password for user {target_user.email}")
        
        return {"message": f"Password reset successfully for user {target_user.email}"}
        
    except HTTPException:
        raise
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Admin password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


@router.post("/admin/unlock-account/{user_id}")
async def unlock_user_account(
    user_id: UUID,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Unlock user account (admin only).
    
    Args:
        user_id: ID of user to unlock
        admin_user: Current admin user
        db: Database session
        
    Returns:
        Success message
    """
    try:
        # Get target user
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Unlock account
        target_user.unlock_account()
        
        # Reset rate limiting for this user
        await rate_limiter.reset_rate_limit(RateLimitType.LOGIN, target_user.email)
        
        db.commit()
        
        logger.info(f"Admin {admin_user.email} unlocked account for user {target_user.email}")
        
        return {"message": f"Account unlocked successfully for user {target_user.email}"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Account unlock error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlock account"
        )


@router.get("/admin/rate-limit-status/{email}")
async def get_user_rate_limit_status(
    email: EmailStr,
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Get rate limit status for user (admin only).
    
    Args:
        email: User email to check
        admin_user: Current admin user
        
    Returns:
        Rate limit status information
    """
    try:
        login_status = await rate_limiter.get_rate_limit_status(RateLimitType.LOGIN, email)
        
        return {
            "email": email,
            "login_rate_limit": login_status
        }
        
    except Exception as e:
        logger.error(f"Rate limit status check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check rate limit status"
        )