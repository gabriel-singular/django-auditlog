from __future__ import unicode_literals

import json

from auditlog.diff import model_instance_diff
from auditlog.models import LogEntry
from django.utils.encoding import smart_text


def log_create(sender, instance, created, **kwargs):
    """
    Signal receiver that creates a log entry when a model instance is first saved to the database.

    Direct use is discouraged, connect your model through :py:func:`auditlog.registry.register` instead.
    """
    if created:
        changes = model_instance_diff(None, instance)

        log_entry = LogEntry.objects.log_create(
            instance,
            action=LogEntry.Action.CREATE,
            changes=json.dumps(changes),
        )


def log_update(sender, instance, **kwargs):
    """
    Signal receiver that creates a log entry when a model instance is changed and saved to the database.

    Direct use is discouraged, connect your model through :py:func:`auditlog.registry.register` instead.
    """
    if instance.pk is not None:
        try:
            old = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            pass
        else:
            new = instance

            changes = model_instance_diff(old, new)

            # Log an entry only if there are changes
            if changes:
                log_entry = LogEntry.objects.log_create(
                    instance,
                    action=LogEntry.Action.UPDATE,
                    changes=json.dumps(changes),
                )

def log_m2m(sender, instance, **kwargs):
    """
    Signal receiver that creates a log entry when a model instance is changed and saved to the database.

    Direct use is discouraged, connect your model through :py:func:`auditlog.registry.register` instead.
    """
    action = kwargs['action']
    pk_set = kwargs['pk_set']
    m2m_fields = instance._meta.local_many_to_many
    model_attr = None
    for field in m2m_fields:
        if field.name in sender._meta.model_name:
            model_attr = field.name
            break

    old_queryset = getattr(instance, model_attr).all().distinct()
    old_value = [str(obj) for obj in old_queryset] if old_queryset is not None and len(old_queryset) > 0 else list()
    if action == 'pre_add':
        new_queryset = old_queryset | kwargs['model'].objects.filter(pk__in=pk_set).distinct()
        new_value = [str(obj) for obj in new_queryset] if new_queryset is not None and \
                    len(new_queryset) > 0 else list()
    elif action == 'pre_remove':
        new_queryset = old_queryset.exclude(pk__in=pk_set).distinct()
        new_value = [str(obj) for obj in new_queryset] if new_queryset is not None and len(new_queryset) > 0 else list()
    else:
        new_value = None
    changes = {}
    if old_value != new_value and new_value is not None:
        changes[model_attr] = (smart_text(old_value), smart_text(new_value))

    if len(changes) == 0:
        changes = None

    if changes:
        log_entry = LogEntry.objects.log_create(
            instance,
            action=LogEntry.Action.UPDATE,
            changes=json.dumps(changes),
        )


def log_delete(sender, instance, **kwargs):
    """
    Signal receiver that creates a log entry when a model instance is deleted from the database.

    Direct use is discouraged, connect your model through :py:func:`auditlog.registry.register` instead.
    """
    if instance.pk is not None:
        changes = model_instance_diff(instance, None)

        log_entry = LogEntry.objects.log_create(
            instance,
            action=LogEntry.Action.DELETE,
            changes=json.dumps(changes),
        )
