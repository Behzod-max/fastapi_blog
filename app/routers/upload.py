import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .. import models, oauth2
from ..database import get_db

router = APIRouter(prefix="/upload", tags=["Upload"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILES = 5
MAX_SIZES = {
    "image": 5 * 1024 * 1024,
    "application/pdf": 20 * 1024 * 1024,
    "video/mp4": 100 * 1024 * 1024,
}
ALLOWED_TYPES = {
    "image/jpeg": (b"\xff\xd8\xff", ".jpg", "image"),
    "image/png": (b"\x89PNG\r\n\x1a\n", ".png", "image"),
    "image/gif": (b"GIF87a", ".gif", "image"),
    "image/webp": (b"RIFF", ".webp", "image"),
    "application/pdf": (b"%PDF-", ".pdf", "application/pdf"),
    "video/mp4": (b"", ".mp4", "video/mp4"),
}
IMAGE_TYPES = {content_type for content_type in ALLOWED_TYPES if content_type.startswith("image/")}


async def _read_file(file: UploadFile, *, images_only: bool = False) -> tuple[bytes, str]:
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES or (
        images_only and content_type not in IMAGE_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ruxsat etilmagan fayl turi",
        )

    signature, extension, size_group = ALLOWED_TYPES[content_type]
    contents = await file.read(MAX_SIZES[size_group] + 1)
    if len(contents) > MAX_SIZES[size_group]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fayl hajmi {MAX_SIZES[size_group] // (1024 * 1024)} MB dan oshmasin",
        )

    if content_type == "video/mp4":
        valid_signature = len(contents) >= 12 and contents[4:8] == b"ftyp"
    elif content_type == "image/webp":
        valid_signature = contents.startswith(signature) and contents[8:12] == b"WEBP"
    else:
        valid_signature = contents.startswith(signature)
    if not valid_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fayl mazmuni ko'rsatilgan formatga mos emas",
        )
    return contents, extension


async def _save_file(contents: bytes, extension: str) -> dict:
    filename = f"{uuid4()}{extension}"
    path = UPLOAD_DIR / filename
    try:
        await run_in_threadpool(path.write_bytes, contents)
    except OSError:
        path.unlink(missing_ok=True)
        raise
    return {
        "filename": filename,
        "url": f"/uploads/{filename}",
        "size": len(contents),
    }


def _remove_saved_files(paths: list[Path]) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    try:
        contents, extension = await _read_file(file, images_only=True)
        result = await _save_file(contents, extension)
        return {
            **result,
            "content_type": file.content_type,
            "uploaded_by": current_user.username,
        }
    finally:
        await file.close()


@router.post("/images")
async def upload_multiple_images(
    files: list[UploadFile] = File(...),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return await _upload_multiple(files, current_user, images_only=True)


@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    try:
        contents, extension = await _read_file(file)
        result = await _save_file(contents, extension)
        return {
            **result,
            "content_type": file.content_type,
            "uploaded_by": current_user.username,
        }
    finally:
        await file.close()


@router.post("/files")
async def upload_multiple_files(
    files: list[UploadFile] = File(...),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return await _upload_multiple(files, current_user, images_only=False)


async def _upload_multiple(
    files: list[UploadFile],
    current_user: models.User,
    *,
    images_only: bool,
) -> dict:
    if len(files) > MAX_FILES:
        for file in files:
            await file.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bir vaqtda eng ko'pi bilan 5 ta fayl yuklash mumkin",
        )

    saved_paths = []
    results = []
    try:
        for file in files:
            contents, extension = await _read_file(file, images_only=images_only)
            result = await _save_file(contents, extension)
            results.append({**result, "content_type": file.content_type})
            saved_paths.append(UPLOAD_DIR / result["filename"])
    except (OSError, HTTPException):
        _remove_saved_files(saved_paths)
        raise
    finally:
        for file in files:
            await file.close()

    return {
        "uploaded": results,
        "count": len(results),
        "uploaded_by": current_user.username,
    }


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    saved_path = None
    old_avatar_url = current_user.avatar_url
    try:
        contents, extension = await _read_file(file, images_only=True)
        result = await _save_file(contents, extension)
        saved_path = UPLOAD_DIR / result["filename"]
        current_user.avatar_url = result["url"]
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        if saved_path is not None:
            _remove_saved_files([saved_path])
        raise
    finally:
        await file.close()

    if old_avatar_url and old_avatar_url.startswith("/uploads/"):
        old_filename = Path(old_avatar_url).name
        if old_avatar_url == f"/uploads/{old_filename}":
            try:
                await run_in_threadpool(
                    (UPLOAD_DIR / old_filename).unlink,
                    missing_ok=True,
                )
            except OSError:
                logger.exception("Old user avatar could not be removed")

    return {
        **result,
        "content_type": file.content_type,
        "uploaded_by": current_user.username,
        "avatar_url": result["url"],
    }
