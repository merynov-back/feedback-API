import smtplib
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.celery_app import celery_app
from src.config import settings

logger = logging.getLogger(__name__)


def _build_verification_email(
    to_email: str,
    to_name: str,
    code: str,
) -> MIMEMultipart:
    """Сформировать MIME-сообщение с HTML-содержимым."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Подтверждение email — Feedback API"
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg["To"] = to_email

    html_body = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0;padding:0;background:#f4f6f9;font-family:'Helvetica Neue',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="padding:40px 20px;">
            <table width="520" cellpadding="0" cellspacing="0"
                   style="background:#ffffff;border-radius:12px;
                          box-shadow:0 4px 20px rgba(0,0,0,.08);overflow:hidden;">

              <!-- Header -->
              <tr>
                <td style="background:linear-gradient(135deg,#667eea,#764ba2);
                           padding:32px;text-align:center;">
                  <h1 style="margin:0;color:#fff;font-size:24px;font-weight:700;
                             letter-spacing:-.5px;">
                    Feedback API
                  </h1>
                  <p style="margin:8px 0 0;color:rgba(255,255,255,.8);font-size:14px;">
                    Подтверждение регистрации
                  </p>
                </td>
              </tr>

              <!-- Body -->
              <tr>
                <td style="padding:40px 32px;">
                  <p style="margin:0 0 16px;color:#374151;font-size:16px;">
                    Привет, <strong>{to_name}</strong>! 👋
                  </p>
                  <p style="margin:0 0 28px;color:#6b7280;font-size:15px;line-height:1.6;">
                    Введи код ниже чтобы подтвердить свой email и активировать аккаунт.
                    Код действует <strong>15 минут</strong>.
                  </p>

                  <!-- OTP Code -->
                  <div style="text-align:center;margin:0 0 28px;">
                    <div style="display:inline-block;background:#f3f4f6;
                                border:2px dashed #d1d5db;border-radius:12px;
                                padding:20px 40px;">
                      <span style="font-size:42px;font-weight:800;letter-spacing:12px;
                                   color:#1f2937;font-family:'Courier New',monospace;">
                        {code}
                      </span>
                    </div>
                  </div>

                  <p style="margin:0;color:#9ca3af;font-size:13px;line-height:1.5;">
                    Если ты не регистрировался в Feedback API — просто проигнорируй это письмо.
                    Твой аккаунт не будет создан.
                  </p>
                </td>
              </tr>

              <!-- Footer -->
              <tr>
                <td style="background:#f9fafb;padding:20px 32px;
                           border-top:1px solid #e5e7eb;text-align:center;">
                  <p style="margin:0;color:#9ca3af;font-size:12px;">
                    © 2026 Feedback API. Это автоматическое письмо, не отвечай на него.
                  </p>
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg

@celery_app.task(
    bind=True,
    name="tasks.send_verification_email",
    max_retries=3,
    default_retry_delay=60,         
)

def send_verification_email(
    self,
    user_email: str,
    user_name: str,
    otp_code: str,
) -> dict:
    logger.info(
        "Отправка verification email: to=%s, task_id=%s, attempt=%d",
        user_email,
        self.request.id,
        self.request.retries + 1,
    )
    
    try:
        msg = _build_verification_email(user_email, user_name, otp_code)

        with smtplib.SMTP_SSL(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
        ) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(
                from_addr=settings.EMAILS_FROM_EMAIL,
                to_addrs=[user_email],
                msg=msg.as_string()
            )
        logger.info(
            "Email успешно отправлен: to=%s", {user_email},
        )

        return {"status": "sent", "to": user_email}

    except smtplib.SMTPException as exc:
        logger.warning(
            "SMTP ошибка при отправке на %s: %s. Retry %d/%d",
            user_email,
            exc,
            self.request.retries + 1,
            self.max_retries,
        )

        raise self.retry(
            exc=exc
        )