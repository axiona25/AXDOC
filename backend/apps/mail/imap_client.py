"""
Client IMAP per scaricare email da account configurati.
"""
import email
import imaplib
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime

from django.core.files.base import ContentFile
from django.utils import timezone

from .models import MailAccount, MailAttachment, MailMessage


def _decode_header_value(raw: str) -> str:
    """Decodifica header MIME (gestisce encoding misti)."""
    if not raw:
        return ""
    parts = decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded).strip()


def _parse_addresses(raw: str) -> list[dict]:
    """Parsa header To/Cc/Bcc in lista di {email, name}."""
    if not raw:
        return []
    addresses = []
    for addr_str in raw.split(","):
        name, email_addr = parseaddr(addr_str.strip())
        if email_addr:
            addresses.append(
                {
                    "email": email_addr,
                    "name": _decode_header_value(name) if name else "",
                }
            )
    return addresses


def fetch_new_emails(account: MailAccount, max_messages: int = 50) -> int:
    """
    Scarica nuove email dall'account IMAP.
    Ritorna il numero di nuovi messaggi scaricati.
    """
    try:
        if account.imap_use_ssl:
            conn = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
        else:
            conn = imaplib.IMAP4(account.imap_host, account.imap_port)

        conn.login(account.imap_username, account.imap_password)
        conn.select("INBOX")

        if account.last_fetch_uid:
            try:
                uid_min = int(account.last_fetch_uid) + 1
                status, data = conn.uid("SEARCH", None, f"UID {uid_min}:*")
            except ValueError:  # pragma: no cover — UID non numerico in DB legacy
                status, data = conn.uid("SEARCH", None, "ALL")
        else:
            status, data = conn.uid("SEARCH", None, "ALL")

        if status != "OK" or not data or not data[0]:
            conn.logout()
            return 0

        uids = data[0].split()
        if not uids:
            conn.logout()
            return 0

        uids = uids[-max_messages:]
        count = 0

        for uid_bytes in uids:
            uid = uid_bytes.decode()

            if MailMessage.objects.filter(account=account, imap_uid=uid).exists():
                continue

            status, msg_data = conn.uid("fetch", uid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = _decode_header_value(msg.get("Subject", ""))
            from_name, from_addr = parseaddr(msg.get("From", ""))
            to_addresses = _parse_addresses(msg.get("To", ""))
            cc_addresses = _parse_addresses(msg.get("Cc", ""))
            message_id = msg.get("Message-ID", "") or ""
            in_reply_to = msg.get("In-Reply-To", "") or ""

            date_header = msg.get("Date")
            if date_header:
                try:
                    sent_at = parsedate_to_datetime(date_header)
                    if sent_at is not None and timezone.is_naive(sent_at):
                        sent_at = timezone.make_aware(sent_at)
                except Exception:  # pragma: no cover — date header malformato
                    sent_at = timezone.now()
            else:
                sent_at = timezone.now()

            body_text = ""
            body_html = ""
            attachments_data = []

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    disposition = str(part.get("Content-Disposition", ""))

                    if "attachment" in disposition:
                        att_filename = part.get_filename()
                        if att_filename:
                            att_filename = _decode_header_value(att_filename)
                            att_data = part.get_payload(decode=True)
                            if att_data:
                                attachments_data.append(
                                    {
                                        "filename": att_filename,
                                        "content_type": content_type,
                                        "data": att_data,
                                    }
                                )
                    elif content_type == "text/plain" and not body_text:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            body_text = payload.decode(charset, errors="replace")
                    elif content_type == "text/html" and not body_html:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            body_html = payload.decode(charset, errors="replace")
            else:
                content_type = msg.get_content_type()
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    if content_type == "text/html":
                        body_html = payload.decode(charset, errors="replace")
                    else:
                        body_text = payload.decode(charset, errors="replace")

            mail_msg = MailMessage.objects.create(
                account=account,
                direction="in",
                message_id=message_id,
                in_reply_to=in_reply_to,
                from_address=from_addr or "unknown@invalid.local",
                from_name=_decode_header_value(from_name) if from_name else "",
                to_addresses=to_addresses,
                cc_addresses=cc_addresses,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                has_attachments=len(attachments_data) > 0,
                status="unread",
                folder="INBOX",
                imap_uid=uid,
                sent_at=sent_at,
            )

            for att in attachments_data:
                MailAttachment.objects.create(
                    message=mail_msg,
                    filename=att["filename"],
                    content_type=att["content_type"],
                    size=len(att["data"]),
                    file=ContentFile(att["data"], name=att["filename"]),
                )

            count += 1

        if uids:
            account.last_fetch_uid = uids[-1].decode()
            account.last_fetch_at = timezone.now()
            account.save(update_fields=["last_fetch_uid", "last_fetch_at"])

        conn.logout()
        return count

    except Exception as e:
        print(f"[IMAP] Errore fetch {account.email_address}: {e}")
        return 0
