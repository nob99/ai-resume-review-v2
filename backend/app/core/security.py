"""
Security utilities for password hashing, validation, and authentication.
Implements bcrypt for secure password hashing with comprehensive validation.
"""

import re
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from passlib.context import CryptContext
from passlib.exc import InvalidTokenError
from jose import JWTError, jwt
from pydantic import BaseModel, Field

# Configure secure logging (never log passwords)
logger = logging.getLogger(__name__)

# Password hashing context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# Common weak passwords to reject
COMMON_PASSWORDS = {
    "password", "123456", "123456789", "12345678", "12345", "1234567", "password123",
    "admin", "qwerty", "abc123", "Password1", "welcome", "monkey", "dragon",
    "letmein", "password1", "Password", "123123", "welcome123", "admin123"
}

# JWT Configuration (will be moved to config later)
SECRET_KEY = "your-secret-key-change-in-production"  # TODO: Move to environment config
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class PasswordPolicy(BaseModel):
    """Password policy configuration."""
    min_length: int = Field(default=8, ge=1)
    require_uppercase: bool = Field(default=True)
    require_lowercase: bool = Field(default=True)
    require_digit: bool = Field(default=True)
    require_special: bool = Field(default=True)
    max_length: int = Field(default=128, le=256)
    check_common_passwords: bool = Field(default=True)


class PasswordValidationResult(BaseModel):
    """Result of password validation."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    strength_score: int = Field(default=0, ge=0, le=100)


class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass


class PasswordHasher:
    """Secure password hashing and validation utilities."""
    
    def __init__(self, policy: Optional[PasswordPolicy] = None):
        """Initialize with password policy."""
        self.policy = policy or PasswordPolicy()
        self._pwd_context = pwd_context
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt with secure salt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
            
        Raises:
            SecurityError: If password is invalid
        """
        # Validate password before hashing
        validation_result = self.validate_password(password)
        if not validation_result.is_valid:
            raise SecurityError(f"Password validation failed: {', '.join(validation_result.errors)}")
        
        # Hash the password
        try:
            hashed = self._pwd_context.hash(password)
            logger.info("Password successfully hashed")
            return hashed
        except Exception as e:
            logger.error(f"Password hashing failed: {str(e)}")
            raise SecurityError("Failed to hash password")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Stored password hash
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            is_valid = self._pwd_context.verify(plain_password, hashed_password)
            if is_valid:
                logger.info("Password verification successful")
            else:
                logger.warning("Password verification failed - invalid credentials")
            return is_valid
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False
    
    def needs_rehash(self, hashed_password: str) -> bool:
        """
        Check if password hash needs to be updated.
        
        Args:
            hashed_password: Stored password hash
            
        Returns:
            True if hash should be updated
        """
        try:
            return self._pwd_context.needs_update(hashed_password)
        except Exception:
            return True  # Assume needs update if can't check
    
    def validate_password(self, password: str) -> PasswordValidationResult:
        """
        Validate password against security policy.
        
        Args:
            password: Plain text password to validate
            
        Returns:
            PasswordValidationResult with validation details
        """
        errors = []
        strength_score = 0
        
        # Check basic length requirements
        if len(password) < self.policy.min_length:
            errors.append(f"Password must be at least {self.policy.min_length} characters long")
        else:
            strength_score += 20
        
        if len(password) > self.policy.max_length:
            errors.append(f"Password must not exceed {self.policy.max_length} characters")
            
        # Check character requirements
        if self.policy.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        else:
            strength_score += 15
            
        if self.policy.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        else:
            strength_score += 15
            
        if self.policy.require_digit and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        else:
            strength_score += 15
            
        if self.policy.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)")
        else:
            strength_score += 15
        
        # Check against common passwords
        if self.policy.check_common_passwords and password.lower() in COMMON_PASSWORDS:
            errors.append("Password is too common, please choose a more unique password")
            strength_score = max(0, strength_score - 30)
        
        # Additional strength checks
        if len(password) >= 12:
            strength_score += 10  # Bonus for longer passwords
            
        if len(set(password)) >= len(password) * 0.6:  # Good character diversity
            strength_score += 10
        
        # Cap strength score
        strength_score = min(100, strength_score)
        
        return PasswordValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            strength_score=strength_score
        )
    
    def generate_secure_password(self, length: int = 12) -> str:
        """
        Generate a cryptographically secure random password.
        
        Args:
            length: Desired password length
            
        Returns:
            Secure random password
        """
        if length < self.policy.min_length:
            length = self.policy.min_length
            
        # Character sets
        lowercase = "abcdefghijklmnopqrstuvwxyz"
        uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        digits = "0123456789"
        special = "!@#$%^&*(),.?\":{}|<>"
        
        # Ensure at least one character from each required set
        password = []
        if self.policy.require_lowercase:
            password.append(secrets.choice(lowercase))
        if self.policy.require_uppercase:
            password.append(secrets.choice(uppercase))
        if self.policy.require_digit:
            password.append(secrets.choice(digits))
        if self.policy.require_special:
            password.append(secrets.choice(special))
        
        # Fill remaining length with random characters
        all_chars = lowercase + uppercase + digits + special
        for _ in range(length - len(password)):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password list
        for i in range(len(password)):
            j = secrets.randbelow(len(password))
            password[i], password[j] = password[j], password[i]
        
        return ''.join(password)


class TokenManager:
    """JWT token management for authentication."""
    
    def __init__(self, secret_key: str = SECRET_KEY, algorithm: str = ALGORITHM):
        """Initialize token manager."""
        self.secret_key = secret_key
        self.algorithm = algorithm
        self._redis_client = None
        # In-memory blacklist for testing when Redis is not available
        self._test_blacklist = set()
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token.
        
        Args:
            data: Data to encode in token
            expires_delta: Token expiration time
            
        Returns:
            JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.info("Access token created successfully")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Token creation failed: {str(e)}")
            raise SecurityError("Failed to create access token")
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token data or None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.warning(f"Token verification failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return None
    
    def set_redis_client(self, redis_client):
        """Set Redis client for token blacklisting."""
        self._redis_client = redis_client
    
    async def blacklist_token(self, token: str) -> bool:
        """
        Add token to blacklist using Redis or in-memory fallback.
        
        Args:
            token: JWT token to blacklist
            
        Returns:
            True if successfully blacklisted
        """
        # Try Redis first if available
        if self._redis_client:
            try:
                # Decode token to get expiration time
                payload = self.verify_token(token)
                if not payload:
                    return False
                
                exp_timestamp = payload.get("exp")
                if not exp_timestamp:
                    return False
                
                # Calculate TTL (time to live) for Redis key
                exp_time = datetime.fromtimestamp(exp_timestamp)
                current_time = datetime.utcnow()
                
                if exp_time <= current_time:
                    # Token already expired, no need to blacklist
                    return True
                
                ttl_seconds = int((exp_time - current_time).total_seconds())
                
                # Store token in Redis blacklist with expiration
                blacklist_key = f"blacklisted_token:{token}"
                await self._redis_client.setex(blacklist_key, ttl_seconds, "1")
                
                # Also add to in-memory blacklist as fallback
                self._test_blacklist.add(token)
                
                logger.info("Token successfully added to Redis blacklist and in-memory fallback")
                return True
                
            except RuntimeError as e:
                # Handle event loop issues in test environment - fall through to in-memory
                if "Event loop is closed" in str(e) or "no running event loop" in str(e):
                    logger.warning(f"Redis unavailable due to event loop issue, using in-memory blacklist: {str(e)}")
                else:
                    logger.error(f"Failed to blacklist token in Redis: {str(e)}")
                    return False
            except Exception as e:
                logger.error(f"Failed to blacklist token in Redis: {str(e)}")
                return False
        
        # Fallback to in-memory blacklist (for testing or when Redis unavailable)
        try:
            # Verify token is valid before blacklisting
            payload = self.verify_token(token)
            if not payload:
                return False
            
            # Add to in-memory blacklist
            self._test_blacklist.add(token)
            logger.info("Token successfully added to in-memory blacklist")
            return True
            
        except Exception as e:
            logger.error(f"Failed to blacklist token in memory: {str(e)}")
            return False
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted in Redis or in-memory blacklist.
        
        Args:
            token: JWT token to check
            
        Returns:
            True if token is blacklisted
        """
        # Check in-memory blacklist first (for testing)
        if token in self._test_blacklist:
            logger.debug("Token found in in-memory blacklist")
            return True
        
        # Check Redis blacklist if available
        if self._redis_client:
            try:
                blacklist_key = f"blacklisted_token:{token}"
                result = await self._redis_client.exists(blacklist_key)
                if result:
                    logger.debug("Token found in Redis blacklist")
                    return True
                return False
            except RuntimeError as e:
                # Handle event loop issues in test environment
                if "Event loop is closed" in str(e) or "no running event loop" in str(e):
                    logger.warning(f"Redis blacklist check skipped due to event loop issue, checking in-memory only")
                    return False
                logger.error(f"Failed to check Redis token blacklist: {str(e)}")
                return False
            except Exception as e:
                logger.error(f"Failed to check Redis token blacklist: {str(e)}")
                return False
        
        return False


# Global instances
password_hasher = PasswordHasher()
token_manager = TokenManager()


# Utility functions for backward compatibility
def hash_password(password: str) -> str:
    """Hash password using global password hasher."""
    return password_hasher.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using global password hasher."""
    return password_hasher.verify_password(plain_password, hashed_password)


def validate_password(password: str) -> PasswordValidationResult:
    """Validate password using global password hasher."""
    return password_hasher.validate_password(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create access token using global token manager."""
    return token_manager.create_access_token(data, expires_delta)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify token using global token manager."""
    return token_manager.verify_token(token)


async def blacklist_token(token: str) -> bool:
    """Blacklist token using global token manager."""
    return await token_manager.blacklist_token(token)


async def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted using global token manager."""
    return await token_manager.is_token_blacklisted(token)


def set_redis_client_for_tokens(redis_client):
    """Set Redis client for token blacklisting."""
    token_manager.set_redis_client(redis_client)