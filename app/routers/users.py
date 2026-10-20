from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, oauth2, schemas
from ..database import get_db
from ..utils.email import send_welcome_email, write_log
from ..utils.hashing import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["Users"])

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.UserResponse,
)
def create_user(
    user: schemas.UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    existing = db.query(models.User).filter(
        models.User.email == user.email
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu email allaqachon ro'yxatdan o'tgan"
        )

    user_data = user.model_dump()
    user_data["password"] = hash_password(user.password)
    new_user = models.User(**user_data)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    background_tasks.add_task(
        send_welcome_email,
        email=new_user.email,
        username=new_user.username
    )
    background_tasks.add_task(
        write_log,
        action="user_created",
        user_id=new_user.id,
        details=f"email={new_user.email}"
    )

    return new_user


@router.get("/me", response_model=schemas.UserResponse)
def get_current_user(
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return current_user


@router.put("/me/password")
def change_password(
    password_update: schemas.UserPasswordUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    if not verify_password(password_update.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Eski parol noto'g'ri",
        )

    current_user.password = hash_password(password_update.new_password)
    db.commit()
    return {"message": "Parol muvaffaqiyatli o'zgartirildi"}


@router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID={user_id} bo'lgan foydalanuvchi topilmadi",
        )
    return user