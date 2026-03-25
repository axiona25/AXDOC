from rest_framework import serializers
from .models import SecurityIncident


class SecurityIncidentSerializer(serializers.ModelSerializer):
    reported_by_email = serializers.EmailField(source="reported_by.email", read_only=True)
    assigned_to_email = serializers.SerializerMethodField()

    def get_assigned_to_email(self, obj):
        return obj.assigned_to.email if obj.assigned_to else None

    class Meta:
        model = SecurityIncident
        fields = [
            "id",
            "title",
            "description",
            "severity",
            "status",
            "category",
            "affected_systems",
            "affected_users_count",
            "data_compromised",
            "containment_actions",
            "remediation_actions",
            "reported_to_authority",
            "authority_report_date",
            "authority_reference",
            "reported_by",
            "reported_by_email",
            "assigned_to",
            "assigned_to_email",
            "detected_at",
            "created_at",
            "updated_at",
            "resolved_at",
        ]
        read_only_fields = [
            "id",
            "reported_by",
            "reported_by_email",
            "created_at",
            "updated_at",
        ]
