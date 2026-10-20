
import logging
from html import escape

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema

from ..config import settings

logger = logging.getLogger(__name__)


def _mail_client() -> FastMail | None:
    if (
        not settings.mail_username
        or not settings.mail_password
        or not settings.mail_from
    ):
        logger.warning(
            "Email yuborilmadi: MAIL_USERNAME, MAIL_PASSWORD "
            "va MAIL_FROM sozlanmagan"
        )
        return None

    config = ConnectionConfig(
        MAIL_USERNAME=settings.mail_username,
        MAIL_PASSWORD=settings.mail_password,
        MAIL_FROM=settings.mail_from,
        MAIL_PORT=settings.mail_port,
        MAIL_SERVER=settings.mail_server,
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
    )

    return FastMail(config)


async def _send_email(
    user_email: str,
    subject: str,
    body: str,
) -> None:
    mail_client = _mail_client()

    if mail_client is None:
        return

    message = MessageSchema(
        subject=subject,
        recipients=[user_email],  # Xabar userning o'ziga boradi
        body=body,
        subtype="html",
    )

    await mail_client.send_message(message)

    logger.info("Email foydalanuvchiga yuborildi: %s", user_email)


async def send_welcome_email(email: str, username: str) -> None:
    safe_username = escape(username)

    await _send_email(
        user_email=email,
        subject="Xush kelibsiz!",
        body=(
            f"<h2>Salom, {safe_username}!</h2>"
            "<p>Blog API ga xush kelibsiz!</p>"
            "<p>Hisobingiz muvaffaqiyatli yaratildi.</p>"
        ),
    )


async def send_post_notification(
    user_email: str,
    title: str,
) -> None:
    safe_title = escape(title)

    await _send_email(
        user_email=user_email,
        subject="Postingiz muvaffaqiyatli yaratildi",
        body=(
            "<h2>Assalomu alaykum!</h2>"
            "<p>Sizning postingiz muvaffaqiyatli yaratildi:</p>"
            f"<p><strong>{safe_title}</strong></p>"
            "<p>Blog API dan foydalanganingiz uchun rahmat!</p>"
        ),
    )


def write_log(action: str, user_id: int, details: str = "") -> None:
    """Faoliyat logi."""
    logger.info(
        "LOG: user=%s | action=%s | %s",
        user_id,
        action,
        details,
    )
