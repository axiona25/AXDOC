"""
Utility per export CSV membri UO (RF-026).
"""
import csv
from io import StringIO

from .models import OrganizationalUnit


def export_members_csv(ou_id):
    """Genera CSV dei membri dell'UO (id UUID). Restituisce StringIO."""
    try:
        ou = OrganizationalUnit.objects.get(pk=ou_id, is_active=True)
    except OrganizationalUnit.DoesNotExist:
        return None
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Email", "Nome", "Ruolo UO", "Data ingresso"])
    for m in ou.memberships.filter(is_active=True).select_related("user"):
        writer.writerow([
            m.user.email,
            m.user.get_full_name(),
            m.get_role_display(),
            m.joined_at.strftime("%Y-%m-%d %H:%M"),
        ])
    buffer.seek(0)
    return buffer
