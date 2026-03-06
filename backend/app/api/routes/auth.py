"""Authentication routes - register, login, profile."""

from pydantic import BaseModel, EmailStr

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.services.auth import authenticate_user, create_token, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: "UserResponse"


class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new account."""
    if len(body.password) < 6:
        raise HTTPException(
            status_code=400, detail="Password must be at least 6 characters"
        )

    try:
        user = register_user(db, body.email, body.name, body.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    token = create_token(user.user_id)
    return AuthResponse(
        token=token,
        user=UserResponse(user_id=user.user_id, email=user.email, name=user.name),
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Log in with email and password."""
    user = authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user.user_id)
    return AuthResponse(
        token=token,
        user=UserResponse(user_id=user.user_id, email=user.email, name=user.name),
    )


@router.get("/me", response_model=UserResponse)
def get_profile(user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return UserResponse(user_id=user.user_id, email=user.email, name=user.name)
