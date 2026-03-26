"""
API Rubrica Contatti.
"""
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Contact
from .serializers import ContactDetailSerializer, ContactListSerializer


class ContactViewSet(viewsets.ModelViewSet):
    """CRUD contatti + ricerca + import da mail."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Contact.objects.all()

        if getattr(user, "role", None) != "ADMIN":
            qs = qs.filter(Q(is_shared=True) | Q(created_by=user))

        search = self.request.query_params.get("search", "").strip()
        if search:
            q = (
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(company_name__icontains=search)
            )
            # email/pec/phone sono cifrati: niente icontains; solo uguaglianza esatta su email/pec
            if "@" in search:
                q |= Q(email=search) | Q(pec=search)
            qs = qs.filter(q)

        contact_type = self.request.query_params.get("type")
        if contact_type:
            qs = qs.filter(contact_type=contact_type)

        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(tags__contains=[tag])

        if self.request.query_params.get("favorites") == "true":
            qs = qs.filter(is_favorite=True)

        return qs.order_by("last_name", "first_name", "company_name")

    def get_serializer_class(self):
        if self.action in ("list",):
            return ContactListSerializer
        return ContactDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, source="manual")

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        """
        GET /api/contacts/search/?q=mario
        Ricerca veloce per autocomplete (ritorna max 15 risultati).
        """
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response([])

        q_filter = (
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(company_name__icontains=q)
        )
        if "@" in q:
            q_filter |= Q(email=q) | Q(pec=q)
        qs = self.get_queryset().filter(q_filter).distinct()[:15]

        return Response(ContactListSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"], url_path="import_from_mail")
    def import_from_mail(self, request):
        """
        POST /api/contacts/import_from_mail/
        Importa contatti unici dalle email ricevute/inviate.
        """
        from apps.mail.models import MailMessage
        from django.contrib.auth import get_user_model

        User = get_user_model()

        messages = MailMessage.objects.all()
        addresses = {}

        for msg in messages.iterator():
            if msg.from_address:
                addr = msg.from_address.lower().strip()
                name = msg.from_name or ""
                if addr and (addr not in addresses or (name and not addresses.get(addr, ""))):
                    addresses[addr] = name

            for field in (msg.to_addresses, msg.cc_addresses):
                if not field:
                    continue
                for entry in field:
                    if isinstance(entry, dict):
                        addr = (entry.get("email") or "").lower().strip()
                        name = entry.get("name") or ""
                    elif isinstance(entry, str):
                        addr = entry.lower().strip()
                        name = ""
                    else:
                        continue
                    if addr and (addr not in addresses or (name and not addresses.get(addr, ""))):
                        addresses[addr] = name

        internal_emails = {
            e.lower().strip()
            for e in User.objects.filter(is_active=True).values_list("email", flat=True)
            if e
        }
        existing_emails = {
            e.lower().strip()
            for e in Contact.objects.exclude(email="").values_list("email", flat=True)
            if e
        }
        existing_pecs = {
            p.lower().strip()
            for p in Contact.objects.exclude(pec="").values_list("pec", flat=True)
            if p
        }

        created = 0
        internal_skipped = 0
        already_existing = 0

        for addr, name in addresses.items():
            if not addr or "@" not in addr:
                continue
            if addr in internal_emails:
                internal_skipped += 1
                continue
            if addr in existing_emails or addr in existing_pecs:
                already_existing += 1
                continue

            first_name = ""
            last_name = ""
            if name:
                parts = name.strip().split(" ", 1)
                first_name = parts[0] if parts else ""
                last_name = parts[1] if len(parts) > 1 else ""

            Contact.objects.create(
                contact_type="person",
                first_name=first_name,
                last_name=last_name,
                email=addr,
                source="mail_import",
                created_by=request.user,
                is_shared=True,
            )
            created += 1
            existing_emails.add(addr)

        return Response(
            {
                "total_addresses": len(addresses),
                "already_existing": already_existing,
                "internal_skipped": internal_skipped,
                "created": created,
            }
        )

    @action(detail=True, methods=["post"], url_path="toggle_favorite")
    def toggle_favorite(self, request, pk=None):
        contact = self.get_object()
        contact.is_favorite = not contact.is_favorite
        contact.save(update_fields=["is_favorite"])
        return Response({"is_favorite": contact.is_favorite})
