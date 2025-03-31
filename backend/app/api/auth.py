from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.db.session import get_db
from app.schemas import AuthResponse, LoginRequest, RegisterRequest, UserRead
from app.services.seed import assign_all_cases_to_doctor

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return AuthResponse(
        access_token=create_access_token(user.id, {"email": user.email, "role": user.role}),
        user=UserRead.model_validate(user),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name.strip(),
        role="physician",
        specialty=payload.specialty.strip() or "General Medicine",
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    assign_all_cases_to_doctor(db, user.id)
    db.commit()
    db.refresh(user)
    return AuthResponse(
        access_token=create_access_token(user.id, {"email": user.email, "role": user.role}),
        user=UserRead.model_validate(user),
    )
