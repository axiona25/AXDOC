"""
Serializers per template, step e istanze workflow.
"""
from rest_framework import serializers
from .models import WorkflowTemplate, WorkflowStep, WorkflowInstance, WorkflowStepInstance


class WorkflowStepSerializer(serializers.ModelSerializer):
    assignee_display = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowStep
        fields = [
            "id", "template", "name", "order", "action", "assignee_type",
            "assignee_role", "assignee_user", "assignee_ou", "assignee_ou_role",
            "is_required", "deadline_days", "instructions", "assignee_display",
        ]
        read_only_fields = ["id", "template"]

    def get_assignee_display(self, obj):
        if obj.assignee_type == "role" and obj.assignee_role:
            return f"Ruolo: {obj.assignee_role}"
        if obj.assignee_type == "specific_user" and obj.assignee_user:
            return obj.assignee_user.get_full_name()
        if obj.assignee_type == "ou_role" and obj.assignee_ou:
            return f"{obj.assignee_ou.name} — {obj.assignee_ou_role or obj.assignee_role}"
        if obj.assignee_type == "document_ou":
            return "UO del documento"
        return "—"


class WorkflowTemplateListSerializer(serializers.ModelSerializer):
    step_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTemplate
        fields = [
            "id", "name", "description", "is_published",
            "created_by", "created_at", "updated_at", "step_count",
        ]

    def get_step_count(self, obj):
        return obj.steps.count()


class WorkflowTemplateDetailSerializer(serializers.ModelSerializer):
    steps = WorkflowStepSerializer(many=True, read_only=True)
    step_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTemplate
        fields = [
            "id", "name", "description", "is_published",
            "created_by", "created_at", "updated_at",
            "steps", "step_count",
        ]

    def get_step_count(self, obj):
        return obj.steps.count()


class WorkflowStepInstanceSerializer(serializers.ModelSerializer):
    step_name = serializers.CharField(source="step.name", read_only=True)
    step_action = serializers.CharField(source="step.action", read_only=True)
    assigned_to_emails = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowStepInstance
        fields = [
            "id", "step", "step_name", "step_action", "assigned_to", "assigned_to_emails",
            "status", "started_at", "completed_at", "completed_by",
            "action_taken", "comment", "deadline",
        ]

    def get_assigned_to_emails(self, obj):
        return list(obj.assigned_to.values_list("email", flat=True))


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    document_title = serializers.CharField(source="document.title", read_only=True)
    step_instances = WorkflowStepInstanceSerializer(many=True, read_only=True)
    current_step_instance = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowInstance
        fields = [
            "id", "template", "template_name", "document", "document_title",
            "started_by", "started_at", "completed_at", "status",
            "current_step_order", "step_instances", "current_step_instance",
        ]

    def get_current_step_instance(self, obj):
        current = obj.get_current_step()
        return WorkflowStepInstanceSerializer(current).data if current else None
