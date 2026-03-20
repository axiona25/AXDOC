from django.contrib import admin
from .models import WorkflowTemplate, WorkflowStep, WorkflowInstance, WorkflowStepInstance


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 0


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "is_published", "created_by", "created_at"]
    list_filter = ["is_published"]
    inlines = [WorkflowStepInline]


@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):
    list_display = ["template", "document", "status", "started_by", "started_at"]


@admin.register(WorkflowStepInstance)
class WorkflowStepInstanceAdmin(admin.ModelAdmin):
    list_display = ["workflow_instance", "step", "status", "action_taken", "completed_at"]
