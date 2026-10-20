from app.routers.upload import UPLOAD_DIR

PNG_IMAGE = b"\x89PNG\r\n\x1a\n" + b"test image data"
PDF_FILE = b"%PDF-1.7\nsmall test document"
MP4_FILE = b"\x00\x00\x00\x18ftypisomsmall video"


def test_upload_image(authorized_client):
    response = authorized_client.post(
        "/upload/image",
        files={"file": ("image.png", PNG_IMAGE, "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"].endswith(".png")
    assert data["size"] == len(PNG_IMAGE)
    assert data["content_type"] == "image/png"
    image_path = UPLOAD_DIR / data["filename"]
    try:
        assert image_path.read_bytes() == PNG_IMAGE
        download = authorized_client.get(data["url"])
        assert download.status_code == 200
        assert download.content == PNG_IMAGE
    finally:
        image_path.unlink(missing_ok=True)


def test_upload_image_requires_authentication(client):
    response = client.post(
        "/upload/image",
        files={"file": ("image.png", PNG_IMAGE, "image/png")},
    )

    assert response.status_code == 401


def test_upload_image_rejects_mismatched_file_content(authorized_client):
    response = authorized_client.post(
        "/upload/image",
        files={"file": ("image.png", b"not an image", "image/png")},
    )

    assert response.status_code == 400


def test_upload_image_rejects_files_over_limit(authorized_client):
    response = authorized_client.post(
        "/upload/image",
        files={
            "file": (
                "image.png",
                b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024),
                "image/png",
            )
        },
    )

    assert response.status_code == 400


def test_upload_pdf_and_mp4(authorized_client):
    response = authorized_client.post(
        "/upload/files",
        files=[
            ("files", ("document.pdf", PDF_FILE, "application/pdf")),
            ("files", ("video.mp4", MP4_FILE, "video/mp4")),
        ],
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert [item["content_type"] for item in data["uploaded"]] == [
        "application/pdf",
        "video/mp4",
    ]
    paths = [UPLOAD_DIR / item["filename"] for item in data["uploaded"]]
    try:
        assert [path.read_bytes() for path in paths] == [PDF_FILE, MP4_FILE]
    finally:
        for path in paths:
            path.unlink(missing_ok=True)


def test_upload_avatar_updates_current_user(authorized_client, test_user):
    response = authorized_client.post(
        "/upload/avatar",
        files={"file": ("avatar.png", PNG_IMAGE, "image/png")},
    )

    assert response.status_code == 200
    avatar_url = response.json()["avatar_url"]
    user_response = authorized_client.get("/users/me")
    assert user_response.status_code == 200
    assert user_response.json()["avatar_url"] == avatar_url
    path = UPLOAD_DIR / response.json()["filename"]
    path.unlink(missing_ok=True)


def test_upload_multiple_files_rolls_back_when_a_file_is_invalid(authorized_client):
    before = set(UPLOAD_DIR.iterdir())
    response = authorized_client.post(
        "/upload/files",
        files=[
            ("files", ("document.pdf", PDF_FILE, "application/pdf")),
            ("files", ("not-a-pdf.pdf", b"invalid", "application/pdf")),
        ],
    )

    assert response.status_code == 400
    assert set(UPLOAD_DIR.iterdir()) == before
