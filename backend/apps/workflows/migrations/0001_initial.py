# FASE 08 - Workflow documentale multi-step

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0001_initial"),
        ("documents", "0003_alter_document_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkflowTemplate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("is_published", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_workflow_templates", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Template workflow",
                "verbose_name_plural": "Template workflow",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="WorkflowStep",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("order", models.IntegerField(default=0)),
                ("action", models.CharField(choices=[("review", "Revisione"), ("approve", "Approvazione"), ("sign", "Firma"), ("acknowledge", "Presa visione")], default="review", max_length=20)),
                ("assignee_type", models.CharField(choices=[("role", "Ruolo globale"), ("ou_role", "Ruolo in Unità Organizzativa"), ("specific_user", "Utente specifico"), ("document_ou", "UO del documento")], default="role", max_length=20)),
                ("assignee_role", models.CharField(blank=True, max_length=30, null=True)),
                ("assignee_ou_role", models.CharField(blank=True, max_length=30, null=True)),
                ("is_required", models.BooleanField(default=True)),
                ("deadline_days", models.IntegerField(blank=True, null=True)),
                ("instructions", models.TextField(blank=True)),
                ("assignee_ou", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="workflow_steps_ou", to="organizations.organizationalunit")),
                ("assignee_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_workflow_steps", to=settings.AUTH_USER_MODEL)),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="steps", to="workflows.workflowtemplate")),
            ],
            options={
                "verbose_name": "Step workflow",
                "verbose_name_plural": "Step workflow",
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="WorkflowInstance",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("active", "In corso"), ("completed", "Completato"), ("rejected", "Rifiutato"), ("cancelled", "Annullato")], default="active", max_length=20)),
                ("current_step_order", models.IntegerField(default=0)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="workflow_instances", to="documents.document")),
                ("started_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="started_workflows", to=settings.AUTH_USER_MODEL)),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="instances", to="workflows.workflowtemplate")),
            ],
            options={
                "verbose_name": "Istanza workflow",
                "verbose_name_plural": "Istanze workflow",
                "ordering": ["-started_at"],
            },
        ),
        migrations.CreateModel(
            name="WorkflowStepInstance",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("pending", "In attesa"), ("in_progress", "In lavorazione"), ("completed", "Completato"), ("rejected", "Rifiutato"), ("skipped", "Saltato")], default="pending", max_length=20)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("action_taken", models.CharField(blank=True, max_length=30, null=True)),
                ("comment", models.TextField(blank=True)),
                ("deadline", models.DateTimeField(blank=True, null=True)),
                ("assigned_to", models.ManyToManyField(blank=True, related_name="workflow_step_assignments", to=settings.AUTH_USER_MODEL)),
                ("completed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="completed_workflow_steps", to=settings.AUTH_USER_MODEL)),
                ("step", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="step_instances", to="workflows.workflowstep")),
                ("workflow_instance", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="step_instances", to="workflows.workflowinstance")),
            ],
            options={
                "verbose_name": "Istanza step",
                "verbose_name_plural": "Istanze step",
                "unique_together": {("workflow_instance", "step")},
            },
        ),
    ]
