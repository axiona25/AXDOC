"""
Workflow documentale multi-step (RF-048..RF-057).
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

STEP_ACTION = [
    ("review", "Revisione"),
    ("approve", "Approvazione"),
    ("sign", "Firma"),
    ("acknowledge", "Presa visione"),
]

STEP_ASSIGNEE_TYPE = [
    ("role", "Ruolo globale"),
    ("ou_role", "Ruolo in Unità Organizzativa"),
    ("specific_user", "Utente specifico"),
    ("document_ou", "UO del documento"),
]

WORKFLOW_INSTANCE_STATUS = [
    ("active", "In corso"),
    ("completed", "Completato"),
    ("rejected", "Rifiutato"),
    ("cancelled", "Annullato"),
]

STEP_INSTANCE_STATUS = [
    ("pending", "In attesa"),
    ("in_progress", "In lavorazione"),
    ("completed", "Completato"),
    ("rejected", "Rifiutato"),
    ("skipped", "Saltato"),
]


def _user_model():
    return settings.AUTH_USER_MODEL


class WorkflowTemplate(models.Model):
    """Template di workflow multi-step (RF-048, RF-050)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        _user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_workflow_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "Template workflow"
        verbose_name_plural = "Template workflow"

    def __str__(self):
        return self.name

    def can_be_applied_to(self, document):
        """Verifica se il workflow può essere applicato al documento (es. tipo/struttura)."""
        return True


class WorkflowStep(models.Model):
    """Step del template con azione e tipo assegnatario (RF-051, RF-052)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    name = models.CharField(max_length=200)
    order = models.IntegerField(default=0)
    action = models.CharField(max_length=20, choices=STEP_ACTION, default="review")
    assignee_type = models.CharField(
        max_length=20,
        choices=STEP_ASSIGNEE_TYPE,
        default="role",
    )
    assignee_role = models.CharField(max_length=30, null=True, blank=True)
    assignee_user = models.ForeignKey(
        _user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_workflow_steps",
    )
    assignee_ou = models.ForeignKey(
        "organizations.OrganizationalUnit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_steps_ou",
    )
    assignee_ou_role = models.CharField(max_length=30, null=True, blank=True)
    is_required = models.BooleanField(default=True)
    deadline_days = models.IntegerField(null=True, blank=True)
    instructions = models.TextField(blank=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "Step workflow"
        verbose_name_plural = "Step workflow"

    def __str__(self):
        return f"{self.template.name} — {self.name}"


class WorkflowInstance(models.Model):
    """Istanza di workflow avviata su un documento (RF-053..RF-056)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.PROTECT,
        related_name="instances",
    )
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="workflow_instances",
    )
    started_by = models.ForeignKey(
        _user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="started_workflows",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=WORKFLOW_INSTANCE_STATUS,
        default="active",
    )
    current_step_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Istanza workflow"
        verbose_name_plural = "Istanze workflow"

    def __str__(self):
        return f"{self.template.name} — {self.document.title}"

    def get_current_step(self):
        """Ritorna WorkflowStepInstance dello step corrente o None."""
        return self.step_instances.filter(step__order=self.current_step_order).first()

    def advance(self):
        """Avanza al prossimo step (ordine)."""
        self.current_step_order += 1
        self.save(update_fields=["current_step_order"])

    def get_assignees_for_step(self, step):
        """Ritorna lista User assegnati a questo step (delegato al servizio)."""
        from .services import WorkflowService
        return WorkflowService.get_assignees(step, self.document)


class WorkflowStepInstance(models.Model):
    """Istanza di uno step in un workflow (stato, assegnatari, esito)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="step_instances",
    )
    step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.PROTECT,
        related_name="step_instances",
    )
    assigned_to = models.ManyToManyField(
        _user_model(),
        related_name="workflow_step_assignments",
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STEP_INSTANCE_STATUS,
        default="pending",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        _user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_workflow_steps",
    )
    action_taken = models.CharField(max_length=30, null=True, blank=True)
    comment = models.TextField(blank=True)
    deadline = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [["workflow_instance", "step"]]
        verbose_name = "Istanza step"
        verbose_name_plural = "Istanze step"

    def __str__(self):
        return f"{self.workflow_instance} — {self.step.name} ({self.status})"
