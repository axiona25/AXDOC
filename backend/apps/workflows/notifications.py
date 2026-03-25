"""
Helper per creare notifiche workflow in-app.
"""
from apps.notifications.models import Notification
from django.contrib.contenttypes.models import ContentType


def _tenant_id_for_workflow(workflow):
    doc = getattr(workflow, "document", None)
    if doc and getattr(doc, "tenant_id", None):
        return doc.tenant_id
    if getattr(workflow, "tenant_id", None):
        return workflow.tenant_id
    return None


def notify_step_assigned(step_instance):
    """
    Notifica tutti gli utenti assegnati a uno step che è il loro turno.
    Tipo: workflow_assigned
    """
    workflow = step_instance.workflow_instance
    doc_title = workflow.document.title
    step_name = step_instance.step.name
    template_name = workflow.template.name

    ct = ContentType.objects.get_for_model(workflow)
    tid = _tenant_id_for_workflow(workflow)

    for user in step_instance.assigned_to.all():
        Notification.objects.create(
            recipient=user,
            tenant_id=tid,
            notification_type="workflow_assigned",
            title=f"Azione richiesta: {step_name}",
            body=f'Sei stato assegnato allo step "{step_name}" del workflow "{template_name}" sul documento "{doc_title}".',
            content_type=ct,
            object_id=workflow.pk,
            link_url=f"/documents?doc={workflow.document_id}",
            metadata={
                "workflow_instance_id": str(workflow.pk),
                "step_instance_id": str(step_instance.pk),
                "document_id": str(workflow.document_id),
                "action": step_instance.step.action,
            },
        )


def notify_step_completed(step_instance, completed_by_user):
    """
    Notifica chi ha avviato il workflow che uno step è stato completato.
    Tipo: workflow_approved
    """
    workflow = step_instance.workflow_instance
    if not workflow.started_by or workflow.started_by == completed_by_user:
        return  # Non notificare se stessa persona

    doc_title = workflow.document.title
    step_name = step_instance.step.name
    action_label = {
        "approve": "approvato",
        "complete": "completato",
        "sign": "firmato",
    }.get(step_instance.action_taken, "completato")

    ct = ContentType.objects.get_for_model(workflow)
    tid = _tenant_id_for_workflow(workflow)

    Notification.objects.create(
        recipient=workflow.started_by,
        tenant_id=tid,
        notification_type="workflow_approved",
        title=f"Step {action_label}: {step_name}",
        body=f'{completed_by_user.get_full_name() or completed_by_user.email} ha {action_label} lo step "{step_name}" sul documento "{doc_title}".',
        content_type=ct,
        object_id=workflow.pk,
        link_url=f"/documents?doc={workflow.document_id}",
        metadata={
            "workflow_instance_id": str(workflow.pk),
            "document_id": str(workflow.document_id),
        },
    )


def notify_step_rejected(step_instance, rejected_by_user):
    """
    Notifica chi ha avviato il workflow che uno step è stato rifiutato.
    Tipo: workflow_rejected
    """
    workflow = step_instance.workflow_instance
    if not workflow.started_by or workflow.started_by == rejected_by_user:
        return

    doc_title = workflow.document.title
    step_name = step_instance.step.name
    comment = step_instance.comment or ""

    ct = ContentType.objects.get_for_model(workflow)
    tid = _tenant_id_for_workflow(workflow)

    suffix = f" Motivo: {comment}" if comment else ""
    body = (
        f'{rejected_by_user.get_full_name() or rejected_by_user.email} ha rifiutato lo step "{step_name}" '
        f'sul documento "{doc_title}".{suffix}'
    )

    Notification.objects.create(
        recipient=workflow.started_by,
        tenant_id=tid,
        notification_type="workflow_rejected",
        title=f"Step rifiutato: {step_name}",
        body=body,
        content_type=ct,
        object_id=workflow.pk,
        link_url=f"/documents?doc={workflow.document_id}",
        metadata={
            "workflow_instance_id": str(workflow.pk),
            "document_id": str(workflow.document_id),
            "comment": comment,
        },
    )


def notify_workflow_completed(workflow_instance):
    """
    Notifica chi ha avviato il workflow che è stato completato.
    Tipo: workflow_completed
    """
    workflow = workflow_instance
    if not workflow.started_by:
        return

    doc_title = workflow.document.title
    template_name = workflow.template.name

    ct = ContentType.objects.get_for_model(workflow)
    tid = _tenant_id_for_workflow(workflow)

    Notification.objects.create(
        recipient=workflow.started_by,
        tenant_id=tid,
        notification_type="workflow_completed",
        title=f"Workflow completato: {template_name}",
        body=f'Il workflow "{template_name}" sul documento "{doc_title}" è stato completato con successo.',
        content_type=ct,
        object_id=workflow.pk,
        link_url=f"/documents?doc={workflow.document_id}",
        metadata={
            "workflow_instance_id": str(workflow.pk),
            "document_id": str(workflow.document_id),
        },
    )


def notify_workflow_cancelled(workflow_instance, cancelled_by_user):
    """
    Notifica tutti gli utenti assegnati allo step corrente che il workflow è stato annullato.
    """
    workflow = workflow_instance
    doc_title = workflow.document.title

    ct = ContentType.objects.get_for_model(workflow)
    tid = _tenant_id_for_workflow(workflow)

    # Notifica assegnatari dello step corrente
    current_si = workflow.step_instances.filter(status="in_progress").first()
    recipients = set()
    if current_si:
        recipients.update(current_si.assigned_to.all())
    # Notifica anche chi ha avviato (se diverso)
    if workflow.started_by and workflow.started_by != cancelled_by_user:
        recipients.add(workflow.started_by)

    for user in recipients:
        if user == cancelled_by_user:
            continue
        Notification.objects.create(
            recipient=user,
            tenant_id=tid,
            notification_type="system",
            title="Workflow annullato",
            body=f'{cancelled_by_user.get_full_name() or cancelled_by_user.email} ha annullato il workflow sul documento "{doc_title}".',
            content_type=ct,
            object_id=workflow.pk,
            link_url=f"/documents?doc={workflow.document_id}",
            metadata={
                "workflow_instance_id": str(workflow.pk),
                "document_id": str(workflow.document_id),
            },
        )


def notify_consulted(step_instance):
    """
    Notifica gli utenti Consulted che il loro parere è richiesto.
    Tipo: workflow_assigned (riuso, con metadata.raci_role = 'consulted')
    """
    workflow = step_instance.workflow_instance
    doc_title = workflow.document.title
    step_name = step_instance.step.name
    ct = ContentType.objects.get_for_model(workflow)
    tid = _tenant_id_for_workflow(workflow)

    for user in step_instance.step.consulted_users.all():
        Notification.objects.create(
            recipient=user,
            tenant_id=tid,
            notification_type="workflow_assigned",
            title=f"Parere richiesto: {step_name}",
            body=(
                f'Il tuo parere è richiesto per lo step "{step_name}" sul documento "{doc_title}". '
                f"Rispondi con il tuo feedback."
            ),
            content_type=ct,
            object_id=workflow.pk,
            link_url=f"/documents?doc={workflow.document_id}",
            metadata={
                "workflow_instance_id": str(workflow.pk),
                "step_instance_id": str(step_instance.pk),
                "document_id": str(workflow.document_id),
                "raci_role": "consulted",
            },
        )


def notify_informed(step_instance, action_taken, completed_by_user):
    """
    Notifica gli utenti Informed che lo step è stato completato.
    Tipo: workflow_approved (riuso, con metadata.raci_role = 'informed')
    """
    workflow = step_instance.workflow_instance
    doc_title = workflow.document.title
    step_name = step_instance.step.name
    action_label = {
        "approve": "approvato",
        "complete": "completato",
        "sign": "firmato",
        "reject": "rifiutato",
    }.get(action_taken, "completato")
    ct = ContentType.objects.get_for_model(workflow)
    tid = _tenant_id_for_workflow(workflow)

    for user in step_instance.step.informed_users.all():
        if user == completed_by_user:
            continue
        Notification.objects.create(
            recipient=user,
            tenant_id=tid,
            notification_type="workflow_approved",
            title=f"Step {action_label}: {step_name}",
            body=(
                f'Lo step "{step_name}" sul documento "{doc_title}" è stato {action_label} da '
                f"{completed_by_user.get_full_name() or completed_by_user.email}."
            ),
            content_type=ct,
            object_id=workflow.pk,
            link_url=f"/documents?doc={workflow.document_id}",
            metadata={
                "workflow_instance_id": str(workflow.pk),
                "document_id": str(workflow.document_id),
                "raci_role": "informed",
            },
        )

    accountable = step_instance.step.accountable_user
    if accountable and accountable != completed_by_user:
        Notification.objects.create(
            recipient=accountable,
            tenant_id=tid,
            notification_type="workflow_approved",
            title=f"Step {action_label}: {step_name} (supervisione)",
            body=(
                f'Lo step "{step_name}" di cui sei responsabile è stato {action_label} da '
                f"{completed_by_user.get_full_name() or completed_by_user.email}."
            ),
            content_type=ct,
            object_id=workflow.pk,
            link_url=f"/documents?doc={workflow.document_id}",
            metadata={
                "workflow_instance_id": str(workflow.pk),
                "document_id": str(workflow.document_id),
                "raci_role": "accountable",
            },
        )
