from rest_framework import serializers
from apps.documents.models import Document


class SearchResultSerializer(serializers.ModelSerializer):
    """Documento con snippet e score per risultati ricerca."""
    snippet = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    folder_name = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id", "title", "description", "status", "current_version",
            "created_at", "updated_at", "created_by_id",
            "folder_id", "folder_name", "metadata_structure_id",
            "snippet", "score",
        ]

    def get_snippet(self, obj):
        return getattr(obj, "_search_snippet", None) or (obj.description or "")[:300]

    def get_score(self, obj):
        return getattr(obj, "_search_score", None)

    def get_folder_name(self, obj):
        return obj.folder.name if obj.folder_id else None
