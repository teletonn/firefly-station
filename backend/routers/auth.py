from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict, Any
import logging
from backend import database
from backend import auth

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = "admin"

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login", response_model=Token)
async def login_for_access_token(request: Request):
    """Login and get access token with simplified authentication."""
    try:
        # Get raw body and parse manually
        body = await request.body()
        content_type = request.headers.get("content-type", "")

        username = None
        password = None

        if "application/x-www-form-urlencoded" in content_type:
            # Parse form data manually
            form_data = body.decode('utf-8')
            params = dict(param.split('=') for param in form_data.split('&') if '=' in param)
            username = params.get('username')
            password = params.get('password')
        elif "application/json" in content_type:
            # Parse JSON manually
            import json
            try:
                json_data = json.loads(body.decode('utf-8'))
                username = json_data.get('username')
                password = json_data.get('password')
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid JSON format"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Content-Type must be application/json or application/x-www-form-urlencoded"
            )

        logger.info(f"Login attempt for user: {username}")

        # Validate required fields
        if not username or not password:
            logger.warning(f"Login attempt with missing credentials: username={bool(username)}, password={bool(password)}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Username and password are required"
            )

        # Authenticate user
        user = auth.authenticate_user(username, password)
        if not user:
            logger.warning(f"Authentication failed for user: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token
        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(
            data={"sub": user['username']}, expires_delta=access_token_expires
        )

        # Update last login
        try:
            database.update_admin_last_login(user['id'])
            logger.info(f"Successful login for user: {username}")
        except Exception as e:
            logger.error(f"Failed to update last login for user {username}: {e}")
            # Don't fail the login if this fails

        return {"access_token": access_token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )

# Simple login endpoint for debugging
@router.post("/simple-login")
async def simple_login(request: Request):
    """Simple login endpoint for debugging."""
    try:
        body = await request.body()
        content_type = request.headers.get("content-type", "")

        print(f"DEBUG: Content-Type: {content_type}")
        print(f"DEBUG: Raw body: {body}")

        if "application/x-www-form-urlencoded" in content_type:
            form_data = body.decode('utf-8')
            print(f"DEBUG: Form data: {form_data}")
            params = dict(param.split('=') for param in form_data.split('&') if '=' in param)
            username = params.get('username')
            password = params.get('password')
        elif "application/json" in content_type:
            import json
            try:
                json_data = json.loads(body.decode('utf-8'))
                print(f"DEBUG: JSON data: {json_data}")
                username = json_data.get('username')
                password = json_data.get('password')
            except json.JSONDecodeError:
                return {"error": "Invalid JSON format"}
        else:
            return {"error": "Content-Type must be application/json or application/x-www-form-urlencoded"}

        print(f"DEBUG: Extracted username: {username}, password: {password}")

        if not username or not password:
            return {"error": "Username and password are required"}

        # Authenticate user
        user = auth.authenticate_user(username, password)
        if not user:
            return {"error": "Invalid credentials"}

        # Create access token
        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(
            data={"sub": user['username']}, expires_delta=access_token_expires
        )

        # Update last login
        try:
            database.update_admin_last_login(user['id'])
        except Exception as e:
            print(f"DEBUG: Failed to update last login: {e}")

        return {"access_token": access_token, "token_type": "bearer", "success": True}

    except Exception as e:
        print(f"DEBUG: Error in simple login: {e}")
        return {"error": str(e)}

# Keep the original OAuth2 endpoint as fallback
@router.post("/login-oauth2", response_model=Token)
async def login_for_access_token_oauth2(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token using OAuth2 form data (fallback method)."""
    try:
        logger.info(f"OAuth2 login attempt for user: {form_data.username}")

        user = auth.authenticate_user(form_data.username, form_data.password)
        if not user:
            logger.warning(f"OAuth2 authentication failed for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(
            data={"sub": user['username']}, expires_delta=access_token_expires
        )

        # Update last login
        try:
            database.update_admin_last_login(user['id'])
            logger.info(f"Successful OAuth2 login for user: {form_data.username}")
        except Exception as e:
            logger.error(f"Failed to update last login for user {form_data.username}: {e}")

        return {"access_token": access_token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during OAuth2 login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )

@router.post("/register", response_model=Token)
async def register_admin(user: UserCreate):
    """Register a new admin user and return an access token."""
    # Check if user already exists
    existing_user = database.get_admin_user_by_username(user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Hash password
    hashed_password = auth.get_password_hash(user.password)

    # Create user
    admin_id = database.create_admin_user(user.username, user.email, hashed_password, user.role)
    if not admin_id:
        raise HTTPException(status_code=500, detail="Failed to create user")

    # Create access token for the new user
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def read_users_me(current_user = Depends(auth.get_current_active_user)):
    """Get current user info."""
    return {
        "username": current_user['username'],
        "email": current_user['email'],
        "role": current_user['role'],
        "is_active": current_user['is_active']
    }