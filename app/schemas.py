from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ─── USER SCHEMAS ─────────────────────────────

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class UserPasswordUpdate(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1)


# ─── POST SCHEMAS ─────────────────────────────

class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str
    published: bool = True
    rating: Optional[int] = None


class PostCreate(PostBase):
    pass


class PostUpdate(PostBase):
    pass


class PostPatch(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    published: Optional[bool] = None
    rating: Optional[int] = None


class PostResponse(PostBase):
    id: int
    created_at: datetime
    owner_id: Optional[int] = None

    model_config = {
        "from_attributes": True
    }


class PostWithOwner(PostResponse):
    owner: Optional[UserResponse] = None

    model_config = {
        "from_attributes": True
    }


# ─── TOKEN SCHEMAS ────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: Optional[str] = None