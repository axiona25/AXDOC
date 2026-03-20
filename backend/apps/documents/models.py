"""
Modelli documenti: cartelle, documenti, versioning, allegati, permessi (FASE 05).
Compatibilità con cifratura on-demand (FASE 04): DocumentVersion.is_encrypted, encryption_salt.
"""
import uuid
from django.db import models
from django.conf import settings


def _user_model():
    return settings.AUTH_USER_MODEL


class Folder(models.Model):
    """Cartella con gerarchia parent/subfolders (RF-028). Metadati AGID (FASE 18)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subfolders",
    )
    created_by = models.ForeignKey(
        _user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_folders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    metadata_structure = models.ForeignKey(
        "metadata.MetadataStructure",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="folders",
    )
    metadata_values = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Cartella"
        verbose_name_plural = "Cartelle"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_path(self):
        """Restituisce il path come stringa 'root/cartella/sottocartella'."""
        ancestors = self.get_ancestors()
        if not ancestors:
            return "root" if not self.parent_id else self.name
        return "root/" + "/".join(a.name for a in ancestors) + "/" + self.name

    def get_ancestors(self):
        """Lista delle cartelle parent dalla root verso il basso."""
        out = []
        current = self.parent
        while current:
            out.append(current)
            current = current.parent
        return list(reversed(out))

    def validate_metadata(self, values):
        """Valida metadata_values rispetto alla struttura associata. Ritorna lista errori."""
        if not self.metadata_structure_id:
            return []
        from apps.metadata.validators import validate_metadata_values
        return validate_metadata_values(self.metadata_structure, values)


class Document(models.Model):
    """Documento con stato, cartella, versioning e permessi (RF-028..RF-039)."""
    STATUS_DRAFT = "DRAFT"
    STATUS_IN_REVIEW = "IN_REVIEW"
    STATUS_APPROVED = "APPROVED"
    STATUS_ARCHIVED = "ARCHIVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Bozza"),
        (STATUS_IN_REVIEW, "In revisione"),
        (STATUS_APPROVED, "Approvato"),
        (STATUS_ARCHIVED, "Archiviato"),
        (STATUS_REJECTED, "Rifiutato"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    folder = models.ForeignKey(
        Folder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    current_version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        _user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    metadata_structure = models.ForeignKey(
        "metadata.MetadataStructure",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    metadata_values = models.JSONField(default=dict)
    locked_by = models.ForeignKey(
        _user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="locked_documents",
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    is_protocolled = models.BooleanField(
        default=False,
        help_text="Se True, il documento non è modificabile (RF-063).",
    )
    # FASE 19: I miei File — visibilità e proprietario
    VISIBILITY_PERSONAL = "personal"
    VISIBILITY_OFFICE = "office"
    VISIBILITY_SHARED = "shared"
    VISIBILITY_CHOICES = [
        (VISIBILITY_PERSONAL, "Personale"),
        (VISIBILITY_OFFICE, "Ufficio"),
        (VISIBILITY_SHARED, "Condiviso"),
    ]
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PERSONAL,
        help_text="personal: solo autore; office: tutti i membri UO; shared: condivisione esplicita.",
    )
    owner = models.ForeignKey(
        _user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_documents",
        help_text="Proprietario (impostato a created_by alla creazione).",
    )

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documenti"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title

    def validate_metadata(self, values):
        """
        Valida metadata_values rispetto alla struttura associata.
        Ritorna lista errori: [{"field": "name", "message": "..."}, ...]
        """
        if not self.metadata_structure_id:
            return []
        from apps.metadata.validators import validate_metadata_values
        return validate_metadata_values(self.metadata_structure, values)

    @property
    def current_version_obj(self):
        """Restituisce l'oggetto DocumentVersion della versione corrente."""
        return self.versions.filter(version_number=self.current_version).first()


class DocumentVersion(models.Model):
    """Versione di un documento: file, checksum, autore (RF-033, RF-034)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to="documents/%Y/%m/", blank=True)
    file_name = models.CharField(max_length=500, default="")
    file_size = models.BigIntegerField(default=0)
    file_type = models.CharField(max_length=255, default="")
    checksum = models.CharField(max_length=64, default="")
    created_by = models.ForeignKey(
        _user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="document_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    change_description = models.TextField(blank=True)
    is_current = models.BooleanField(default=True)
    # FASE 04: cifratura on-demand
    is_encrypted = models.BooleanField(default=False)
    encryption_salt = models.CharField(max_length=256, blank=True)

    class Meta:
        ordering = ["-version_number"]
        unique_together = [["document", "version_number"]]
        verbose_name = "Versione documento"
        verbose_name_plural = "Versioni documento"

    def __str__(self):
        return f"{self.document.title} v{self.version_number}"


class DocumentAttachment(models.Model):
    """Allegato a un documento (RF-036)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="attachments/%Y/%m/")
    file_name = models.CharField(max_length=500)
    file_size = models.BigIntegerField(default=0)
    file_type = models.CharField(max_length=255, default="")
    uploaded_by = models.ForeignKey(
        _user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="document_attachments",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = "Allegato"
        verbose_name_plural = "Allegati"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.file_name


class DocumentPermission(models.Model):
    """Permesso utente su documento: read/write/delete (RF-035)."""
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="user_permissions",
    )
    user = models.ForeignKey(
        _user_model(),
        on_delete=models.CASCADE,
        related_name="document_permissions",
    )
    can_read = models.BooleanField(default=True)
    can_write = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = [["document", "user"]]
        verbose_name = "Permesso documento (utente)"
        verbose_name_plural = "Permessi documento (utenti)"

    def __str__(self):
        return f"{self.document.title} — {self.user.email}"


class DocumentOUPermission(models.Model):
    """Permesso UO su documento: read/write (RF-035)."""
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="ou_permissions",
    )
    organizational_unit = models.ForeignKey(
        "organizations.OrganizationalUnit",
        on_delete=models.CASCADE,
        related_name="document_permissions",
    )
    can_read = models.BooleanField(default=True)
    can_write = models.BooleanField(default=False)

    class Meta:
        unique_together = [["document", "organizational_unit"]]
        verbose_name = "Permesso documento (UO)"
        verbose_name_plural = "Permessi documento (UO)"

    def __str__(self):
        return f"{self.document.title} — {self.organizational_unit.code}"
