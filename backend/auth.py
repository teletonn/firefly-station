from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from . import database
import logging

logger = logging.getLogger(__name__)

# JWT settings
SECRET_KEY = "your-secret-key-here"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=300)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(username: str, password: str):
    """Authenticate admin user with enhanced logging."""
    try:
        if not username or not password:
            print(f"DEBUG: Empty credentials provided - username: {bool(username)}, password: {bool(password)}")
            return False

        print(f"DEBUG: Attempting to authenticate user: {username}")
        user = database.get_admin_user_by_username(username)

        if not user:
            print(f"DEBUG: User '{username}' not found in database")
            return False

        print(f"DEBUG: User found: {user['username']}, active: {user.get('is_active', True)}")

        if not user.get('is_active', True):
            print(f"DEBUG: User '{username}' is not active")
            return False

        password_valid = verify_password(password, user['hashed_password'])
        print(f"DEBUG: Password verification result: {password_valid}")

        if not password_valid:
            print(f"DEBUG: Invalid password for user '{username}'")
            return False

        print(f"DEBUG: Authentication successful for user: {username}")
        return user

    except Exception as e:
        print(f"DEBUG: Error during authentication for user '{username}': {e}")
        return False

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user."""
    logger.info(f"Token received: {credentials.credentials[:50]}...")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        logger.info(f"Decoded username: {username}")
        if username is None:
            raise credentials_exception
    except JWTError:
        logger.error("JWT decode failed")
        raise credentials_exception

    user = database.get_admin_user_by_username(username)
    logger.info(f"User from DB: {user}")
    if user is None:
        raise credentials_exception
    logger.info(f"User role: {user.get('role', 'no_role')}, is_active: {user.get('is_active', False)}")
    return user

def get_current_active_user(current_user = Depends(get_current_user)):
    """Get current active user."""
    if not current_user['is_active']:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def check_permission(user, required_permission):
    """Check if a user has a required permission."""
    logger.info(f"Checking permission for user {user.get('username', 'unknown')} with role {user.get('role', 'no_role')} for permission '{required_permission}'")

    # Get permissions from the database for the user's role
    role_permissions = database.get_role_permissions(user['role'])
    logger.info(f"Role permissions from DB for role '{user['role']}': {role_permissions}")

    # The 'super_admin' role has an 'all' permission, which grants access to everything.
    if "all" in role_permissions:
        logger.info("Permission granted: 'all' permission found in role.")
        return True

    # Check for specific permissions. This allows for granular control, e.g., 'zones:read', 'zones:write'.
    # A role with the 'zones' permission will be granted access to both 'zones:read' and 'zones:write'.
    for perm in role_permissions:
        if required_permission == perm or required_permission.startswith(f"{perm}:"):
            logger.info(f"Permission granted: role '{user['role']}' has permission '{perm}' which satisfies '{required_permission}'")
            return True

    logger.warning(f"Permission DENIED for user '{user.get('username', 'unknown')}' with role '{user.get('role', 'no_role')}' for permission '{required_permission}'")
    return False