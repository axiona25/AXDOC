from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea il tenant di default e assegna i record esistenti senza tenant."

    def handle(self, *args, **options):
        from apps.organizations.models import Tenant, OrganizationalUnit
        from apps.users.models import User, UserGroup
        from apps.documents.models import Document, Folder, DocumentTemplate
        from apps.protocols.models import Protocol, ProtocolCounter
        from apps.dossiers.models import Dossier
        from apps.workflows.models import WorkflowTemplate, WorkflowInstance
        from apps.metadata.models import MetadataStructure
        from apps.sharing.models import ShareLink
        from apps.chat.models import ChatRoom
        from apps.mail.models import MailAccount
        from apps.archive.models import InformationPackage
        from apps.admin_panel.models import SystemSettings
        from apps.authentication.models import AuditLog
        from apps.audit.models import SecurityIncident
        from apps.notifications.models import Notification

        tenant, created = Tenant.objects.get_or_create(
            slug="default",
            defaults={
                "name": "Organizzazione Default",
                "plan": "enterprise",
            },
        )
        self.stdout.write(
            f"Tenant: {tenant.name} ({'creato' if created else 'esistente'})"
        )

        models = [
            OrganizationalUnit,
            User,
            UserGroup,
            Document,
            Folder,
            DocumentTemplate,
            Protocol,
            ProtocolCounter,
            Dossier,
            WorkflowTemplate,
            WorkflowInstance,
            MetadataStructure,
            ShareLink,
            ChatRoom,
            MailAccount,
            InformationPackage,
            SystemSettings,
            AuditLog,
            SecurityIncident,
            Notification,
        ]
        for Model in models:
            n = Model.objects.filter(tenant__isnull=True).update(tenant=tenant)
            if n:
                self.stdout.write(f"  {Model.__name__}: {n} aggiornati")
