"""
Gestione licenza di sistema (Documento Collaudo).
Impostazioni di sistema (FASE 17): Email, Organizzazione, Protocollo, Sicurezza, Storage, LDAP, Conservazione.
"""
from django.db import models
from django.utils import timezone


class SystemSettings(models.Model):
    """
    Singleton (pk=1) per configurazioni di sistema.
    Sezioni: email, organization, protocol, security, storage, ldap, conservation.
    """
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    # Sezioni in un unico JSON per flessibilità
    email = models.JSONField(default=dict, blank=True)  # backend_console, smtp_*, test
    organization = models.JSONField(default=dict, blank=True)  # name, code, pec, logo, protocol_format
    protocol = models.JSONField(default=dict, blank=True)
    security = models.JSONField(default=dict, blank=True)  # login_attempts, timeout, mfa_admin
    storage = models.JSONField(default=dict, blank=True)  # max_upload_mb, allowed_extensions
    ldap = models.JSONField(default=dict, blank=True)  # enabled, server_uri, bind_dn, password, search_base
    conservation = models.JSONField(default=dict, blank=True)  # provider, api_url, api_key
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Impostazioni di sistema"
        verbose_name_plural = "Impostazioni di sistema"

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={})
        return obj


class SystemLicense(models.Model):
    """
    Unica istanza — configurazione licenza del sistema.
    id=1 usato come singleton.
    """
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    organization_name = models.CharField(max_length=500)
    license_key = models.CharField(max_length=500, blank=True)
    activated_at = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)  # null = perpetua
    max_users = models.IntegerField(null=True, blank=True)  # null = illimitato
    max_storage_gb = models.FloatField(null=True, blank=True)
    features_enabled = models.JSONField(
        default=dict,
        blank=True,
        help_text='Es: {"mfa": true, "sso": false, "ldap": true, ...}',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Licenza di sistema"
        verbose_name_plural = "Licenze di sistema"

    def __str__(self):
        return self.organization_name or "Licenza"

    @classmethod
    def get_current(cls):
        return cls.objects.filter(pk=1).first()

    @classmethod
    def is_feature_enabled(cls, feature: str) -> bool:
        lic = cls.get_current()
        if not lic or not lic.features_enabled:
            return False
        return lic.features_enabled.get(feature, False)
