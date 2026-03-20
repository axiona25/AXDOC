"""
Client SMTP per inviare email.
"""
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid
from typing import Optional

from django.core.files.base import ContentFile
from django.utils import timezone

from .models import MailAccount, MailAttachment, MailMessage


def send_email(
    account: MailAccount,
    to_addresses: list[str],
    subject: str,
    body_text: str = "",
    body_html: str = "",
    cc_addresses: list[str] | None = None,
    bcc_addresses: list[str] | None = None,
    attachments: list[dict] | None = None,
    reply_to_message: Optional[MailMessage] = None,
) -> MailMessage:
    """
    Invia una email tramite SMTP e salva il messaggio nel DB.
    attachments: [{"filename": str, "content_type": str, "data": bytes}]
    Ritorna il MailMessage creato.
    """
    msg = MIMEMultipart("mixed")
    msg["From"] = f"{account.name} <{account.email_address}>"
    msg["To"] = ", ".join(to_addresses)
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=account.email_address.split("@")[-1] if "@" in account.email_address else None)

    if cc_addresses:
        msg["Cc"] = ", ".join(cc_addresses)
    if reply_to_message and reply_to_message.message_id:
        msg["In-Reply-To"] = reply_to_message.message_id
        msg["References"] = reply_to_message.message_id

    if body_html:
        alt = MIMEMultipart("alternative")
        if body_text:
            alt.attach(MIMEText(body_text, "plain", "utf-8"))
        alt.attach(MIMEText(body_html, "html", "utf-8"))
        msg.attach(alt)
    elif body_text:
        msg.attach(MIMEText(body_text, "plain", "utf-8"))

    file_attachments = []
    if attachments:
        for att in attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(att["data"])
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{att["filename"]}"')
            msg.attach(part)
            file_attachments.append(att)

    all_recipients = list(to_addresses)
    if cc_addresses:
        all_recipients.extend(cc_addresses)
    if bcc_addresses:
        all_recipients.extend(bcc_addresses)

    if account.smtp_use_ssl:
        server = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port)
    else:
        server = smtplib.SMTP(account.smtp_host, account.smtp_port)
        if account.smtp_use_tls:
            server.starttls()

    server.login(account.smtp_username, account.smtp_password)
    server.sendmail(account.email_address, all_recipients, msg.as_string())
    server.quit()

    mid = msg["Message-ID"] or ""
    irt = msg.get("In-Reply-To", "") or ""

    mail_msg = MailMessage.objects.create(
        account=account,
        direction="out",
        message_id=mid,
        in_reply_to=irt,
        from_address=account.email_address,
        from_name=account.name,
        to_addresses=[{"email": a, "name": ""} for a in to_addresses],
        cc_addresses=[{"email": a, "name": ""} for a in (cc_addresses or [])],
        bcc_addresses=[{"email": a, "name": ""} for a in (bcc_addresses or [])],
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        has_attachments=len(file_attachments) > 0,
        status="read",
        folder="SENT",
        sent_at=timezone.now(),
    )

    for att in file_attachments:
        MailAttachment.objects.create(
            message=mail_msg,
            filename=att["filename"],
            content_type=att.get("content_type", "application/octet-stream"),
            size=len(att["data"]),
            file=ContentFile(att["data"], name=att["filename"]),
        )

    return mail_msg
