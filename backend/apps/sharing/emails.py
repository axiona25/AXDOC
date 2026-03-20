"""
Email per condivisione esterna (FASE 11).
"""
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_share_email(share_link):
    """
    Invia email HTML all'utente esterno con link alla risorsa condivisa.
    """
    frontend = getattr(settings, "FRONTEND_URL", "") or "http://localhost:3000"
    url = f"{frontend}/share/{share_link.token}"
    shared_by = share_link.shared_by
    shared_by_name = f"{getattr(shared_by, 'first_name', '')} {getattr(shared_by, 'last_name', '')}".strip() or shared_by.email

    if share_link.document_id:
        title = share_link.document.title
        resource_type = "documento"
    else:
        title = share_link.protocol.subject or share_link.protocol.protocol_id
        resource_type = "protocollo"

    expires_text = "Questo link non scade."
    if share_link.expires_at:
        from django.utils.formats import date_format
        from django.utils import timezone
        expires_text = f"Questo link scade il {date_format(timezone.localtime(share_link.expires_at), 'DATETIME_FORMAT')}."

    subject = f"{shared_by_name} ha condiviso un {resource_type} con te"
    html_message = f"""
    <p>Ciao{(' ' + share_link.recipient_name) if share_link.recipient_name else ''},</p>
    <p><strong>{shared_by_name}</strong> ha condiviso un {resource_type} con te.</p>
    <p><strong>Titolo:</strong> {title}</p>
    <p>{expires_text}</p>
    <p><a href="{url}" style="display:inline-block; padding:10px 20px; background:#4F46E5; color:white; text-decoration:none; border-radius:6px;">Accedi al {resource_type}</a></p>
    <p style="color:#666; font-size:12px;">{expires_text}</p>
    """
    plain = strip_tags(html_message)
    send_mail(
        subject=subject,
        message=plain,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[share_link.recipient_email],
        fail_silently=True,
        html_message=html_message,
    )
