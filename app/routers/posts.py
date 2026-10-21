
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.orm import Session

from .. import models, schemas, oauth2
from ..database import get_db
from ..cache import (
    cache_get,
    cache_set,
    cache_delete,
    cache_delete_pattern,
)

router = APIRouter(prefix="/posts", tags=["Posts"])


# READ ALL: Barcha postlarni olish
@router.get("/", response_model=List[schemas.PostResponse])
def get_all_posts(
    db: Session = Depends(get_db),
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = "",
):
    # Parametrlarni tekshirish
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit 1 dan 100 gacha bo'lishi kerak",
        )

    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skip manfiy bo'lishi mumkin emas",
        )

    search = search or ""
    cache_key = (
        f"posts:all:limit={limit}:skip={skip}:search={search}"
    )

    # 1. Redis cache'dan tekshirish
    cached = cache_get(cache_key)

    if cached is not None:
        print(f"✅ Cache HIT: {cache_key}")
        return cached

    # 2. Cache'da yo'q bo'lsa, ma'lumotlar bazasidan olish
    print(f"❌ Cache MISS: {cache_key}")

    posts = (
        db.query(models.Post)
        .filter(models.Post.title.contains(search))
        .limit(limit)
        .offset(skip)
        .all()
    )

    # SQLAlchemy obyektlarini JSON uchun mos dict'ga aylantirish
    posts_data = [
        schemas.PostResponse.model_validate(
            post, from_attributes=True
        ).model_dump(mode="json")
        for post in posts
    ]

    # 3. Natijani 5 daqiqaga Redis'ga saqlash
    cache_set(cache_key, posts_data, ttl=300)

    return posts_data


# READ ONE: Bitta postni olish
@router.get("/{post_id}", response_model=schemas.PostResponse)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
):
    cache_key = f"posts:{post_id}"

    # 1. Cache tekshirish
    cached = cache_get(cache_key)

    if cached is not None:
        print(f"✅ Cache HIT: {cache_key}")
        return cached

    print(f"❌ Cache MISS: {cache_key}")

    # 2. Database'dan olish
    post = (
        db.query(models.Post)
        .filter(models.Post.id == post_id)
        .first()
    )

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID={post_id} bo'lgan post topilmadi",
        )

    post_data = schemas.PostResponse.model_validate(
        post, from_attributes=True
    ).model_dump(mode="json")

    # 3. 10 daqiqaga cache'ga saqlash
    cache_set(cache_key, post_data, ttl=600)

    return post_data


# CREATE: Yangi post yaratish
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.PostResponse,
)
def create_post(
    post: schemas.PostCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    new_post = models.Post(
        owner_id=current_user.id,
        **post.model_dump(),
    )

    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    # Ro'yxat cache'larini tozalash
    background_tasks.add_task(
        cache_delete_pattern, "posts:all:*"
    )

    return new_post


# UPDATE: Postni yangilash
@router.put(
    "/{post_id}",
    response_model=schemas.PostResponse,
)
def update_post(
    post_id: int,
    updated_post: schemas.PostUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    post = (
        db.query(models.Post)
        .filter(models.Post.id == post_id)
        .first()
    )

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID={post_id} bo'lgan post topilmadi",
        )

    if post.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Siz bu postni yangilay olmaysiz",
        )

    # Faqat yuborilgan maydonlarni yangilash
    update_data = updated_post.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(post, field, value)

    db.commit()
    db.refresh(post)

    # Bitta post va barcha ro'yxat cache'larini tozalash
    background_tasks.add_task(cache_delete, f"posts:{post_id}")
    background_tasks.add_task(
        cache_delete_pattern, "posts:all:*"
    )

    return post


# DELETE: Postni o'chirish
@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_post(
    post_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    post = (
        db.query(models.Post)
        .filter(models.Post.id == post_id)
        .first()
    )

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID={post_id} bo'lgan post topilmadi",
        )

    if post.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Siz bu postni o'chira olmaysiz",
        )

    db.delete(post)
    db.commit()

    # Eskirgan cache'larni tozalash
    background_tasks.add_task(cache_delete, f"posts:{post_id}")
    background_tasks.add_task(
        cache_delete_pattern, "posts:all:*"
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
