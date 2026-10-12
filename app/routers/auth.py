from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..utils.hashing import verify_password
from ..oauth2 import create_access_token

router = APIRouter(
    tags=["Authentication"]
)

@router.post("/login", response_model=schemas.Token)
def login(
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # 1. Foydalanuvchini topish
    user = db.query(models.User).filter(
        models.User.email == user_credentials.username
    ).first()

    # 2. Foydalanuvchi borligini tekshirish
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Noto'g'ri email yoki parol"
        )

    # 3. Parolni tekshirish
    if not verify_password(user_credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Noto'g'ri email yoki parol"
        )

    # 4. Token yaratish
    access_token = create_access_token(
        data={"user_id": user.id}
    )

    # 5. Tokenni qaytarish
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }